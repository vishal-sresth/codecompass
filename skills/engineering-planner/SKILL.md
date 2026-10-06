---
name: engineering-planner
description: Turns the CodeCompass PRD and spec into one engineering document (high-level design) covering architecture, the Foundry agent, storage, API, folder layout and testing, before any app code is written. Use at Stage 2, or when the user says "engineering plan", "high-level design" or "architecture".
---

# Engineering Planner

## Input
`docs/CodeCompass_PRD.md` and `docs/spec.md` (read both fully). If either is missing, stop and ask.

## Steps
1. Extract functional and non-functional requirements, and list gaps or contradictions between the PRD and the spec.
2. For any real architectural ambiguity, ask the user with `AskUserQuestion` before writing (auth method, where to run, storage, model). Do not assume.
3. Write `docs/engineering/engineering-doc.md` with these sections. Every statement concrete, no "TBD".
   1. Summary and success metrics (from the PRD: precision, recall, citation accuracy, hallucination, gap honesty, latency)
   2. Scope: in and out (match `docs/spec.md` section 7)
   3. Users and flows (ask, answer, verify, verdict)
   4. Frontend architecture (Next.js, screen states, how errors are shown)
   5. Backend architecture (FastAPI, endpoints, citation checker, logging)
   6. AI architecture: Foundry project, agent name and version, model, tool (file_search only), vector store, prompt file and version, JSON output schema, how a prompt change is made and verified
   7. Data: the index (chunks, headers) and the SQLite log (tables, fields)
   8. API specification (request and response shapes, error codes)
   9. Folder structure and naming conventions
   10. Evaluation strategy: ground truth, trick questions, repeated runs, scoring buckets, pacing against the token quota
   11. Security and privacy notes (feeds `/security-foundation`)
   12. Cost and quota (tokens per question, tokens-per-minute limit, estimated spend)
   13. Spec-to-implementation mapping (each spec section -> files)
4. Include a diagram (ASCII or Mermaid) of browser -> server -> Foundry agent -> checker -> log.

## Output
`docs/engineering/engineering-doc.md` only.

## Gate
Stop. Summarise the document in 10 lines, list open questions, and ask the user whether to proceed to `/implementation-specs`.
