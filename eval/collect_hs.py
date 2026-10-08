"""Collect live answers for the Hyperswitch questions through the running CodeCompass API, then score them offline.

CALLS AZURE (about $0.01 each). Plan: each answerable question once, the near-miss once, each trick question 3 times.
Hard cap MAX_CALLS; saves after every call; stops after 3 failures in a row. Pace: PAUSE seconds between calls.

  python eval/collect_hs.py            # collect + score; writes eval/results/hs_live_<timestamp>.json
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_hs import load_questions, score_all, summarise  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
API = "http://127.0.0.1:8000"
PAUSE = 25        # seconds between calls (token quota)
MAX_CALLS = 26    # hard budget, about $0.26
TRICK_RUNS = 3


def plan(questions):
    steps = [(qid, 1) for qid, (kind, _) in questions.items() if kind == "answerable"]
    steps += [(qid, 1) for qid, (kind, _) in questions.items() if kind == "near_miss"]
    steps += [(qid, run) for run in range(1, TRICK_RUNS + 1) for qid, (kind, _) in questions.items() if kind == "trick"]
    return steps


def main():
    questions = load_questions()
    steps = plan(questions)
    assert len(steps) <= MAX_CALLS, f"plan has {len(steps)} calls, over the cap {MAX_CALLS}"
    out = ROOT / "eval" / "results" / f"hs_live_{datetime.now():%Y%m%d_%H%M}.json"
    answers, failures = [], 0
    print(f"{len(steps)} calls planned (cap {MAX_CALLS}); output {out.name}", flush=True)
    for i, (qid, run) in enumerate(steps):
        if i:
            time.sleep(PAUSE)
        question = questions[qid][1]["question"]
        t = time.time()
        try:
            r = httpx.post(f"{API}/api/ask", json={"question": question}, timeout=160)
            body = r.json()
            status = r.status_code
        except Exception as e:  # network or server problems
            status, body = 0, {"error": "client_error", "message": str(e)[:200]}
        answers.append({"id": qid, "run": run, "question": question, "status": status, "seconds": round(time.time() - t, 1), "response": body})
        failures = 0 if status == 200 else failures + 1
        m = body.get("meta", {}) if isinstance(body, dict) else {}
        print(f"[{i+1}/{len(steps)}] {qid} run {run}: HTTP {status} {round(time.time()-t)}s tokens {m.get('input_tokens')} rules {len(body.get('rules', [])) if status == 200 else '-'}", flush=True)
        out.write_text(json.dumps({"agent_note": "agent version is in each response meta", "answers": answers}, indent=2))
        if failures >= 3:
            print("3 failures in a row: stopping to avoid wasting calls", flush=True)
            break

    out.write_text(json.dumps({"answers": answers, **score_run(answers, questions)}, indent=2))
    print(json.dumps(json.loads(out.read_text())["summary"], indent=2))
    print("saved", out.relative_to(ROOT))


def score_run(answers, questions):
    """Score collected answers offline. Answerable and near-miss questions use their single run; each trick question is scored
    per run and passes only if ALL runs pass. (Only trick questions are touched in the per-run step: the scorer adds
    'NOT RUN' entries for every question missing from a batch, and those must not overwrite real results.)"""
    first = [a for a in answers if a["run"] == 1 and questions[a["id"]][0] != "trick"]
    scored = score_all(first)
    trick_runs = {}
    for run in range(1, TRICK_RUNS + 1):
        part = [a for a in answers if questions[a["id"]][0] == "trick" and a["run"] == run]
        for qid, res in score_all(part).items():
            if questions[qid][0] == "trick" and res["verdict"] != "NOT RUN":
                trick_runs.setdefault(qid, []).append(res["verdict"])
    for qid, verdicts in trick_runs.items():
        scored[qid] = {"kind": "trick", "question": questions[qid][1]["question"], "runs": verdicts,
                       "verdict": "PASS" if all(v == "PASS" for v in verdicts) and len(verdicts) == TRICK_RUNS else "FAIL" if "FAIL" in verdicts else "INCOMPLETE"}
    return {"scored": scored, "summary": summarise(scored)}


def rescore(path):
    """Re-score a saved results file without calling Azure."""
    saved = json.loads(Path(path).read_text(encoding="utf-8"))
    result = score_run(saved["answers"], load_questions())
    Path(path).write_text(json.dumps({"answers": saved["answers"], **result}, indent=2))
    print(json.dumps(result["summary"], indent=2))
    return result


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--rescore":
        rescore(sys.argv[2])
    else:
        main()
