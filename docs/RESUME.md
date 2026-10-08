# Resume notes (updated 2026-10-08)

Demo Day: **Fri 2026-10-09 / Sat 2026-10-10**. Public repo: https://github.com/vishal-sresth/codecompass

## The demo
**One company's codebase, a handful of PM-style rules questions.** Codebase: Hyperswitch (open-source payments product, standing in for "your product's code"). The second codebase (active_merchant) stays in a separate index as a later generalisation test and is not shown. Script: `docs/DEMO.md`.

## Where we are
| Stage | State |
|---|---|
| 1 to 3 | done (PRD, engineering doc, specs) |
| 4 Foundry backend | done: agent `Codecompass-agent` v6 = GPT-5 mini, file_search only, store `codecompass-hyperswitch` (894 chunks), prompt system_v1. Older versions v4/v5 and the two-codebase store are kept for rollback and comparison |
| 5 Frontend and server | done: FastAPI server (citation checker, SQLite log, parser) and Next.js page; 79 server tests + 17 scorer tests |
| 6 Features | v0.1 UI done and polished after the first user test (real source lines, plain badge, category hidden unless `?debug=1`, "show more rules" after 5) |
| 7 Evaluation | first live run on v6 done (`eval/results/hs_live_20261007_2028.json`): 11 of 12 answerable pass (the miss: right fact, wrong section), 9 of 9 absent-concept runs invent nothing, 0 unverified citations. Not done: repeats of answerable questions, a larger set, prompt v2 |
| 8 Security | not started (`/security-foundation`) |

## Next steps
1. Push to GitHub after the pre-push scan (`python scripts/prepush_scan.py --also "<employer>,<your resource names>"`), the user's yes on the file list, never committing `.env`, `.venv`, source repos, chunks, logs or `web/node_modules`.
2. Optional stability check: 2 more runs of each of the three demo questions (about 6 calls, about $0.06).
3. Record the demo; keep the recording as the fallback.
4. After Demo Day: prompt v2 (cite the connector's own section, tighter ranges, no adjacent rules), repeats of the answerable set, security plan, a second codebase.


## Working agreement (standing rules)
- Teach and partner; small steps; ask at decisions. The user asked on 2026-10-07 to move fast: keep explanations short, keep the safeguards.
- **Ask before anything that calls Azure/Foundry** (agent or model calls, uploads, eval runs, resource changes) and say roughly what it costs. The user makes Foundry portal changes; Claude drafts and verifies read-only.
- Ask before anything public (GitHub). Show the exact file list first.
- Keep `LEARNINGS.md` current. Never trust "0 matches" without a positive control and a count of files read; never report "done" from an `echo`; verify from the receiving side; check your own checks (a `pgrep -f` can match its own shell).
- Stage-gated: stop after each stage and ask.

## Environment gotchas
- Start Claude Code from VS Code's integrated terminal (`claude --continue`); an orphaned process lost folder access once (`LEARNINGS.md` 13).
- Use the project venv (`.venv/bin/python`) for anything that imports `ingest` (needs `tiktoken`). Run `brew` from the home folder. Azure auth is `az login`; GitHub is `gh` (logged in).
- Use Python (not shell grep) for searches; quote URLs with `?` in zsh. A background launcher's "completed" notice only means the launcher exited.
