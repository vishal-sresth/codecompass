# CodeCompass demo app: product spec (v0.1, draft for review)

## 1. What this is
A one-screen web app where a non-technical PM asks a question about the indexed codebases (Hyperswitch config, active_merchant gateways)
and gets plain-English rules with verifiable file:line citations, plus an honest "where I looked and did not find it" section.
The brain is an Azure AI Foundry agent (`Codecompass-agent`, GPT-5 mini + File Search over a 2,397-chunk index). The app is a thin shell around it.

Demo goal (Oct 10): ask 3 questions live: one answerable, one where the honest answer is "not found", one ambiguous. Show the evidence and the cost.

## 2. Architecture (decided)
```
Browser (Next.js, localhost:3000)
   | POST /api/ask {question}
   v
Local Python server (FastAPI, localhost:8000)         <- reuses scripts/ask_agent.py and the citation checker
   | Responses API with agent_reference, auth = az login (no keys in the browser or in files)
   v
Foundry agent "Codecompass-agent" (version 4, file_search only)
   v
FastAPI parses the JSON, runs the citation checker on every citation, adds verified flags, tokens and latency
   v
Browser renders the result
```
Rules: no secrets in the browser or in git; `.env` holds only non-secret settings; the agent is the only source of answers (no web search, no outside knowledge).

## 3. The one screen
1. **Header:** "CodeCompass" and a one-line disclosure: "Candidate answers from the code. Verify before using in PRDs, launches or compliance decisions."
2. **Question box** with a Submit button and 4 example questions (answerable, absent, ambiguous, and one about a specific connector). A repo filter is out of scope for v0.1.
3. **Answer panel** (the agent's `answer`, 2-4 plain sentences).
4. **Rules panel:** one card per rule with
   - the plain-English rule and a category label (regulatory / commercial / technical / unknown);
   - citations as `repo / file : line_start-line_end`, with the evidence text in a code box;
   - a badge: **Citation verified** (green) when the cited lines contain the evidence, **Could not verify** (amber) otherwise. Never hide an unverified rule; show it with the amber badge.
5. **Gaps panel**, always visible even when empty: "Where I looked and did not find it", with `looked_in`, `not_found` and `suggested_follow_up`.
6. **Verdict buttons** under every answer (including "not found" answers): **Correct / Partial / Wrong** and an optional note. Saved state is shown ("Saved"). These labels feed the eval set.
7. **Status bar:** latency, input/output tokens, agent version. (Cost is estimated later; tokens only for now.)
8. **States:** loading (answers take 15-35 s, show elapsed seconds), empty, and errors, including a friendly message for rate limiting ("The model is busy; wait a minute and try again").

## 4. Behaviour rules (must hold)
- Never show an answer that is not valid JSON; show "The agent returned something unexpected" and a collapsed raw view.
- If `rules` is empty, say so explicitly ("No matching rule found in the indexed code") and lead with the gaps. Do not fill the space.
- Never change or "improve" the agent's text; display it as returned. Only add the verification badge.
- Remove the Foundry Playground's `[[n]]` citation markers if they ever appear in text.
- **Every request is logged automatically by the server** to a local SQLite file `logs/codecompass.db` (see section 5b): question, full result, citation checks, tokens, latency,
  agent version, prompt version, index commit SHAs, errors. The UI never decides what gets saved.
- The PM can attach a **verdict** (Correct / Wrong / Partial, plus an optional note) to the answer. A verdict updates the logged record; it never replaces it.

## 5. API contract (FastAPI)
`POST /api/ask` body `{ "question": string }` (1-500 chars) returns
```
{ "id": number,            // row id in the log, used by /api/verdict
  "answer": string,
  "rules": [{ "rule", "category", "citations": [{ "repo","file","line_start","line_end","evidence","verified": bool,"verify_note": string }], "reasoning", "all_verified": bool }],
  "gaps": [{ "looked_in": [string], "not_found": string, "suggested_follow_up": string }],
  "meta": { "seconds": number, "input_tokens": number, "output_tokens": number, "agent_version": number } }
```
Errors: `{ "error": "rate_limited" | "agent_error" | "bad_output", "message": string }` with matching HTTP codes (429, 502, 502).
`POST /api/verdict` body `{ "id": number, "verdict": "correct"|"partial"|"wrong", "note"?: string }` returns `{ ok: true }`.
`GET /api/records?limit=50` returns recent records (for the eval export). `GET /api/health` returns `{ ok: true }`.

## 5b. Storage (SQLite, decided; Supabase deferred to the Beta stage)
Table `queries`: `id` integer primary key, `ts` text (UTC ISO), `question` text, `answer` text, `rules_json` text, `gaps_json` text, `meta_json` text (seconds, tokens),
`agent_version` integer, `prompt_version` text, `index_commits_json` text, `error` text null, `verdict` text null, `verdict_note` text null, `verdict_ts` text null.
Access goes through a small interface (`save_record`, `save_verdict`, `list_records`) so the store can be swapped later. The DB file is git-ignored.
Privacy: the MVP indexes public code only; before any private repo is used, add a retention policy (see PRD Section 8).

## 6. Citation checker rules (server side)
- Resolve `repo` to its pinned local clone; the file must exist.
- Strip any leading `NN |` line-number prefix from `evidence`; compare whitespace-normalized, case-insensitive.
- Evidence must appear within lines line_start..line_end. A range off by one or two lines still counts as verified but sets `verify_note` to "range slightly loose".
- If the evidence is found elsewhere in the same file, report `verify_note: "text found at lines X-Y, not at the cited lines"` and mark it **not verified** (this is the BitPay case).

## 7. Out of scope for v0.1
Per-rule verdicts, a saved rule inventory, memory that learns from verdicts, multi-user, auth, a hosted database (Supabase), deployment, repo filter, cost in dollars, streaming.

## 8. Acceptance test (what "done" means)
1. `Which countries does the Stripe gateway in active_merchant support?` shows 1 rule with a green badge and 41 countries.
2. `What is the refund time window enforced by the Stripe gateway in active_merchant?` shows zero rules, an explicit "No matching rule found", and a filled gaps panel.
3. `Is Klarna available in Germany?` shows rules attributed to named connectors/sections, or an honest gap; never a bare yes/no.
4. A forced error (stop the server) shows a friendly message, not a blank page.
5. Clicking **Correct/Partial/Wrong** on an answer saves a verdict; the row in `logs/codecompass.db` has the verdict and the original answer intact, and a new question is also logged even if no button is pressed.
