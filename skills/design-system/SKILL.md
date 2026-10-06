---
name: design-system
description: Creates docs/design.md for CodeCompass if it is missing, and enforces it on every piece of UI code (colors, type, spacing, badges, states, accessibility). Use whenever building or styling any screen, component or page, or when the user says "follow the design system" or "make it look right".
---

# Design system

`docs/design.md` is the single source of truth for visual decisions. Use only values defined there. Never hard-code a color, size or spacing value in a component.

## If `docs/design.md` does not exist
Ask the user four questions with `AskUserQuestion`: (1) the feel of the product (calm and trustworthy, or bold?), (2) brand colors or a reference, (3) type preference, (4) light, dark or both. Then write it.

## `docs/design.md` must contain
- Color tokens: surface, text, border, brand, and **semantic** (verified = green, unverified = amber, error = red, info = blue). Semantic colors always come with a text label and an icon, never color alone.
- Type scale and font families; a monospace style for code and evidence boxes.
- Spacing scale and page layout (one column, max width, panel order from `docs/spec.md` section 3).
- Components: question box, example chips, answer panel, rule card, citation line, evidence code box, verification badge, gaps panel, verdict buttons, status bar, loading and error states.
- Motion: durations and easing; respect reduced-motion.
- Accessibility: WCAG AA contrast (4.5:1 for text), visible focus states, full keyboard use, ARIA live region for the loading and result changes.
- The disclosure banner text and where it sits.

## Applying it
For each UI task: read `docs/design.md`, reference tokens by name, render all agent text as **plain text** (never inject it as HTML), and check keyboard focus and contrast before saying it is done.

## Gate
After creating or changing `docs/design.md`, stop and ask the user to review it before building UI against it.
