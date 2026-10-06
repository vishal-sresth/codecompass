---
name: security-foundation
description: Audits and hardens CodeCompass (credentials, API input, rate limits, prompt injection, output rendering, logging, repo hygiene) and writes docs/security/security-plan.md plus server/security/ helpers. Use at Stage 8, before publishing, or when the user says "security", "harden" or "is this safe to publish".
---

# Security foundation

## Input
`docs/engineering/engineering-doc.md`, `docs/specs/`, and the current code in `server/` and `web/`. Review them first and list every security surface.

## Surfaces and required controls
1. **Credentials:** auth is `az login` (Entra, DefaultAzureCredential). No keys in files, the browser, logs or git. `.env` holds names only; `.env.example` is the template. Confirm `.gitignore` covers `.env`, `.venv`, local DB, source repos.
2. **API input:** validate with Pydantic. `question` is required, 1-500 characters, plain text. Invalid input returns 422 with a clear message. Verdict values are a fixed set; `id` must exist.
3. **Rate limiting:** a simple per-client limit on `/api/ask` (the agent is slow and quota-limited at roughly 50-200K tokens per minute). Return 429 with `Retry-After`. Also map Foundry's own 429 to a friendly "busy, try again" message.
4. **Prompt injection:** questions are untrusted. The agent has read-only File Search and no write tools, so the blast radius is small, but still reject or flag questions that try to override instructions ("ignore previous", "reveal your system prompt") and never echo the system prompt.
5. **Output handling:** agent text is untrusted too. Render as plain text in the UI; never as HTML; never build file paths or commands from it. Validate the JSON against the contract before use.
6. **Data and logs:** the SQLite log stores questions and answers. MVP indexes public code only. Before any private repo is used, add a retention policy and access control. Never log credentials or tokens.
7. **Network:** the server listens on localhost; CORS only for `http://localhost:3000`.
8. **Dependencies:** list direct dependencies; run `pip-audit` and `npm audit` and report findings honestly.
9. **Repo hygiene before publishing:** scan every file that would be committed for employer names, emails, subscription or tenant IDs, resource names, vector store IDs and absolute local paths. **The scan needs a positive control** (a planted known string must be found) and must print the number of files read.

## Outputs
- `docs/security/security-plan.md`: surfaces, threats, controls, what was fixed and what remains, with an audit table (issue, severity, status).
- `server/security/` helpers: `input_validation.py`, `rate_limit.py`, `injection_guard.py`, `output_guard.py`.
- A `.env.example` check and the list of commands the user must run.

## Gate
Stop. Present the audit table and ask before changing existing code or publishing anything.
