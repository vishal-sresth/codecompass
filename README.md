# CodeCompass

**Ask plain-English questions about how your product's code works, and get answers backed by the exact lines of code.**

CodeCompass helps non-technical product managers who inherit a product they didn't build. Instead of booking an engineering meeting to learn
"why is this payment method available in one country but not another?", a PM asks in plain English and gets plain-English rules with
`file:line` citations, an automatic check that each citation really contains the claimed text, and an explicit
**"where I looked and did not find it"** section. Output is a set of candidate rules for human review, never a compliance determination.

**The demo:** one company's codebase, a handful of rules questions about it. Here the codebase is [Hyperswitch](https://github.com/juspay/hyperswitch)
(an open-source payments product, Apache-2.0), standing in for "your product's code". A second codebase ([active_merchant](https://github.com/activemerchant/active_merchant), MIT)
is indexed separately as a generalisation test for the next stage; it is not part of the demo.

> Status: work in progress (course capstone, Demo Day 2026-10-09/10). The web app and the server are built and run locally (v0.1), the Foundry agent answers over the index,
> and the honesty evaluation and build log are in the repo. Not done: a larger scored evaluation, prompt v2, the security review. See [Stages](#stages).

## How it works
```
PM question -> web app (Next.js) -> local server (FastAPI) -> Azure AI Foundry agent (GPT-5 mini + File Search over an index of the code)
                                         |-> citation checker (does the cited text really sit on the cited lines?)
                                         |-> SQLite log of every request + PM verdict (Correct / Partial / Wrong)
```
- **The page:** a tagline, one question box with a small verify-before-use note under it, then the answer, the rules (each with its evidence and a verified or could-not-verify badge),
  a "where I looked and did not find it" section and verdict buttons. There are no example buttons: you type or paste the question.
  Add `?debug=1` to the address (for example `http://localhost:3000/?debug=1`) to show builder details: the server status line and, under each answer, seconds, tokens, agent version and prompt version.
- **The index:** `ingest/ingest.py` cuts the code into small chunks with a header (`REPO / COMMIT / PATH / SECTION / LINES`) and numbered lines, because File Search itself
  returns no line numbers. The `SECTION` line (for example `[pm_filters.stripe]`) keeps a rule attached to the connector it belongs to. Chunks are sized in tokens so the service never re-splits them.
- **The agent:** instructions in `prompts/system_v1.md`. It may use only File Search, never the web, and must say so when it cannot find a rule.
- **Indexed (pinned commits):** Hyperswitch's configuration files for the demo (`ingest.py --repo hyperswitch`, about 900 chunks); the two-codebase index also holds active_merchant's gateway files.
  Their code is not in this repo; `scripts/setup_repos.sh` fetches the exact versions.

## What we measured so far (small samples; treat as a starting point)
- **Honesty run on an earlier agent version:** 5 questions about things that are *not* in the code plus one near-miss. 2 clean passes; 1 question was invalid because my absence check missed the codebase's own vocabulary (`crypto_currency`);
  2 answers were honest but attached tangential rules ("relevance creep"); the citation checker caught one case of right text with wrong line numbers.
- **First live run through the real app (agent v5):** 4 of 4 questions returned valid answers; every citation the agent gave verified; 14.8K to 16.7K input tokens and 8 to 14 seconds per question; connector attribution checked by hand against the files.
- **Next:** a scored run of 12 labelled Hyperswitch questions and 3 absent-concept questions is prepared (`eval/hs_questions.json`, `eval/score_hs.py`); recall is not measured yet.
  What went wrong along the way, and how each problem was solved, is in [`LEARNINGS.md`](LEARNINGS.md).

## Stages
The project follows a gated workflow: after each stage, stop and ask. See [`CLAUDE.md`](CLAUDE.md).

| Stage | Skill / output | Status |
|---|---|---|
| 1 Product definition | `docs/CodeCompass_PRD.md` | done |
| 2 Engineering plan | `/engineering-planner` | done |
| 3 Implementation specs | `/implementation-specs` | done (`docs/specs/`) |
| 4 Foundry backend | `ingest/`, `scripts/`, `prompts/` | done (agent v6 on the Hyperswitch-only index); prompt v2 pending |
| 5 Frontend and server | `/frontend-setup` | done (`web/`, `server/`; 79 server tests + 17 scorer tests) |
| 6 Features | `/design-system` | v0.1 UI done (design tokens in `docs/design.md`); polish ongoing |
| 7 Evaluation | `/honesty-eval`, `/verify-absence` | first live run done: 11 of 12 labelled questions pass, 9 of 9 absent-concept runs invent nothing, 0 unverified citations (small sample, one run each); larger set pending |
| 8 Security | `/security-foundation` | not started |

Skills live in [`skills/`](skills/) and are linked at `.claude/skills` so Claude Code can run them as slash commands.

## Run it
Needs an Azure subscription with a Foundry project, a deployed chat model and `text-embedding-3-small`, the Azure CLI, Node.js and Python 3.
```bash
az login
cp .env.example .env                       # fill in your project endpoint and names (no keys)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
bash scripts/setup_repos.sh                # pinned source repos
python ingest/ingest.py --repo hyperswitch --out ingest/out_hs
python ingest/verify_chunks.py --out ingest/out_hs          # headers, line numbers, coverage, chunk size
python scripts/upload_chunks.py --name my-index --chunks ingest/out_hs/chunks   # calls Azure: creates a vector store (a few cents)
```
Then create an agent in the Foundry portal, paste `prompts/system_v1.md` as its instructions, attach the vector store to File Search, and make sure there is no web-search tool.
Start the app in two terminals: `uvicorn server.main:app --host 127.0.0.1 --port 8000` and `cd web && npm install && npm run dev`, then open `http://localhost:3000`.
Uploading and asking questions cost Azure credit, and the agent's tokens-per-minute quota matters (see learning 16).

## Layout
`docs/` PRD, spec, design, engineering, security, demo script | `skills/` slash-command skills | `prompts/` agent prompts | `ingest/` chunker and verifier | `scripts/` Foundry helpers |
`server/` FastAPI (checker, storage, API) | `web/` Next.js app | `eval/` question sets, scorer, results | `demo/` earlier terminal demo | `LEARNINGS.md` build log of problems and fixes.

## Credits and licenses
- Built as a capstone for the AI PM course taught by Mahesh Yadav (Maven).
- The stage-gated workflow and skills-as-slash-commands structure are inspired by [sachin0034-tech/dev-os](https://github.com/sachin0034-tech/dev-os). The skills in this repo are written fresh for this project.
- This repository is MIT-licensed ([`LICENSE`](LICENSE)). The indexed third-party projects keep their own licenses.

## Disclaimer
CodeCompass output is candidate information for review. Verify before using in PRDs, launches or compliance decisions.
