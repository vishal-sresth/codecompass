#!/usr/bin/env python3
"""CodeCompass demo: PM question -> cited rules + gaps -> citation check -> PM verdict.

Agent = headless Claude Code (`claude -p`) with read-only tools (Read/Grep/Glob) on the Hyperswitch repo.

  python3 codecompass.py ask "Why is Klarna on Stripe available in Germany but not India?" [--verify] [--plain] [--replay]
  python3 codecompass.py eval          # runs all questions, saves results/eval.json
  python3 codecompass.py scoreboard    # prints saved eval results
"""
import json, os, re, subprocess, sys, time, hashlib
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(os.path.dirname(HERE), "hyperswitch")
RES = os.path.join(HERE, "results")
os.makedirs(os.path.join(RES, "answers"), exist_ok=True)

# ---------------------------------------------------------------- prompts ---
SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "rules": {"type": "array", "items": {"type": "object", "properties": {
            "statement": {"type": "string"},
            "category": {"type": "string", "enum": ["regulatory", "commercial", "technical", "unknown"]},
            "connector": {"type": "string"},
            "payment_method": {"type": "string"},
            "countries": {"type": "array", "items": {"type": "string"}},
            "currencies": {"type": "array", "items": {"type": "string"}},
            "citations": {"type": "array", "items": {"type": "object", "properties": {
                "file": {"type": "string"}, "line_start": {"type": "integer"},
                "line_end": {"type": "integer"}, "quote": {"type": "string"}},
                "required": ["file", "line_start", "line_end", "quote"]}},
            "reasoning": {"type": "string"}},
            "required": ["statement", "category", "connector", "payment_method", "countries", "currencies", "citations", "reasoning"]}},
        "gaps": {"type": "array", "items": {"type": "object", "properties": {
            "looked_in": {"type": "array", "items": {"type": "string"}},
            "not_found": {"type": "string"},
            "ask_engineering": {"type": "string"}},
            "required": ["looked_in", "not_found", "ask_engineering"]}},
    },
    "required": ["summary", "rules", "gaps"],
}

SYSTEM = """You are CodeCompass, an assistant for non-technical fintech product managers.
You answer questions about which payment features are available where, using ONLY the Hyperswitch
repository in the current directory. Payment-method availability by connector, country and currency is
mostly declared in config/*.toml under [pm_filters.<connector>] sections.

Rules:
- Return plain-English rules a PM can read. Each rule must have at least one citation: repo-relative file,
  line_start, line_end (keep the range to a few lines) and `quote` = the first 60 characters of the cited
  line, copied exactly.
- Make ONE rule per config entry (e.g. one rule for stripe/klarna), and put the entry's COMPLETE country and
  currency lists in it. Do not split an entry into per-country rules; explain specific countries (e.g. why
  Germany yes, India no) in the statement text. If an entry lists only a currency, countries is [].
- Fill connector, payment_method (the config key, e.g. klarna), countries and currencies (ISO codes exactly
  as listed in the config for that entry; use [] if the entry lists none).
- category: regulatory / commercial / technical / unknown. Config rarely says WHY a rule exists; if the
  reason is not stated in the code, use "unknown" and say so in gaps. Never invent a reason.
- gaps: every answer must say where you looked and what you did NOT find (e.g. no stated reason, no amount
  limits). If the question assumes a rule that does not exist in the repo, return rules: [] and explain in gaps.
- Never answer from memory. If you cannot find it in the files, it is a gap."""

SYSTEM_PLAIN = """You are an assistant for non-technical fintech PMs. You cannot access any repository in this
conversation. Answer the question about the Hyperswitch payments codebase as best you can and fill the same
JSON structure, including your best-guess file path, line numbers and quote for each rule."""

# ----------------------------------------------------------------- agent ---
def run_claude(question, plain=False):
    cmd = ["claude", "-p", question, "--output-format", "json", "--json-schema", json.dumps(SCHEMA),
           "--no-session-persistence", "--append-system-prompt", SYSTEM_PLAIN if plain else SYSTEM]
    if plain:
        cmd += ["--tools", "", "--max-turns", "3"]
    else:
        cmd += ["--tools", "Read,Grep,Glob", "--allowedTools", "Read,Grep,Glob", "--max-turns", "20"]
    t0 = time.time()
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=300)
    secs = time.time() - t0
    try:
        d = json.loads(p.stdout)
    except Exception:
        return {"error": (p.stdout + p.stderr)[-500:], "secs": secs}
    out = d.get("structured_output")
    if out is None:
        txt = re.sub(r"^```(?:json)?|```$", "", (d.get("result") or "").strip(), flags=re.M).strip()
        try:
            out = json.loads(txt)
        except Exception:
            return {"error": "unparseable: " + txt[:300], "secs": secs}
    u = d.get("usage", {})
    out["_meta"] = {"secs": round(secs, 1), "turns": d.get("num_turns"), "cost_usd": d.get("total_cost_usd"),
                    "tokens": (u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                               + u.get("cache_read_input_tokens", 0) + u.get("output_tokens", 0)),
                    "model": list((d.get("modelUsage") or {}).keys())}
    return out

# --------------------------------------------------------------- checker ---
def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()

def check_rule(rule):
    """Deterministic: do the cited lines exist, contain the quote, and contain every country/currency claimed?"""
    cites = rule.get("citations") or []
    if not cites:
        return False, "no citation"
    blob = ""
    for c in cites:
        path = os.path.realpath(os.path.join(REPO, c["file"]))
        if not path.startswith(os.path.realpath(REPO) + os.sep) or not os.path.isfile(path):
            return False, f"file not found: {c['file']}"
        lines = open(path, errors="replace").read().splitlines()
        a, b = c["line_start"], c["line_end"]
        if a < 1 or b < a or b > len(lines) or b - a > 40:
            return False, f"bad line range {c['file']}:{a}-{b}"
        text = " ".join(lines[a - 1:b])
        if norm(c["quote"]) not in norm(text):
            return False, f"quote not found at {c['file']}:{a}-{b}"
        blob += " " + text
    for v in (rule.get("countries") or []) + (rule.get("currencies") or []):
        if not re.search(r"(?<![A-Za-z])" + re.escape(v) + r"(?![A-Za-z])", blob):
            return False, f"value '{v}' not in cited lines"
    return True, "ok"

def annotate(ans):
    for r in ans.get("rules", []):
        r["_ok"], r["_why"] = check_rule(r)
    return ans

# ----------------------------------------------------------- ground truth ---
def load_gt():
    return json.load(open(os.path.join(HERE, "ground_truth.json")))

def same(a, b):
    f = lambda xs: {x.strip().upper() for x in xs if x.strip()}
    return f(a) == f(b)

def rule_matches(rule, g):
    return (rule.get("connector", "").lower() == g["connector"] and rule.get("payment_method", "").lower() == g["payment_method"]
            and same(rule.get("countries", []), g["countries"]) and same(rule.get("currencies", []), g["currencies"]))

# ---------------------------------------------------------------- display ---
B, D, G, R, Y, C, X = "\033[1m", "\033[2m", "\033[32m", "\033[31m", "\033[33m", "\033[36m", "\033[0m"

def slug(q):
    return hashlib.md5(q.encode()).hexdigest()[:10]

def verdicts():
    p = os.path.join(RES, "verdicts.json")
    return json.load(open(p)) if os.path.exists(p) else {}

def show(ans, q):
    print(f"\n{B}PM question:{X} {q}\n")
    print(f"{B}Answer:{X} {ans.get('summary','')}\n")
    vs = verdicts()
    rules = ans.get("rules", [])
    if not rules:
        print(f"{Y}No supporting rule found in the repo.{X}\n")
    for i, r in enumerate(rules, 1):
        badge = f"{G}✔ citation verified{X}" if r["_ok"] else f"{R}✘ citation FAILED ({r['_why']}) - dropped{X}"
        print(f"{B}Rule {i}{X}  [{C}{r['category']}{X}]  {badge}")
        print(f"  {r['statement']}")
        for c in r.get("citations", []):
            print(f"  {D}{c['file']}:{c['line_start']}-{c['line_end']}{X}")
        print(f"  {D}why I think so: {r['reasoning']}{X}")
        v = vs.get(f"{r['connector']}|{r['payment_method']}")
        if v:
            print(f"  {G}PM-verified earlier: {v['verdict']}{X} {D}{v.get('note','')}{X}")
        print()
    gaps = ans.get("gaps", [])
    print(f"{B}{Y}Where I looked and did NOT find an answer{X}")
    for g in gaps:
        print(f"  - {g['not_found']}")
        print(f"    {D}looked in: {', '.join(g['looked_in'])}{X}")
        print(f"    {Y}ask engineering:{X} {g['ask_engineering']}")
    if not gaps:
        print("  (none reported)")
    m = ans.get("_meta", {})
    print(f"\n{D}{m.get('secs')}s, {m.get('turns')} turns, {m.get('tokens')} tokens, ${(m.get('cost_usd') or 0):.2f}{X}\n")

def verify(ans):
    vs = verdicts()
    for i, r in enumerate([r for r in ans.get("rules", []) if r["_ok"]], 1):
        k = f"{r['connector']}|{r['payment_method']}"
        a = input(f"Rule '{r['connector']} {r['payment_method']}': [c]orrect / [w]rong / [p]artial / [s]kip? ").strip().lower()
        if a and a[0] in "cwp":
            note = input("  note (optional): ")
            vs[k] = {"verdict": {"c": "Correct", "w": "Wrong", "p": "Partial"}[a[0]], "note": note, "at": time.strftime("%F %T")}
    json.dump(vs, open(os.path.join(RES, "verdicts.json"), "w"), indent=2)
    print("saved. Ask again to see the verified badge.")

# ------------------------------------------------------------------- eval ---
def eval_one(item):
    q, plain = item["question"], item["plain"]
    ans = run_claude(q, plain=plain)
    return {"id": item["id"], "plain": plain, "answer": annotate(ans) if "error" not in ans else ans}

def score(results, gt):
    out = {}
    for mode in ("plain", "agent", "agent+checker"):
        rets = tp = cited = cited_ok = found = 0
        trick_ok = 0
        tok, secs, n = 0, 0, 0
        for g in gt["rules"] + gt["tricks"]:
            rec = next((x for x in results if x["id"] == g["id"] and x["plain"] == (mode == "plain")), None)
            if not rec or "error" in rec["answer"]:
                continue
            a = rec["answer"]
            rules = a.get("rules", [])
            if mode == "agent+checker":
                rules = [r for r in rules if r["_ok"]]
            m = a.get("_meta", {})
            tok += m.get("tokens", 0); secs += m.get("secs", 0); n += 1
            if g["id"].startswith("T"):
                trick_ok += int(len(rules) == 0 and len(a.get("gaps", [])) > 0)
                continue
            rets += len(rules)
            hit = [r for r in rules if rule_matches(r, g)]
            tp += len(hit); found += int(bool(hit))
            cited += len(rules); cited_ok += sum(r["_ok"] for r in rules)
        out[mode] = {"precision": tp / rets if rets else 0, "recall": found / len(gt["rules"]),
                     "citation_acc": cited_ok / cited if cited else 0, "hallucination": 1 - (cited_ok / cited) if cited else 0,
                     "tricks": f"{trick_ok}/{len(gt['tricks'])}", "tokens_per_q": tok // max(n, 1), "secs_per_q": round(secs / max(n, 1), 1)}
    return out

def scoreboard():
    p = os.path.join(RES, "eval.json")
    if not os.path.exists(p):
        sys.exit("no results/eval.json yet - run: python3 codecompass.py eval")
    s = json.load(open(p))["scores"]
    names = {"plain": "Plain LLM (no repo)", "agent": "Agent (raw)", "agent+checker": "Agent + citation checker"}
    print(f"\n{B}CodeCompass eval - Hyperswitch @ {json.load(open(p))['commit']}{X}")
    hdr = f"{'':28}{'Precision':>10}{'Recall':>8}{'Citation':>9}{'Halluc.':>9}{'Tricks':>8}{'Tok/q':>9}{'s/q':>6}"
    print(hdr); print("-" * len(hdr))
    for k in ("plain", "agent", "agent+checker"):
        v = s[k]
        print(f"{names[k]:28}{v['precision']:>10.0%}{v['recall']:>8.0%}{v['citation_acc']:>9.0%}{v['hallucination']:>9.0%}{v['tricks']:>8}{v['tokens_per_q']:>9}{v['secs_per_q']:>6}")
    print(f"\n{D}Targets: precision >80%, recall >60%, citation >90%, hallucination <5%, tricks all passed{X}\n")

def run_eval():
    gt = load_gt()
    jobs = []
    for g in gt["rules"] + gt["tricks"]:
        for plain in (True, False):
            jobs.append({"id": g["id"], "question": g["question"], "plain": plain})
    print(f"running {len(jobs)} headless runs (4 at a time)...")
    with ThreadPoolExecutor(4) as ex:
        results = list(ex.map(eval_one, jobs))
    errs = [r for r in results if "error" in r["answer"]]
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    json.dump({"commit": commit, "results": results, "scores": score(results, gt)}, open(os.path.join(RES, "eval.json"), "w"), indent=2)
    print(f"{len(errs)} errors")
    scoreboard()

# ------------------------------------------------------------------- main ---
def main(argv):
    if not argv:
        sys.exit(__doc__)
    cmd = argv[0]
    if cmd == "ask":
        flags = [a for a in argv[1:] if a.startswith("--")]
        q = " ".join(a for a in argv[1:] if not a.startswith("--"))
        f = os.path.join(RES, "answers", slug(q + ("plain" if "--plain" in flags else "")) + ".json")
        if "--replay" in flags and os.path.exists(f):
            ans = json.load(open(f))
        else:
            print(f"{D}exploring the repo...{X}")
            ans = annotate(run_claude(q, plain="--plain" in flags))
            if "error" in ans:
                sys.exit("agent error: " + ans["error"])
            json.dump(ans, open(f, "w"), indent=2)
        show(ans, q)
        if "--verify" in flags:
            verify(ans)
    elif cmd == "eval":
        run_eval()
    elif cmd == "scoreboard":
        scoreboard()
    else:
        sys.exit(__doc__)

if __name__ == "__main__":
    main(sys.argv[1:])
