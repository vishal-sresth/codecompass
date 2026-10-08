# CodeCompass design system (v0.1, defaults chosen for speed; change freely)

Feel: calm and trustworthy. A tool a careful PM relies on, not a flashy product. One column, readable, evidence first.
All values live as CSS variables at the top of `web/app/globals.css`. Components reference tokens by name; no raw colours elsewhere.

## Colour tokens (light / dark)
| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` / `--surface` | #f6f7f9 / #ffffff | #0e141b / #161d27 | page / cards |
| `--text` / `--muted` | #17202e / #475467 | #e8ecf2 / #aab4c3 | body / secondary |
| `--border` | #d0d5dd | #2b3544 | outlines |
| `--brand` | #1d4ed8 | #8fb0ff | buttons, links, focus |
| `--ok-text` on `--ok-bg` | #0b5c33 on #e4f4eb | #7fe3ab on #12301f | "Citation verified" |
| `--warn-text` on `--warn-bg` | #7a4300 on #fff1d1 | #ffd27d on #3a2c0b | "Could not verify" |
| `--err-text` on `--err-bg` | #9b1c1c on #fde8e8 | #ffa3a3 on #3a1414 | errors |
| `--code-bg` | #f1f3f6 | #0b1017 | evidence boxes |

Rule: **colour is never the only signal**. Every badge carries an icon (check, warning) and words.
Contrast target: WCAG AA (4.5:1 for text). These pairs were chosen for it; re-measure if you change them.

## Type and spacing
Body font Geist Sans (system fallback), evidence in Geist Mono at 13 px. Scale: 28 / 18 / 16 / 14 / 13 px. Spacing tokens 4 / 8 / 16 / 24 px. Radius 10 px (cards), 8 px (controls).

## Components (see `docs/specs/ui-states.md` for states and wording)
Question box with counter and a small verify-before-use note; answer card; rule card (rule, category chip, citation line, evidence box, badge, collapsible reasoning);
gaps card (always shown); verdict buttons with optional note and "Saved"; builder details (status bar, server status) only with `?debug=1`; tagline under the title.

## Accessibility
Every control works by keyboard (Ctrl or Cmd + Enter submits); visible focus ring (3 px); live regions announce loading, errors and "Saved";
focus moves to the answer heading when a result arrives; reduced-motion respected; agent text is always rendered as plain text.
