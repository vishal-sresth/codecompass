# UI states

One page, one column. Panels in order: disclosure, question, answer, rules, gaps, verdict, status bar. All agent text is rendered as plain text (never HTML). Styling comes only from `docs/design.md`.
Colour is never the only signal: every state has a text label and an icon.

## Page-level states
| State | Trigger | What the user sees | Behaviour |
|---|---|---|---|
| Idle | page load | Disclosure banner; question box; four example chips; empty result area | Submit disabled until the question has at least 1 non-space character; counter "0/500" |
| Loading | after Submit | Spinner and "Asking the agent... 12 s" (elapsed seconds, updates every second); Submit and chips disabled | Announced to screen readers (`aria-live="polite"`). After 45 s add "Still working. Answers can take up to a minute." |
| Result with rules | `200`, `rules` not empty | Answer; one card per rule; gaps panel; verdict buttons; status bar | Focus moves to the answer heading |
| Result without rules | `200`, `rules` empty | Answer; **"No matching rule found in the indexed code."**; gaps panel first and expanded; verdict buttons; status bar | Presented as a normal result, not an error. Do not fill the space with other content |
| Busy / rate limited | `429` | "The model is busy. Wait about {retry_after} s and try again." | Submit re-enabled after the countdown; the question text is kept |
| Invalid input | `422 invalid_input` | Message under the question box ("Questions can be 1 to 500 characters.") | Focus returns to the question box |
| Unsafe input | `422 unsafe_input` | "That question looks like an instruction to the assistant, not a question about the code. Please rephrase." | Question kept |
| Agent error | `502 agent_error` | "The agent could not be reached. Try again in a moment." | Retry button |
| Bad output | `502 bad_output` | "The agent returned something unexpected." and a collapsed "Show raw reply" | Raw reply in a code block (plain text) |
| Server down | network error | "Can't reach the CodeCompass server. Is it running on port 8000?" | Retry button; never a blank page |

## Rule card
- Rule statement; category label ("Regulatory", "Commercial", "Technical", "Unknown") with a small icon.
- Citations: `repo / file : line_start-line_end`; the evidence in a monospace box (plain text, horizontally scrollable).
- **Badge per citation:**
  - Green with a check and "Citation verified" when `verified` is true. If notes include `range_loose`, `range_off_by_N`, `truncated` or `prefix_stripped`, add the small note text beside it.
  - Amber with a warning icon and "Could not verify" when `verified` is false, followed by `verify_text` (for example "the text is in this file at lines 1003-1004, not at the cited lines").
- A rule whose citations are not all verified keeps its amber badge and is **never hidden or collapsed away**.
- "Reasoning" is a collapsed line the user can expand.

## Gaps panel
Always rendered, even with no gaps (then it says "No gaps reported."). Per gap: "Where I looked" (list), "What I did not find", "Suggested follow-up for engineering".

## Verdict buttons
Three buttons under every result (including "not found" results): **Correct**, **Partial**, **Wrong**, and an optional note field (max 1000). After clicking: the chosen button is shown as selected, the text "Saved" appears, the buttons stay enabled so the user can change their mind.
Error case: "Could not save your verdict. Try again." (the answer is already logged either way).

## Status bar
`{seconds} s | {input_tokens} in / {output_tokens} out tokens | agent v{agent_version} | prompt {prompt_version}`. If a value is null show "n/a".

## Disclosure banner (always visible)
"Candidate answers from the code. Verify before using in PRDs, launches or compliance decisions."

## Example chips (clicking fills the question box, does not submit)
1. "Which countries does the Stripe gateway in active_merchant support?" (answerable)
2. "Is Klarna available in Germany in Hyperswitch?" (needs the connector named)
3. "What is the refund time window enforced by the Stripe gateway in active_merchant?" (honest not-found)
4. "Which payment methods does Hyperswitch enable for India?" (broader)
The chips should be reviewed before the demo; do not show a question whose result has not been checked.

## Accessibility
Keyboard-only operation of every control; visible focus; WCAG AA contrast; live region for loading and results; buttons have text labels; reduced-motion respected.
