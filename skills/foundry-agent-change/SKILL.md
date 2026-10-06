---
name: foundry-agent-change
description: The checklist for changing the CodeCompass Foundry agent (instructions, tools, knowledge store, quota) so the user learns the portal and every change is verified and recorded. Use whenever the agent's prompt, tools, vector store or deployment quota must change.
---

# Foundry agent change

The user wants to learn the Foundry portal, so **the user makes the change in the portal; Claude drafts the text and verifies afterwards.** Do not change the agent by script when a portal step would teach something.

## Steps
1. **Why:** state the problem and the evidence (a `LEARNINGS.md` entry or an eval result). One change at a time so the effect can be measured.
2. **Draft** the new text in the repo first (`prompts/system_v2.md`), and explain each added rule and which failure it targets.
3. **Portal steps for the user**, with exact clicks: Build -> Agents -> `Codecompass-agent` -> Playground (Instructions and Tools) -> Save. Saving creates a new version; older versions remain, which is the rollback path.
   - Other places: Quota page for tokens per minute; Traces and Monitor for usage (needs Application Insights connected); Models for deployments.
4. **Verify read-only** (ask before running, since it calls Azure): fetch the latest agent version and compare: version number, model, tool list (only `file_search`; no `web_search`), vector store ID and file count, and that the instructions are identical to the file in `prompts/`.
5. **Test** with `/honesty-eval` after asking; compare with the previous version on the same questions.
6. **Record:** add the version, the change and the result to `LEARNINGS.md`. If worse, tell the user how to roll back (re-save the previous instructions as the newest version).

## Never
Add web search or any tool without the user's explicit decision; put keys in prompts; change two things at once.
