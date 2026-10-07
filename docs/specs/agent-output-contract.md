# Agent output contract

The Foundry agent must reply with **one JSON object and nothing else** (see `prompts/system_v1.md`). The server validates it before anything is shown.

## Shape
```json
{
  "answer": "string, plain English, 1-4 sentences",
  "rules": [
    {
      "rule": "string, one plain-English statement",
      "category": "regulatory | commercial | technical | unknown",
      "citations": [
        { "repo": "string", "file": "string", "line_start": 1, "line_end": 1, "evidence": "string, text copied from those lines" }
      ],
      "reasoning": "string, one sentence"
    }
  ],
  "gaps": [
    { "looked_in": ["string"], "not_found": "string", "suggested_follow_up": "string" }
  ]
}
```

## Field rules (what the server enforces)
| Field | Rule |
|---|---|
| `answer` | Required, non-empty string. |
| `rules` | Required array; may be empty. |
| `rules[].rule` | Required, non-empty. |
| `rules[].category` | One of the four values; anything else becomes `unknown` and a warning is logged. |
| `rules[].citations` | Array; a rule with no citations is kept but shown as **Could not verify** ("no citation"). |
| `citations[].line_start`, `line_end` | Integers, 1 <= start <= end. Anything else makes that citation invalid (not verified, note `range_invalid`). |
| `citations[].evidence` | Required string. Checked by the citation checker (`citation-checker.md`). |
| `gaps` | Required array; may be empty. Missing `gaps` is treated as `[]` and a warning is logged. |
| Unknown extra fields | Ignored. |

## Cleaning before parsing
1. Trim whitespace. If the text is wrapped in a Markdown code fence (```` ```json ````), remove the fence once.
2. If there is text before or after one JSON object, extract the first balanced `{ ... }` object. If none, the output is invalid.
3. Remove Playground-style citation markers matching `\[\[\d+\]\]` from every string.

## When the output is invalid
Return `502` with `{"error": "bad_output", "message": "The agent returned something unexpected."}`, **log the request** with `answer` null, `error` set, and the raw text (first 4,000 characters) stored in `meta_json.raw`. The UI shows a collapsed raw view.

## Examples
**Answerable** (one verified rule): `answer` summarises, `rules` has one item with `citations[0].file = "lib/active_merchant/billing/gateways/stripe.rb"`, `line_start = line_end = 30`, `gaps = []` or a short note.
**Not found**: `{"answer": "I could not find ...", "rules": [], "gaps": [{"looked_in": ["..."], "not_found": "...", "suggested_follow_up": "..."}]}`.
**Ambiguous**: several rules, each with a different `citations[].file` or section (connector) named in `rule`, plus a gap saying which connector or environment could not be attributed.
