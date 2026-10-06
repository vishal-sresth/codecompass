---
name: implementation-specs
description: Converts the approved engineering document into executable specs for CodeCompass (API contract, SQLite schema, agent output contract, citation-checker rules, UI states, env template). Use at Stage 3, after the engineering doc is approved.
---

# Implementation Specs

## Input
`docs/engineering/engineering-doc.md` (approved) and `docs/spec.md`. All decisions already exist; do not re-ask them. If something is genuinely missing, say so and stop.

## Principles
Specs are self-contained, concrete and executable: SQL that runs, JSON shapes that validate, no placeholders or "TBD".

## Mandatory outputs (in `docs/specs/`)
1. `storage-schema.sql`: the SQLite `queries` table (see `docs/spec.md` 5b), indexes on `ts` and `verdict`, and a note on how `save_record`, `save_verdict` and `list_records` map to it.
2. `api-contract.md`: every endpoint with request and response JSON, status codes (200, 422 validation, 429 rate limit, 502 agent error or bad output), and examples.
3. `agent-output-contract.md`: the JSON the agent must return (answer, rules, gaps) with field rules, plus what the server does when it is invalid.
4. `citation-checker.md`: exact verification rules (resolve repo to pinned clone, strip leading `NN |`, whitespace-normalised case-insensitive match inside the cited range, found-elsewhere means not verified, loose range note) and 8+ test cases including the BitPay wrong-lines case and the Airwallex prefix case.
5. `ui-states.md`: loading (elapsed seconds), empty rules, rate-limited, invalid output, unverified-rule badge, verdict saved.
6. `.env.example` (project root): names only, grouped by service, no values, with a note that auth is `az login`.

## Optional
`eval-plan.md` if the engineering doc's evaluation section needs more detail.

## Output delivery
List each file path with a one-sentence purpose.

## Gate
Stop. Ask the user to review `docs/specs/`. Do not write application code before approval.
