# CodeCompass

**Ask a codebase what its business rules are, and get answers you can verify.**

CodeCompass helps non-technical product managers who inherit a product they didn't build. Instead of booking an engineering meeting to learn
"why is this payment method available in India but not Germany?", a PM asks in plain English and gets plain-English rules with
`file:line` citations, an automatic check that each citation really contains the claimed text, and an explicit
**"where I looked and did not find it"** section. Output is a set of candidate rules for human review, never a compliance determination.

> Status: work in progress (course capstone, demo 2026-10-10). The Foundry agent, the index, the honesty evaluation and the build log work today.
> The web app is the next stage and is **not built yet**. See [Stages](#stages).

## How it works
```
PM question -> web app (Next.js) -> local server (FastAPI) -> Azure AI Foundry agent (GPT-5 mini + File Search over an index of the code)
                                         |-> citation checker (does the cited text really sit on the cited lines?)
                                         |-> SQLite log of every request + PM verdict (Correct / Partial / Wrong)
```
- **The index:** `ingest/ingest.py` cuts the code into small chunks with a header (`REPO / COMMIT / PATH / SECTION / LINES`) and numbered lines, because File Search itself
  returns no line numbers. The `SECTION` line (for example `[pm_filters.stripe]`) keeps a rule attached to the connector it belongs to.
- **The agent:** instructions in `prompts/system_v1.md`. It may use only File Search, never the web, and must say so when it cannot find a rule.
- **Indexed so far (pinned commits):** [Hyperswitch](https://github.com/juspay/hyperswitch) config files (Apache-2.0) and
  [active_merchant](https://github.com/activemerchant/active_merchant) gateways (MIT). Their code is not in this repo; `scripts/setup_repos.sh` fetches the exact versions.

## What we measured so far (honest numbers)
First honesty run on agent v4 (5 questions about things that are *not* in the code, plus one near-miss): 2 clean passes (sanctions, refund window);
1 question turned out to be invalid because my absence check missed the codebase's own vocabulary (`crypto_currency`); 2 answers were honest but attached
tangential rules ("relevance creep"); the citation checker caught one case of right text with wrong line numbers. Details and what we changed are in [`LEARNINGS.md`](LEARNINGS.md).
Numbers are from a small sample and will move; treat them as a starting point.

## Stages
The project follows a gated workflow: after each stage, stop and ask. See [`CLAUDE.md`](CLAUDE.md).

| Stage | Skill / output | Status |
|---|---|---|
| 1 Product definition | `docs/CodeCompass_PRD.md` | done |
| 2 Engineering plan | `/engineering-planner` | next |
| 3 Implementation specs | `/implementation-specs` | partly (`docs/spec.md`) |
| 4 Foundry backend | `ingest/`, `scripts/`, `prompts/` | done; prompt v2 pending |
| 5 Frontend and server | `/frontend-setup` | next |
| 6 Features | `/design-system` | not started |
| 7 Evaluation | `/honesty-eval`, `/verify-absence` | in progress |
| 8 Security | `/security-foundation` | not started |

Skills live in [`skills/`](skills/) and are linked at `.claude/skills` so Claude Code can run them as slash commands.

## Try the parts that exist
Needs an Azure subscription with a Foundry project, a deployed chat model and `text-embedding-3-small`, and the Azure CLI.
```bash
az login
cp .env.example .env            # fill in your project endpoint and names (no keys)
python3 -m venv .venv && source .venv/bin/activate
pip install azure-ai-projects azure-identity
bash scripts/setup_repos.sh     # pinned source repos
python ingest/ingest.py         # builds chunks in ingest/out/
python scripts/upload_chunks.py --name my-index   # calls Azure: creates a vector store (several hours for ~2,400 files at the rate we saw)
```
Then create an agent in the Foundry portal, paste `prompts/system_v1.md` as its instructions, attach the vector store to File Search, and remove any web-search tool.
Uploading and asking questions cost Azure credit; the agent's token quota matters (see learning 16).

## Layout
`docs/` PRD, spec, engineering and security docs | `skills/` slash-command skills | `prompts/` agent prompts | `ingest/` chunker | `scripts/` Foundry helpers |
`eval/` trick questions, runners, results | `demo/` earlier terminal demo | `LEARNINGS.md` build log of problems and fixes.

## Credits and licenses
- Built as a capstone for the AI PM course taught by Mahesh Yadav (Maven).
- The stage-gated workflow and skills-as-slash-commands structure are inspired by [sachin0034-tech/dev-os](https://github.com/sachin0034-tech/dev-os). The skills in this repo are written fresh for this project.
- This repository is MIT-licensed ([`LICENSE`](LICENSE)). The indexed third-party projects keep their own licenses.

## Disclaimer
CodeCompass output is candidate information for review. Verify before using in PRDs, launches or compliance decisions.
