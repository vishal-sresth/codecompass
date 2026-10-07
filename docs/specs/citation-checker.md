# Citation checker

Purpose: confirm that the text the agent says supports a rule really sits on the lines it cites, in the pinned source. Deterministic, no model calls.
Test fixtures with real lines from the pinned repos: `citation-checker-cases.json` (14 cases). Unit tests load that file.

## Inputs
A citation `{repo, file, line_start, line_end, evidence}` and the repo table `repos.json` (created in Stage 5):
`{"repos": [{"name": "hyperswitch", "path": "hyperswitch", "sha": "...", "url": "..."}, {"name": "active_merchant", "path": "repos/active_merchant", "sha": "...", "url": "..."}]}`.

## Output
`{verified: bool, notes: [code], found_lines: [start, end] | null}`. `verify_note` shown to the user is a plain-English rendering of the first note.

## Algorithm
1. **Resolve the repo.** Unknown name -> not verified, `unknown_repo`.
2. **Resolve the file.** Join `path` and `file`; resolve the real path; if it is outside the repo root (for example `../..`) -> not verified, `path_outside_repo`. If it is not a file -> `file_missing`.
3. **Check the range.** `1 <= line_start <= line_end <= number of lines`, else `range_invalid`.
4. **Normalise the evidence.** Per line, strip a leading `^\s*\d+\s*\|\s?` (a line-number prefix copied from the index). Join lines with one space, collapse whitespace, lowercase.
   If it ends with `...` or `…`, remove that ending and add the note `truncated`. If fewer than **8** characters remain -> `evidence_too_short`.
5. **Normalise the file the same way** (per line: collapse whitespace, lowercase; skip empty lines; join with one space) and remember each line's character span.
6. **Find the evidence as a substring** of the normalised file. Map the match start and end back to line numbers `[found_start, found_end]`.
7. **Decide:**
   - Found, and `[found_start, found_end]` lies inside `[line_start, line_end]` -> **verified**. If the cited range has extra lines beyond the match -> add note `range_loose`.
   - Found, but outside the cited range by at most **2 lines** (distance between the ranges <= 2) -> **verified**, note `range_off_by_N`.
   - Found further away -> **not verified**, note `found_elsewhere`, `found_lines` = where it really is.
   - Not found -> **not verified**, note `not_found`.
8. Search order when the text occurs several times: use the occurrence nearest to the cited range.

## Which note is "first"
A citation can carry several notes (for example `prefix_stripped` and `range_loose`). The note shown to the user, and the fixture field `first_note`, is the highest-priority one:
failure codes (`unknown_repo`, `path_outside_repo`, `file_missing`, `range_invalid`, `evidence_too_short`, `not_found`) > `found_elsewhere` > `range_off_by_N` > `prefix_stripped` > `truncated` > `range_loose` > `ok`.
All notes are stored in the log; only the top one is displayed.

## Notes and their plain-English text
| Code | Text shown |
|---|---|
| `ok` | Citation verified |
| `prefix_stripped` | Verified (a line-number prefix was ignored) |
| `truncated` | Verified (quoted text was shortened) |
| `range_loose` | Verified (cited range is slightly wider than the evidence) |
| `range_off_by_N` | Verified (lines are off by N) |
| `found_elsewhere` | Could not verify: the text is in this file at lines X-Y, not at the cited lines |
| `not_found` | Could not verify: that text is not in the cited file |
| `file_missing`, `path_outside_repo`, `unknown_repo`, `range_invalid`, `evidence_too_short` | Could not verify: (reason) |

## Rule-level result
`rule.all_verified = true` only if the rule has at least one citation and every citation is verified. A rule with no citations is `all_verified = false`, note `no_citation`. Unverified rules are **shown**, with an amber badge, never hidden.

## Required test cases
See `citation-checker-cases.json`: exact match, prefix stripped (Airwallex), loose range, off by one, found elsewhere (the BitPay case, cited at 644-645 but really at 1003-1004), truncated, text not in file, missing file, out-of-bounds range, case and whitespace differences, path traversal, too-short evidence, multi-line evidence, unknown repo.
Each case lists the expected `verified` and the first expected note. The test suite must also assert that `repos.json` SHAs match the checked-out commits (a repo at the wrong commit makes every result suspect).
