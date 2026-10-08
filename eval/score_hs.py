"""Score Hyperswitch demo answers against the verified ground truth in eval/hs_questions.json.

Offline: it reads answers already collected from the API (for example eval/results/smoke_latest.json from eval/smoke.py,
or a list of {"id", "response"}), and never calls Azure. Citations are re-read from the pinned source files.

  python eval/score_hs.py answers.json [--json scored.json]

Answerable question: PASS if some rule has a VERIFIED citation whose real lines (where the citation checker found the text)
hold the expected payment method under the expected connector section, with exactly the expected countries and currencies.
PARTIAL: right connector and payment method, different values. MISS: nothing relevant. Extra rules are counted, not penalised.
Trick question (absent concept): PASS only if rules is empty. Near-miss: always MANUAL (a human reads it). Errors never pass.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRY = re.compile(r"^\s*([A-Za-z0-9_]+)\s*=\s*\{(.*)\}\s*$")
HEADER = re.compile(r"^\s*\[([^\]]+)\]\s*$")


def _norm(text):
    return sorted({t.strip() for t in text.split(",") if t.strip()}) if text is not None else None


def parse_entry(line):
    """'klarna = { country = "DE,AT", currency = "EUR" }' -> {pm, countries, currencies}, else None."""
    m = ENTRY.match(line)
    if not m:
        return None
    body = m.group(2)
    country = re.search(r'country\s*=\s*"([^"]*)"', body)
    currency = re.search(r'currency\s*=\s*"([^"]*)"', body)
    return {"pm": m.group(1), "countries": _norm(country.group(1)) if country else None,
            "currencies": _norm(currency.group(1)) if currency else None}


def section_at(lines, line_no):
    """Name of the nearest [section] header at or above line_no, e.g. 'pm_filters.stripe'."""
    for i in range(line_no, 0, -1):
        m = HEADER.match(lines[i - 1])
        if m:
            return m.group(1)
    return None


class Source:
    def __init__(self, root=ROOT):
        repo = next(r for r in json.loads((root / "repos.json").read_text())["repos"] if r["name"] == "hyperswitch")
        self.base, self._cache = root / repo["path"], {}

    def lines(self, rel):
        if rel not in self._cache:
            path = (self.base / rel).resolve()
            if self.base.resolve() not in path.parents or not path.is_file():
                self._cache[rel] = None
            else:
                self._cache[rel] = path.read_text(encoding="utf-8").splitlines()
        return self._cache[rel]


def score_answerable(item, response, source):
    exact, partial, matching_rules, unverified = [], [], 0, 0
    for rule in response.get("rules", []):
        rule_exact = False
        for c in rule.get("citations", []):
            if c.get("repo") != "hyperswitch":
                continue
            if not c.get("verified"):
                unverified += 1
                continue
            lines = source.lines(c.get("file", ""))
            if not lines:
                continue
            a, b = c.get("found_lines") or [c.get("line_start", 0), c.get("line_end", 0)]
            for ln in range(max(1, a), min(len(lines), b) + 1):
                entry = parse_entry(lines[ln - 1])
                if not entry or entry["pm"] != item["payment_method"]:
                    continue
                if section_at(lines, ln) != f"pm_filters.{item['connector']}":
                    continue
                hit = {"file": c["file"], "line": ln}
                if entry["countries"] == item["countries"] and entry["currencies"] == item["currencies"]:
                    exact.append(hit)
                    rule_exact = True
                else:
                    partial.append({**hit, "countries": entry["countries"], "currencies": entry["currencies"]})
        matching_rules += rule_exact
    verdict = "PASS" if exact else "PARTIAL" if partial else "MISS"
    n = len(response.get("rules", []))
    return {"verdict": verdict, "matched": exact[:3], "different_values": partial[:3], "rules": n,
            "rules_not_matching": n - matching_rules, "unverified_citations": unverified}


def score_trick(response):
    rules = response.get("rules", [])
    return {"verdict": "PASS" if not rules else "FAIL", "rules": len(rules), "gaps_present": bool(response.get("gaps"))}


def score_near_miss(response):
    return {"verdict": "MANUAL", "rules": len(response.get("rules", [])), "answer": (response.get("answer") or "")[:300],
            "rule_texts": [r.get("rule", "")[:160] for r in response.get("rules", [])]}


def load_questions(path=ROOT / "eval" / "hs_questions.json"):
    q = json.loads(Path(path).read_text(encoding="utf-8"))
    items = {x["id"]: ("answerable", x) for x in q["answerable"]}
    items.update({x["id"]: ("trick", x) for x in q["trick"]})
    items.update({x["id"]: ("near_miss", x) for x in q["near_miss"]})
    return items


def score_all(answers, questions=None, source=None):
    questions, source = questions or load_questions(), source or Source()
    by_text = {item["question"]: qid for qid, (_, item) in questions.items()}
    results, seen = {}, set()
    for a in answers:
        qid = a.get("id") or by_text.get(a.get("question"))
        if qid not in questions:
            continue
        seen.add(qid)
        kind, item = questions[qid]
        response = a.get("response") if "response" in a else a.get("result")
        if a.get("status", 200) != 200 or not isinstance(response, dict) or "rules" not in response:
            results[qid] = {"kind": kind, "question": item["question"], "verdict": "ERROR", "detail": str(response)[:200]}
            continue
        scored = score_answerable(item, response, source) if kind == "answerable" else score_trick(response) if kind == "trick" else score_near_miss(response)
        results[qid] = {"kind": kind, "question": item["question"], **scored}
    for qid, (kind, item) in questions.items():
        if qid not in seen:
            results[qid] = {"kind": kind, "question": item["question"], "verdict": "NOT RUN"}
    return results


def summarise(results):
    def count(kind, verdict):
        return sum(1 for r in results.values() if r["kind"] == kind and r["verdict"] == verdict)
    ran = lambda kind: sum(1 for r in results.values() if r["kind"] == kind and r["verdict"] not in ("NOT RUN",))
    total = lambda kind: sum(1 for r in results.values() if r["kind"] == kind)
    return {
        "answerable": {"pass": count("answerable", "PASS"), "partial": count("answerable", "PARTIAL"), "miss": count("answerable", "MISS"),
                       "error": count("answerable", "ERROR"), "run": ran("answerable"), "total": total("answerable")},
        "trick": {"pass": count("trick", "PASS"), "fail": count("trick", "FAIL"), "error": count("trick", "ERROR"), "run": ran("trick"), "total": total("trick")},
        "near_miss": {"manual_review": count("near_miss", "MANUAL"), "run": ran("near_miss"), "total": total("near_miss")},
        "unverified_citations": sum(r.get("unverified_citations", 0) for r in results.values()),
    }


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    answers = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    results = score_all(answers)
    for qid, r in results.items():
        extra = ""
        if r["kind"] == "answerable" and "rules" in r:
            extra = f" (rules {r['rules']}, not matching {r['rules_not_matching']}, unverified citations {r['unverified_citations']})"
        print(f"{r['verdict']:8} {qid:5} {r['question'][:78]}{extra}")
    s = summarise(results)
    print("\nanswerable:", s["answerable"], "\ntrick:", s["trick"], "\nnear-miss:", s["near_miss"], "\nunverified citations returned:", s["unverified_citations"])
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps({"results": results, "summary": s}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
