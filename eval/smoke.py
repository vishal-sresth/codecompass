"""Smoke test: ask questions through the running CodeCompass API (the same call the browser makes).
Calls Azure (about $0.01 per question). Usage: python eval/smoke.py [question ...]  (default: the four example chips)"""
import json, sys, time
import httpx

API = "http://127.0.0.1:8000"
EXAMPLES = [
    "Which countries does the Stripe gateway in active_merchant support?",
    "Is Klarna available in Germany in Hyperswitch?",
    "What is the refund time window enforced by the Stripe gateway in active_merchant?",
    "Which payment methods does Hyperswitch enable for India?",
]
PAUSE = 20  # seconds between questions (token quota)

def main():
    questions = sys.argv[1:] or EXAMPLES
    out = []
    for i, q in enumerate(questions):
        if i:
            time.sleep(PAUSE)
        t = time.time()
        r = httpx.post(f"{API}/api/ask", json={"question": q}, timeout=150)
        d = r.json()
        out.append({"question": q, "status": r.status_code, "result": d})
        print("=" * 100); print(f"Q: {q}\nHTTP {r.status_code} in {time.time()-t:.0f}s")
        if r.status_code != 200:
            print("  ERROR:", d); continue
        m = d["meta"]
        print(f"  agent v{m['agent_version']} prompt {m['prompt_version']} | tokens {m['input_tokens']}/{m['output_tokens']} | {m['seconds']}s | log id {d['id']}")
        print("  ANSWER:", d["answer"][:420])
        print(f"  RULES: {len(d['rules'])}  GAPS: {len(d['gaps'])}")
        for k, rule in enumerate(d["rules"][:6]):
            cits = rule["citations"]
            print(f"   [{k+1}] ({rule['category']}) {rule['rule'][:150]}")
            for c in cits[:3]:
                print(f"        {'OK ' if c['verified'] else 'NOT'} {c['repo']}:{c['file'].split('/')[-1]}:{c['line_start']}-{c['line_end']}  -> {c['verify_text']}")
        if len(d["rules"]) > 6: print(f"   ... and {len(d['rules'])-6} more rules")
        for g in d["gaps"][:2]:
            print("   GAP not_found:", g["not_found"][:200])
    json.dump(out, open("eval/results/smoke_latest.json", "w"), indent=2)

if __name__ == "__main__":
    main()
