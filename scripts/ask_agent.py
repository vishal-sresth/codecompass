"""Ask the published Foundry agent a question (the same call the frontend will make)."""
import json, os, sys, time
from common import project_client


def ask(question):
    p = project_client()
    oc = p.get_openai_client()
    t = time.time()
    r = oc.responses.create(
        input=question,
        extra_body={"agent_reference": {"name": os.environ["AGENT_NAME"], "type": "agent_reference"}},
        include=["file_search_call.results"],
    )
    return r, time.time() - t


if __name__ == "__main__":
    r, secs = ask(sys.argv[1])
    print(f"Q: {sys.argv[1]}\n({secs:.0f}s, tokens in/out: {r.usage.input_tokens}/{r.usage.output_tokens})")
    try:
        print(json.dumps(json.loads(r.output_text), indent=2)[:3500])
    except Exception:
        print("[not valid JSON]\n", r.output_text[:2000])
