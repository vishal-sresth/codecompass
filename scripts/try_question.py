"""Ask the model a question with File Search on a given vector store (no agent changes)."""
import sys, time
from common import project_client

VS, QUESTION = sys.argv[1], sys.argv[2]
INSTRUCTIONS = """You answer questions about code using ONLY the File Search results.
Each result starts with REPO, COMMIT, PATH, optional SECTION, LINES, then numbered lines.
Cite as repo:path:line-line using the numbered lines you actually read.
If you cannot find the rule, or cannot tell which connector/section it belongs to, say so plainly. Never guess or invent."""

oc = project_client().get_openai_client()
t = time.time()
r = oc.responses.create(
    model="gpt-5-mini",
    instructions=INSTRUCTIONS,
    input=QUESTION,
    tools=[{"type": "file_search", "vector_store_ids": [VS]}],
    include=["file_search_call.results"],
)
print(f"Q: {QUESTION}\n--- answer ({time.time()-t:.0f}s, tokens in/out: {r.usage.input_tokens}/{r.usage.output_tokens})")
print(r.output_text)
for item in r.output:
    if item.type == "file_search_call":
        print("--- searched:", item.queries)
        for x in (item.results or [])[:5]:
            print("   hit:", x.filename, round(x.score, 2))
