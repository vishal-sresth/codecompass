# CodeCompass: engineering document (high-level design) v0.1

Inputs: `docs/CodeCompass_PRD.md`, `docs/spec.md` (v0.1 with SQLite log and verdict buttons). Written by following `skills/engineering-planner`. Status: draft for approval (Stage 2 gate).

## 1. Summary and success metrics
CodeCompass answers a non-technical PM's question about what a codebase's business rules are (first: payment-method availability by country and currency) with plain-English rules,
**verifiable file:line citations**, and an explicit "where I looked and did not find it" section. The brain is an Azure AI Foundry agent over a line-numbered index of the code;
a thin local app (Next.js + FastAPI) adds the citation check, a request log and PM verdicts.

Targets (from the PRD, fixed before the runs; reported honestly, small sample):
| Metric | Target | Measured by |
|---|---|---|
| Rule precision / recall on answerable questions | >80% / >60% | eval vs hand-labelled ground truth |
| Citation accuracy | >90% | deterministic citation checker, every answer |
| Hallucination rate (rules not in the code) | <5% | checker + manual review of failures |
| Gap honesty | no fabricated rule on every trick question, all repeats | `/honesty-eval` |
| Latency | <=60 s per answer (observed 10-25 s) | server meta |

## 2. Scope
In (v0.1, demo 2026-10-10): one-screen app, ask a question, answer + rules + gaps, citation badges, Correct/Partial/Wrong verdict per answer, local SQLite log, honesty eval, build log.
Out: per-rule verdicts, rule inventory, memory that learns from verdicts, multi-user and auth, hosted database (Supabase), deployment, repo filter, dollar cost display, streaming. (Matches `docs/spec.md` section 7.)

## 3. Users and flows
- **PM (primary):** asks a question -> reads the answer -> checks the evidence and badges -> marks Correct/Partial/Wrong.
- **Builder (you):** runs evals, reads the SQLite log, changes the agent in the Foundry portal, records learnings.
Flow: `question -> POST /api/ask -> agent (File Search) -> JSON -> citation check -> log row -> UI`; later `POST /api/verdict` updates that row.

## 4. Frontend architecture (Next.js, `web/`)
App Router, TypeScript. One page. Server Components for layout; the question form, result view and verdict buttons are Client Components (`"use client"`).
Reads `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`). All agent text is rendered as plain text (never HTML). Panels in order: header + disclosure, question box + examples,
answer, rules (cards with citations and badge), gaps (always visible), verdict buttons, status bar. States: idle, loading (elapsed seconds), empty rules, rate-limited, invalid output, error. Styling only via `docs/design.md` tokens (`/design-system`).

## 5. Backend architecture (FastAPI, `server/`)
```
Browser :3000 --POST /api/ask--> FastAPI :8000 --Responses API (agent_reference, Entra via az login)--> Foundry agent
                                   |-- validate input (Pydantic)         |-- File Search over the index
                                   |-- one request at a time (semaphore)  `-- JSON {answer, rules, gaps}
                                   |-- parse + validate JSON
                                   |-- citation checker (pinned local clones)
                                   `-- SQLite log (save_record); /api/verdict updates the row
```
Modules: `main.py` (routes), `agent.py` (call + parse, reuses `scripts/ask_agent.py`), `checker.py` (citation checker, reuses `eval/run_trick.py` logic), `storage.py` (`save_record`, `save_verdict`, `list_records`),
`config.py` (repo roots and pinned SHAs, loaded from one `repos.json` shared with `ingest/ingest.py`), `security/` (from `/security-foundation`).
Concurrency: one agent call at a time (semaphore) because each call is 17-35K tokens against a tokens-per-minute quota. Foundry 429 -> our 429 with a friendly message.
Startup: read the agent's latest version once (read-only) to record `agent_version`, and compare its instructions with `prompts/*.md` to name `prompt_version` (filename if identical, else `unknown`). If that call fails, log null, keep serving.

## 6. AI architecture
- **Platform:** Azure AI Foundry project; agent `Codecompass-agent` (versioned; v4 current, v1 to v3 retained for rollback).
- **Model:** `gpt-5-mini` (Global Standard deployment, tokens-per-minute limit raised from 50K to about 200K), reasoning effort low. Embeddings for the index: `text-embedding-3-small`.
- **Tools:** `file_search` only. **No web search**, no other tool; adding one needs an explicit decision (see `/foundry-agent-change`).
- **Knowledge:** one vector store, 2,397 chunk files (about 8.4 MB), built by `ingest/ingest.py` and uploaded by `scripts/upload_chunks.py` (full upload took about 2 h 15 min).
  Chunk rules: up to 60 lines and 2,400 characters (so the service does not re-split), overlap of up to 10 lines capped at a third of the chunk, header `REPO / COMMIT / PATH / SECTION / LINES`, numbered lines.
  `SECTION` = nearest `[toml section]` or `class/module` line above the chunk, so a rule stays attached to its connector.
- **Indexed sources (pinned):** Hyperswitch `config/` (4 files; production environment preferred) and active_merchant `lib/active_merchant/billing/gateways/*.rb` (242 files).
- **Prompt:** `prompts/system_v1.md`; output is one JSON object `{answer, rules[{rule, category, citations[{repo,file,line_start,line_end,evidence}], reasoning}], gaps[{looked_in, not_found, suggested_follow_up}]}`.
  Rules: use only File Search; say so when not found; never invent; if the owning connector is unclear, put it under gaps; report conflicting values from different files separately.
- **Prompt v2 (planned, not yet applied):** quote evidence without the `NN |` prefix; cite the tightest lines; if nothing answers the question return `rules: []` and keep adjacent facts in the answer or gaps; suggestions for engineering may only point at things seen in results.
- **Change procedure:** user edits in the portal -> Claude verifies read-only -> `/honesty-eval` before and after -> log in `LEARNINGS.md`.
- **Observed cost:** 17-35K input and 0.7-2K output tokens per question; 10-25 s latency. Price per token is **not verified here**; check the deployment's pricing in the portal.

## 7. Data
- **Index:** see section 6. Regenerable with `scripts/setup_repos.sh` + `ingest/ingest.py`.
- **Log:** SQLite `logs/codecompass.db`, table `queries(id, ts, question, answer, rules_json, gaps_json, meta_json, agent_version, prompt_version, index_commits_json, error, verdict, verdict_note, verdict_ts)`.
  Every request is logged automatically, including failures; a verdict updates the row and never replaces the original. The file is git-ignored. Public code only for the MVP; a retention policy is required before any private repo.

## 8. API specification
| Endpoint | Request | Success | Errors |
|---|---|---|---|
| `POST /api/ask` | `{question: string 1-500}` | `{id, answer, rules[], gaps[], meta{seconds, input_tokens, output_tokens, agent_version, prompt_version}}`; each citation also has `verified` and `verify_note` | 422 invalid input; 429 busy/quota; 502 agent error or invalid JSON |
| `POST /api/verdict` | `{id, verdict: correct\|partial\|wrong, note?}` | `{ok: true}` | 404 unknown id; 422 |
| `GET /api/records?limit=50` | | recent rows (for eval export) | |
| `GET /api/health` | | `{ok: true}` | |
Full shapes and examples go to `docs/specs/api-contract.md` in Stage 3.

## 9. Folder structure and naming
```
docs/ (PRD, spec, engineering/, specs/, design.md, security/)   skills/ (slash-command skills; linked at .claude/skills)
prompts/ (system_v1.md, ...)   ingest/ (ingest.py)   scripts/ (Foundry helpers, setup_repos.sh)   eval/ (questions, runners, results)
server/ (FastAPI)   web/ (Next.js)   logs/ (SQLite, ignored)   demo/ (earlier terminal demo)   LEARNINGS.md   CLAUDE.md   README.md
```
Python: snake_case modules, type hints, Pydantic models. TypeScript: PascalCase components, camelCase functions. Prompts: `system_vN.md`. Eval results: `trick_YYYYMMDD_HHMM.json`, never overwritten.

## 10. Evaluation strategy
- **Answerable set (~20 rules):** the 12 labelled Hyperswitch rules in `demo/ground_truth.json` plus about 8 new active_merchant rules (expected rule, category, file:line at the pinned commit). Tune on about two thirds, hold out the rest. Single run each.
- **Trick set:** 5 questions verified absent with `/verify-absence`, plus 1 near-miss (Paymill "Country blacklisted" error message). **T4 (crypto) is withdrawn** because the code says `crypto_currency`; replace it using the codebase's vocabulary. **Each trick question runs 3 times.**
- **Scoring (three buckets):** fabricated rule / relevance creep / bad citation. Pass for an absent concept: valid JSON, empty `rules`, filled `gaps`, no invented value. Judge the verdict across repeats, not the wording.
- **Prompt comparison:** run the same set on v4 prompt and v2 prompt; adopt v2 only if fabricated and bad-citation counts do not worsen and relevance creep falls.
- **Pacing:** about 38 calls x about 28K tokens is roughly 1.1M input tokens. With a limit of about 200K tokens per minute, space calls about 15 s apart (about 10 minutes). The runner retries 429 with backoff. **Always ask the user before running.**
- **Reporting:** precision, recall, citation accuracy, hallucination rate, gap honesty, tokens and latency, with the small sample size stated.

## 11. Security and privacy notes (feeds `/security-foundation`)
No secrets in files or the browser (auth is `az login`). Validate input (1-500 chars), rate-limit, treat questions and agent output as untrusted (plain-text rendering; no paths or commands from output), localhost-only CORS,
flag injection phrases, no credentials in logs, dependency audit, pre-publish scan with positive controls. Public repos only until retention and access rules exist.

## 12. Cost and quota
Tokens per minute is the binding constraint (a first quota error occurred at 50K; now about 200K). Budget is the user's Azure credit. Application Insights (for Traces) is billed per GB ingested with a monthly free allowance (check the exact terms in the portal); our volume is tiny. Connect it when the app starts making calls.

## 13. Spec-to-implementation mapping
| Spec section | Built in |
|---|---|
| 3 One screen | `web/` page and components; `docs/design.md` |
| 4 Behaviour rules | `server/agent.py`, `server/main.py`, `web/` result view |
| 5 API contract | `server/main.py`, `docs/specs/api-contract.md` |
| 5b Storage | `server/storage.py`, `docs/specs/storage-schema.sql` |
| 6 Citation checker | `server/checker.py`, `docs/specs/citation-checker.md`, unit tests |
| 8 Acceptance test | `eval/` + a scripted smoke test + manual UI check |

## 14. Testing strategy
Unit: citation checker (at least 8 cases: exact, prefix-stripped, truncated, found-elsewhere/BitPay, loose range, missing file, out-of-bounds, case). API: validation, 429 mapping, invalid JSON, logging of failures, verdict update keeps the original. UI: the 5 acceptance checks in `docs/spec.md` section 8. Eval: `/honesty-eval` plus the answerable set. Smoke test: start both servers, one question, one verdict, read the row back.

## 15. Open questions for approval
1. Shared `repos.json` (pinned repos and SHAs used by ingest, checker and server): create it in Stage 5? (recommended)
2. When to apply prompt v2: before building the UI (cleaner demo) or after the first end-to-end run (UI as test bench)? (recommended: after)
3. Connect Application Insights at the start of Stage 5 so the first real calls show up in Traces? (recommended)
