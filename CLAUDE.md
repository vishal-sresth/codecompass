# CodeCompass: Claude Code project guide

CodeCompass lets a non-technical PM ask what business rules a codebase enforces (first: which payment methods are available in which countries)
and returns plain-English rules with **verifiable file:line citations**, plus an honest "where I looked and did not find it" section.
The brain is an Azure AI Foundry agent; this app is a thin shell around it. Course capstone (AI PM course). Demo due 2026-10-10.
**Demo scope: ONE company's codebase (Hyperswitch) with PM-style rules questions.** The second codebase (active_merchant) lives in a separate index as a later generalisation test and is not shown in the demo.

Workflow style inspired by [sachin0034-tech/dev-os](https://github.com/sachin0034-tech/dev-os) (staged, approval-gated, skills as slash commands).

---

## Core rule: stages are gated
**After completing any stage, stop. Present what was produced. Ask the user if they are happy to proceed to the next stage.** No exceptions.
- Work in small steps; say what you are about to do, why, and what it produces. Ask at real decision points.
- **Never run anything that calls Azure/Foundry** (agent or model calls, uploads, creating/changing resources, eval runs) **without asking first**, and say roughly what it costs.
  Reading local files and running local scripts needs no asking.
- Anything outward-facing (GitHub push, publish, sharing) needs an explicit yes with the exact file list shown first.
- Use `AskUserQuestion` for unclear architectural decisions. Do not assume.

## The stages
| # | Stage | Skill / output | Status |
|---|---|---|---|
| 1 | Product definition | `docs/CodeCompass_PRD.md` | done (PRD Weeks 1-4) |
| 2 | Engineering plan | `/engineering-planner` -> `docs/engineering/engineering-doc.md` | done |
| 3 | Implementation specs | `/implementation-specs` -> `docs/specs/`, `.env.example` | done (tested, approved) |
| 4 | Foundry backend (index + agent) | `ingest/`, `scripts/`, `prompts/`; agent `Codecompass-agent` v6 on the Hyperswitch-only store `codecompass-hyperswitch` (894 chunks) | done; prompt v2 pending |
| 5 | Frontend setup | `/frontend-setup` -> `web/` (Next.js) and `server/` (FastAPI) | done (79 server tests + 17 scorer tests) |
| 6 | Feature implementation | build to `docs/spec.md`; apply `/design-system` to all UI | v0.1 UI done; polish ongoing |
| 7 | Evaluation | `/honesty-eval`, `/verify-absence` -> `eval/results/` | live run done on v6: 11 of 12 answerable pass, 9 of 9 absent-concept runs pass, 0 unverified citations; larger set and repeats pending |
| 8 | Security | `/security-foundation` -> `docs/security/security-plan.md` | not started |
| 9 | Run and publish | local demo; GitHub release | not started |

Skills live in `skills/<name>/SKILL.md`. Our own: `/verify-absence`, `/honesty-eval`, `/foundry-agent-change`.

## Architecture (decided)
- Browser: Next.js on localhost:3000 -> FastAPI on localhost:8000 (`server/`) -> Foundry agent `Codecompass-agent` (GPT-5 mini, file_search only).
- The Foundry index holds 2,397 line-numbered chunks (`ingest/out/chunks/`, regenerate with `ingest/ingest.py`). Each chunk carries REPO / COMMIT / PATH / SECTION / LINES so the agent can cite lines.
- Source repos (pinned, for the citation checker; recreate with `scripts/setup_repos.sh`): `hyperswitch/` and `repos/active_merchant/`.
- Auth: `az login` (DefaultAzureCredential). No keys in files or in the browser. `.env` holds non-secret names only (see `.env.example`).
- The agent is the only source of answers: no web search, no outside knowledge. System prompt: `prompts/system_v1.md`.

## Rules for the code
- Show the agent's answer as returned; only add a verification badge. Unverified rules are shown, flagged amber, never hidden.
- Handle: rate limiting (429), slow answers (15-35 s), invalid JSON, empty `rules`.
- Citation checker: strip any leading `NN |` prefix from evidence, compare whitespace-normalised, require the text on the cited lines; if found elsewhere in the file, mark not verified with a note.
- Match surrounding style; keep it simple; build only what `docs/spec.md` asks for.

## Verification habits (learned the hard way, see `LEARNINGS.md`)
- A search that returns "0 matches" proves nothing until a **positive control** (a term known to be present) returns more than 0 and the number of files read is printed.
- Match whole words and read the hits; substrings fool you (`ofac` inside `PagoFacil`).
- Absence checks must use the codebase's own vocabulary (`crypto_currency`, not "bitcoin").
- Read a written file back; never report "logged/done" from an `echo`.
- Score honesty runs in three buckets: fabricated rule, relevant-but-tangential rule, bad citation. They need different fixes.
- Keep `LEARNINGS.md` current: add an entry whenever something goes wrong or surprises us.

## Layout
`docs/` PRD, spec, design, engineering, security | `skills/` slash commands | `prompts/` agent system prompts | `ingest/` chunker | `scripts/` Foundry helpers |
`eval/` question sets (`hs_questions.json`), scorer (`score_hs.py`), runners, results | `logs/` local SQLite log of every request | `server/` FastAPI | `web/` Next.js | `demo/` terminal demo | `LEARNINGS.md` build log.

## Commands
- Python env: `python3 -m venv .venv && source .venv/bin/activate && pip install azure-ai-projects azure-identity fastapi uvicorn`
- Source repos: `bash scripts/setup_repos.sh`; chunks: `python ingest/ingest.py`
- Server: `uvicorn server.main:app --port 8000 --reload` | Web: `cd web && npm run dev` (port 3000)
