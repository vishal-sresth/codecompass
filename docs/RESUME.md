# Resume notes (written 2026-10-05, end of day 1 of the build)

Demo due **Fri 2026-10-09 / Sat 2026-10-10** (Demo Day). Public repo: https://github.com/vishal-sresth/codecompass

## Where we are
| Stage | State |
|---|---|
| 1 Product definition (PRD) | done (`docs/CodeCompass_PRD.md`) |
| 2 Engineering plan | **written** (`docs/engineering/engineering-doc.md`), approved by the user |
| 3 Implementation specs | **written and tested** (`docs/specs/`, 6 files), **waiting for the user's approval** |
| 4 Foundry backend | done: agent `Codecompass-agent` v4 (GPT-5 mini, file_search only, 2,397-chunk index), prompt `prompts/system_v1.md`; prompt v2 is planned, not applied |
| 5 Frontend and server | **next**: not started |
| 6-9 features, eval, security, publish | not started (eval first run done: see `LEARNINGS.md` 15) |

## NOT yet pushed (local only)
`docs/engineering/engineering-doc.md`, `docs/specs/*`, updated `.env.example`, `LEARNINGS.md` entries 17-18, this file.
Before pushing: update the stage tables in `CLAUDE.md` and `README.md` (Stages 2 and 3 -> done), show the user the exact file list, get a yes, then commit (git identity is already set for this repo only: "Vishal Sresth" with the GitHub no-reply address; never use the Gmail) and push.

## First things to do tomorrow, in order
1. Ask the three questions that closed the last session (the stage-3 gate): (a) approve `docs/specs/`? (b) push now? (c) start Stage 5?
2. Update the stage tables, show the file list, push (with approval).
3. **Stage 5, step 0 (user does it in the Foundry portal):** agent -> Traces tab -> Connect -> create a new Application Insights resource (same resource group and region). Explain why: Traces needs it; our calls then show tokens and latency.
4. Create `repos.json` (pinned repos and SHAs shared by `ingest/ingest.py`, the checker and the server) and switch `ingest.py` to read it.
5. Run `/frontend-setup` by hand: `server/` (FastAPI skeleton + `/api/health`) and `web/` (Next.js), prove the wiring with a visible "server: ok". Check current stable versions first; do not hard-code from memory.
6. Then, in order: `/design-system` (creates `docs/design.md`; ask the user four questions), build `server/` (checker from `citation-checker.md` with the 14 fixtures as unit tests, storage from `storage-schema.sql`, `/api/ask`, `/api/verdict`), build the UI to `docs/spec.md` and `docs/specs/ui-states.md`.
7. First end-to-end run **with the user driving**; only then decide prompt v2.

## Open items (do not lose)
- Replace trick question **T4** (crypto was invalid; the code says `crypto_currency`) using `/verify-absence`.
- Label about 8 active_merchant answerable rules (the 12 Hyperswitch ones are in `demo/ground_truth.json`); target about 20 answerable. Trick questions run 3x each; answerable 1x.
- Prompt v2 (after the first end-to-end run): evidence without the `NN |` prefix, tightest line range, no relevance creep (adjacent facts only in answer/gaps), engineering suggestions only about things seen in results.
- The user was going to try "Is Klarna available in Germany?" in the Playground and paste the answer (does it name connectors and environments, or guess?). Not yet reported.
- Verify the Hyperswitch line of `scripts/setup_repos.sh` (the active_merchant line was tested and works).
- Check all 4 UI example-chip questions before showing them in the demo.
- Token price per question is not verified; check the deployment's pricing in the portal. Deployment quota was raised from 50K to about 201K tokens per minute.
- Add `.claude/skills` check: skills may need a Claude Code restart to appear as slash commands.
- Demo plan: three live questions (answerable, honest not-found, ambiguous), show the evidence and badges, the verdict, the log, and a Foundry trace; record a backup video.

## Working agreement (standing rules)
- Teach and partner: say what, why and what it produces; small steps; ask at decisions.
- **Ask before anything that calls Azure/Foundry** (agent or model calls, uploads, eval runs, resource changes) and say roughly what it costs. The user makes Foundry portal changes themselves; Claude drafts and verifies read-only.
- Ask before anything public (GitHub). Show the exact file list first. Never commit `.env`, `.venv`, source repos, chunks or logs.
- Keep `LEARNINGS.md` current. Never trust "0 matches" without a positive control and a count of files read; never report "done" from an `echo`; verify from the receiving side.
- Stage-gated: stop after each stage and ask.

## Environment gotchas
- Start Claude Code **from VS Code's integrated terminal** (`claude --continue`). A Claude process that became an orphan lost folder access on macOS ("Operation not permitted"): see `LEARNINGS.md` 13.
- Run `brew` from the home folder. Auth for Azure is `az login`; GitHub is `gh` (logged in as `vishal-sresth`).
- Use Python (not shell grep) for searches; quote URLs containing `?` in zsh.
- Python env: `.venv` (azure-ai-projects, azure-identity). `.env` holds names only.
