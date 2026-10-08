# UI states

One page, one column. Panels in order: tagline, question (with the verify-before-use note), answer, rules, gaps, verdict. Builder details (status bar, server status) only with `?debug=1`. All agent text is rendered as plain text (never HTML). Styling comes only from `docs/design.md`.
Colour is never the only signal: every state has a text label and an icon.

## Page-level states
| State | Trigger | What the user sees | Behaviour |
|---|---|---|---|
| Idle | page load | Tagline; question box with the verify-before-use note; empty result area | Submit disabled until the question has at least 1 non-space character; counter "0/500" |
| Loading | after Submit | Spinner and "Asking the agent... 12 s" (elapsed seconds, updates every second); Submit disabled | Announced to screen readers (`aria-live="polite"`). After 45 s add "Still working. Answers can take up to a minute." |
| Result with rules | `200`, `rules` not empty | Answer; one card per rule; gaps panel; verdict buttons | Focus moves to the answer heading |
| Result without rules | `200`, `rules` empty | Answer; **"No matching rule found in the indexed code."**; gaps panel first and expanded; verdict buttons | Presented as a normal result, not an error. Do not fill the space with other content |
| Busy / rate limited | `429` | "The model is busy. Wait about {retry_after} s and try again." | Submit re-enabled after the countdown; the question text is kept |
| Invalid input | `422 invalid_input` | Message under the question box ("Questions can be 1 to 500 characters.") | Focus returns to the question box |
| Unsafe input | `422 unsafe_input` | "That question looks like an instruction to the assistant, not a question about the code. Please rephrase." | Question kept |
| Agent error | `502 agent_error` | "The agent could not be reached. Try again in a moment." | Retry button |
| Bad output | `502 bad_output` | "The agent returned something unexpected." and a collapsed "Show raw reply" | Raw reply in a code block (plain text) |
| Server down | network error | "Can't reach the CodeCompass server. Is it running on port 8000?" | Retry button; never a blank page |

## Rule card
- Rule statement. The category label ("Regulatory", "Commercial", "Technical", "Unknown", with a small icon) is shown only with `?debug=1`: it is the model's guess.
- Long answers: the first 5 rules are shown, then a button "Show N more rules" reveals the rest (a new answer starts collapsed again).
- Citations: `repo / file : first-last line`; a monospace box with the **real source lines** (`source_lines`, with a line-number gutter; falls back to the agent's evidence text only if none were returned).
- **Badge per citation:**
  - Green with a check and "Citation verified" when `verified` is true. The notes (`range_loose`, `range_off_by_N`, `truncated`, `prefix_stripped`) are not shown to the PM; they appear under the badge only with `?debug=1`.
  - Amber with a warning icon and "Could not verify" when `verified` is false, followed by `verify_text` (for example "the text is in this file at lines 1003-1004, not at the cited lines").
- A rule whose citations are not all verified keeps its amber badge and is **never hidden or collapsed away**.
- "Reasoning" is a collapsed line the user can expand.

## Gaps panel
Always rendered, even with no gaps (then it says "No gaps reported."). Per gap: "Where I looked" (list), "What I did not find", "Suggested follow-up for engineering".

## Verdict buttons
Three buttons under every result (including "not found" results): **Correct**, **Partial**, **Wrong**, and an optional note field (max 1000). After clicking: the chosen button is shown as selected, the text "Saved" appears, the buttons stay enabled so the user can change their mind.
Error case: "Could not save your verdict. Try again." (the answer is already logged either way).

## Builder details (hidden unless the address has `?debug=1`)
Status bar: `{seconds} s | {input_tokens} in / {output_tokens} out tokens | agent v{agent_version} | prompt {prompt_version}` (null shown as "n/a"), plus the server-status line from `/api/health`.
The PM-facing page does not show any of this. It exists for the builder and for the "under the hood" moment of the demo.

## Tagline and verify-before-use note (always visible)
Tagline under the title: "Ask plain-English questions about how your product's code works, and get answers backed by the exact lines of code."
Note directly under the question box, small and muted, `role="note"`: "Candidate answers from the code. Verify before using in PRDs, launches or compliance decisions."

## Example questions
None in the UI. For the demo, the presenter types or pastes each question (see `docs/DEMO.md`). Do not show a question whose result has not been checked.

## Accessibility
Keyboard-only operation of every control; visible focus; WCAG AA contrast; live region for loading and results; buttons have text labels; reduced-motion respected.
