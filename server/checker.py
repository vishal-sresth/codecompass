"""Citation checker (docs/specs/citation-checker.md).

Question answered: does the text the agent quotes as evidence really sit on the lines it cites, in the pinned source?
Deterministic; no model calls. Verified against docs/specs/citation-checker-cases.json by server/tests/test_checker.py.
"""
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Line-number prefixes the index puts in front of text, which an agent may copy into its evidence:
#   " 7 |  ", "653 [part 2/3] | ", and the continuation hint row ">> line 653 continues; it begins: ".
PREFIX = re.compile(r"^(?:\s*\d+(?:\s*\[part \d+/\d+\])?\s*\|\s?|>> line \d+ continues; it begins:\s*)")
MIN_EVIDENCE_CHARS = 8
OFF_BY_LIMIT = 2  # a cited range up to this many lines away from the real lines still counts as verified
SOURCE_MAX_LINES = 12   # real source lines shown to the PM per citation
SOURCE_MAX_CHARS = 200  # very long lines (country lists) are shortened for display

# Highest priority first: this decides the single note shown to the user.
NOTE_PRIORITY = [
    "unknown_repo", "path_outside_repo", "file_missing", "range_invalid", "evidence_too_short", "not_found",
    "found_elsewhere", "range_off_by", "prefix_stripped", "truncated", "range_loose", "ok",
]

NOTE_TEXT = {
    "ok": "Citation verified",
    "prefix_stripped": "Verified (a line-number prefix was ignored)",
    "truncated": "Verified (quoted text was shortened)",
    "range_loose": "Verified (cited range is slightly wider than the evidence)",
    "unknown_repo": "Could not verify: unknown repository",
    "path_outside_repo": "Could not verify: the path leaves the repository",
    "file_missing": "Could not verify: that file does not exist",
    "range_invalid": "Could not verify: the line range is not valid for that file",
    "evidence_too_short": "Could not verify: the quoted evidence is too short to check",
    "not_found": "Could not verify: that text is not in the cited file",
    "found_elsewhere": "Could not verify: the text is in this file, but not at the cited lines",
    "no_citation": "Could not verify: the rule has no citation",
}


@dataclass
class CheckResult:
    verified: bool
    notes: list[str] = field(default_factory=list)
    found_lines: list[int] | None = None
    source_lines: list[dict] = field(default_factory=list)  # [{n, text}] real lines from the pinned file, for display

    @property
    def top_note(self) -> str:
        return min(self.notes, key=_rank) if self.notes else "ok"

    def text(self) -> str:
        """What the PM sees. Any verified citation reads simply "Citation verified"; the detail (prefix ignored, range
        slightly loose, ...) stays in `notes` and is shown only in debug mode."""
        if self.verified:
            return NOTE_TEXT["ok"]
        note = self.top_note
        if note == "found_elsewhere" and self.found_lines:
            return f"Could not verify: the text is in this file at lines {self.found_lines[0]}-{self.found_lines[1]}, not at the cited lines"
        return NOTE_TEXT.get(note, note)


def _rank(note: str) -> int:
    for i, prefix in enumerate(NOTE_PRIORITY):
        if note.startswith(prefix):
            return i
    return len(NOTE_PRIORITY)


def _source(lines: list[str], first: int, last: int) -> list[dict]:
    """The real lines first..last of the file (capped), long lines shortened, for display."""
    last = min(last, first + SOURCE_MAX_LINES - 1)
    out = []
    for number in range(first, last + 1):
        text = lines[number - 1].rstrip()
        if len(text) > SOURCE_MAX_CHARS:
            text = text[:SOURCE_MAX_CHARS].rstrip() + " \u2026"
        out.append({"n": number, "text": text})
    return out


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def load_repos(root: Path = ROOT) -> dict[str, dict]:
    """repos.json -> {name: {"path": absolute Path, "sha": ..., ...}} (single source of truth, shared with ingest)."""
    data = json.loads((root / "repos.json").read_text(encoding="utf-8"))
    return {r["name"]: {**r, "path": root / r["path"]} for r in data["repos"]}


@lru_cache(maxsize=64)
def _normalised_file(path: str, mtime_ns: int) -> tuple[list[str], str, list[tuple[int, int, int]]]:
    """(raw lines, one normalised string, spans) where spans = (start_offset, end_offset, line_number) per non-empty line."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    text, spans = "", []
    for number, line in enumerate(lines, 1):
        norm = _squash(line)
        if not norm:
            continue
        if text:
            text += " "
        spans.append((len(text), len(text) + len(norm), number))
        text += norm
    return lines, text, spans


def _line_at(spans: list[tuple[int, int, int]], offset: int) -> int:
    for start, end, number in spans:
        if start <= offset < end:
            return number
    return spans[-1][2]


def check_citation(citation: dict, repos: dict[str, dict] | None = None) -> CheckResult:
    repos = repos if repos is not None else load_repos()
    repo = repos.get(citation.get("repo", ""))
    if not repo:
        return CheckResult(False, ["unknown_repo"])

    root = Path(repo["path"]).resolve()
    target = (root / str(citation.get("file", ""))).resolve()
    if root != target and root not in target.parents:
        return CheckResult(False, ["path_outside_repo"])
    if not target.is_file():
        return CheckResult(False, ["file_missing"])
    try:
        lines, text, spans = _normalised_file(str(target), target.stat().st_mtime_ns)
    except UnicodeDecodeError:  # binary or non-UTF-8 file: nothing in it can be cited
        return CheckResult(False, ["file_missing"])

    try:
        start, end = int(citation["line_start"]), int(citation["line_end"])
    except (KeyError, TypeError, ValueError):
        return CheckResult(False, ["range_invalid"])
    if not (1 <= start <= end <= len(lines)):
        return CheckResult(False, ["range_invalid"])

    cited_view = _source(lines, start, end)
    notes: list[str] = []
    raw_lines = str(citation.get("evidence", "")).split("\n")
    stripped = [PREFIX.sub("", line) for line in raw_lines]
    if stripped != raw_lines:
        notes.append("prefix_stripped")
    evidence = _squash(" ".join(stripped))
    if evidence.endswith("...") or evidence.endswith("…"):
        evidence = evidence.rstrip(".…").rstrip()
        notes.append("truncated")
    if len(evidence) < MIN_EVIDENCE_CHARS:
        return CheckResult(False, ["evidence_too_short"], source_lines=cited_view)

    # every occurrence of the evidence in the file, as (first_line, last_line)
    occurrences, pos = [], text.find(evidence)
    while pos != -1:
        occurrences.append((_line_at(spans, pos), _line_at(spans, pos + len(evidence) - 1)))
        pos = text.find(evidence, pos + 1)
    if not occurrences:
        return CheckResult(False, ["not_found"], source_lines=cited_view)

    def distance(occ: tuple[int, int]) -> int:  # 0 = inside the cited range
        if occ[0] >= start and occ[1] <= end:
            return 0
        return occ[0] - end if occ[0] > end else start - occ[1]

    best = min(occurrences, key=distance)
    gap = distance(best)
    found = [best[0], best[1]]
    shown = _source(lines, best[0], best[1])  # always the lines that really contain the evidence
    if gap == 0:
        if (end - start + 1) - (best[1] - best[0] + 1) >= 1:
            notes.append("range_loose")
        return CheckResult(True, notes or ["ok"], found, shown)
    if gap <= OFF_BY_LIMIT:
        return CheckResult(True, [f"range_off_by_{gap}", *notes], found, shown)
    return CheckResult(False, ["found_elsewhere", *notes], found, shown)


def check_rule(rule: dict, repos: dict[str, dict] | None = None) -> dict:
    """Adds verified, verify_notes, verify_text and found_lines to every citation, and all_verified to the rule.
    A rule without citations is shown but never counts as verified."""
    repos = repos if repos is not None else load_repos()
    checked = []
    for citation in rule.get("citations") or []:
        result = check_citation(citation, repos)
        checked.append({
            **citation,
            "verified": result.verified,
            "verify_notes": result.notes,
            "verify_text": result.text(),
            "found_lines": result.found_lines,
            "source_lines": result.source_lines,
        })
    all_verified = bool(checked) and all(c["verified"] for c in checked)
    out = {**rule, "citations": checked, "all_verified": all_verified}
    if not checked:
        out["verify_text"] = NOTE_TEXT["no_citation"]
    return out
