# API contract (FastAPI, `http://localhost:8000`)

All requests and responses are JSON (`Content-Type: application/json`). CORS allows only `http://localhost:3000`. No authentication in v0.1 (localhost only). Cloud credentials are never exposed to the browser.

## Error shape (every error)
```json
{ "error": "rate_limited", "message": "The model is busy. Wait a minute and try again.", "retry_after": 60 }
```
`error` is one of `invalid_input`, `unsafe_input`, `busy`, `rate_limited`, `agent_error`, `bad_output`, `not_found`. `retry_after` (seconds) appears only for `busy` and `rate_limited`.

## POST /api/ask
Request: `{ "question": "string" }`. `question` is trimmed; length 1-500; plain text only.
Success `200`:
```json
{
  "id": 17,
  "answer": "string",
  "rules": [
    {
      "rule": "string",
      "category": "regulatory | commercial | technical | unknown",
      "citations": [
        { "repo": "active_merchant", "file": "lib/active_merchant/billing/gateways/stripe.rb", "line_start": 30, "line_end": 30,
          "evidence": "string", "verified": true, "verify_notes": ["ok"], "verify_text": "Citation verified", "found_lines": [30, 30] }
      ],
      "reasoning": "string",
      "all_verified": true
    }
  ],
  "gaps": [ { "looked_in": ["string"], "not_found": "string", "suggested_follow_up": "string" } ],
  "meta": { "seconds": 14.2, "input_tokens": 17075, "output_tokens": 787, "agent_version": 4, "prompt_version": "system_v1" }
}
```
Rules:
- The agent's JSON is validated and cleaned per `agent-output-contract.md`; `verified`, `verify_notes`, `verify_text`, `found_lines` and `all_verified` are added by the server (`citation-checker.md`). Agent text is otherwise passed through unchanged.
- The request is logged (`storage-schema.sql`) **before the response is returned**, and `id` is that row's id. Failures are logged too.
- Only one agent call runs at a time. If another is running, the request waits up to **60 s** for its turn.

Errors:
| Status | `error` | When |
|---|---|---|
| 422 | `invalid_input` | missing, empty, or longer than 500 characters; wrong type |
| 422 | `unsafe_input` | matches the injection patterns defined in `docs/security/security-plan.md` (for example "ignore previous instructions", "reveal your system prompt") |
| 429 | `busy` | waited 60 s and the previous call was still running; `retry_after` 30 |
| 429 | `rate_limited` | Foundry returned 429 (tokens-per-minute quota), or the per-client limit was exceeded; `retry_after` from the upstream header, else 60 |
| 502 | `agent_error` | Foundry unreachable, timed out (90 s), or returned a non-429 error |
| 502 | `bad_output` | the agent's output cannot be parsed or validated; the raw text is kept in the log (`meta.raw`) |

## POST /api/verdict
Request: `{ "id": 17, "verdict": "correct" | "partial" | "wrong", "note": "optional, at most 1000 characters" }`.
Success `200`: `{ "ok": true }`. Updates only `verdict`, `verdict_note`, `verdict_ts`; a later call overwrites the earlier verdict, the original record is untouched.
Errors: `404 not_found` (unknown id), `422 invalid_input` (bad verdict value or note too long).

## GET /api/records
Query: `limit` (1-200, default 50), optional `verdict` (`correct|partial|wrong|none`), optional `since` (ISO-8601). Newest first.
Success `200`: `{ "records": [ { "id", "ts", "question", "answer", "rules", "gaps", "meta", "agent_version", "prompt_version", "index_commits", "error", "verdict", "verdict_note", "verdict_ts" } ] }`.
Errors: `422 invalid_input`.

## GET /api/health
`200 { "ok": true, "db": true, "agent_version": 4 }`. `agent_version` is null if the one-time startup lookup failed (the server still serves requests).

## Example: absent concept
`POST /api/ask {"question": "What is the refund time window enforced by the Stripe gateway in active_merchant?"}` ->
`200` with `"rules": []`, a filled `"gaps"`, and `answer` starting "I could not find ...". The UI must show this as a normal, honest result, not as an error.
