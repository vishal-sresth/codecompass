"""CodeCompass ingest: turn repo files into small, line-numbered chunk files for the Foundry vector store.

Why chunks carry their own header and line numbers: File Search returns chunk text, not line numbers, so every chunk
holds REPO / COMMIT / PATH / SECTION / LINES and numbered lines. That lets the agent cite file:line and lets our checker verify it.

Why chunks are sized in TOKENS: the service re-splits anything above about 800 tokens and the second piece loses the header
(LEARNINGS.md 21). Country lists are token-dense, so a character limit is not safe. We budget 600 tokens per chunk file and
measure with two tokenizers, taking the larger count.

Run:   python ingest/ingest.py [--out ingest/out_v2] [--repo hyperswitch]      (needs: pip install tiktoken)
Out:   <out>/chunks/*.txt (one file per chunk) and <out>/manifest.json
Check: python ingest/verify_chunks.py [--out ingest/out_v2]
"""
import argparse
import fnmatch
import json
import re
from pathlib import Path

import tiktoken

ROOT = Path(__file__).resolve().parent.parent  # project root

# --- Repos come from repos.json (single source of truth, shared with the checker and the server). ---
REPOS = [{**r, "path": ROOT / r["path"]} for r in json.loads((ROOT / "repos.json").read_text())["repos"]]

# Never index files that look like secrets (PRD Section 7).
SECRET_PATTERNS = ["*.env", ".env*", "*.pem", "*.key", "*secret*", "*credential*"]

MAX_CHUNK_TOKENS = 600   # whole chunk file including header (service window is about 800)
LINE_MAX_TOKENS = 400    # a single source line longer than this is split into parts
OVERLAP = 10             # rows repeated at the start of the next chunk, capped at a third of the chunk

_ENCODINGS = [tiktoken.get_encoding(n) for n in ("cl100k_base", "o200k_base")]


def count_tokens(text):
    """Conservative: the larger of two common tokenizers."""
    return max(len(e.encode(text, disallowed_special=())) for e in _ENCODINGS)


TOML_SECTION = re.compile(r"^\s*\[[^\]]+\]\s*$")
RUBY_DECL = re.compile(r"^(\s*)(class|module)\s+\S+")
RUBY_END = re.compile(r"^(\s*)end\b")


def section_by_line(lines, ext):
    """section[i] = the structural label that applies at source line i (1-based), or None.
    TOML: nearest [section] header at or above. Ruby: innermost enclosing class (else module), tracking nesting by
    pushing on `class`/`module` and popping on the matching `end` at the same indent."""
    out = [None] * (len(lines) + 1)
    if ext == ".toml":
        cur = None
        for i, l in enumerate(lines, 1):
            if TOML_SECTION.match(l):
                cur = l.strip()
            out[i] = cur
    elif ext == ".rb":
        stack = []  # (indent, kind, text)
        for i, l in enumerate(lines, 1):
            m = RUBY_DECL.match(l)
            if m:
                stack.append((len(m.group(1)), m.group(2), l.strip()))
            classes = [s for s in stack if s[1] == "class"]
            out[i] = (classes[-1] if classes else stack[-1])[2] if stack else None
            e = RUBY_END.match(l)
            if e and stack and len(e.group(1)) == stack[-1][0] and not m:
                stack.pop()
    return out


def split_long_line(text):
    """Split a line over LINE_MAX_TOKENS into parts, preferring comma boundaries (keeps country codes whole)."""
    if count_tokens(text) <= LINE_MAX_TOKENS:
        return [text]
    parts, cur = [], ""
    for piece in re.split(r"(?<=,)", text):
        if cur and count_tokens(cur + piece) > LINE_MAX_TOKENS:
            parts.append(cur)
            cur = piece
        else:
            cur += piece
    parts.append(cur)
    final = []  # a piece with no commas can still be too long: halve it until it fits
    for p in parts:
        stack = [p]
        while stack:
            q = stack.pop(0)
            if count_tokens(q) > LINE_MAX_TOKENS and len(q) > 1:
                stack = [q[: len(q) // 2], q[len(q) // 2:]] + stack
            else:
                final.append(q)
    return final


def build_rows(lines):
    """Rows of (line_no, text_to_show, tokens, is_part). Long lines become several rows with a continuation hint."""
    width = len(str(len(lines)))
    rows = []
    for no, text in enumerate(lines, 1):
        parts = split_long_line(text)
        n = len(parts)
        for k, part in enumerate(parts, 1):
            label = f"{no:>{width}}" + (f" [part {k}/{n}]" if n > 1 else "")
            shown = f"{label} | {part}"
            if k > 1:
                shown = f">> line {no} continues; it begins: {parts[0][:60].strip()}\n" + shown
            rows.append((no, shown, count_tokens(shown), n > 1))
    return rows


def build_header(repo, sha, rel, section, a, b):
    sec = f"SECTION: {section}\n" if section else ""
    return f"REPO: {repo}\nCOMMIT: {sha[:10]}\nPATH: {rel}\n{sec}LINES: {a}-{b}\n----\n"


def chunk_rows(rows, repo, sha, rel, sections, n_lines):
    """Yield (row_start, row_end) so that header + rows fit MAX_CHUNK_TOKENS; overlap capped at a third of the chunk."""
    n, s = len(rows), 0
    while s < n:
        a = rows[s][0]
        used = count_tokens(build_header(repo, sha, rel, sections[a], a, n_lines)) + rows[s][2]
        e = s
        while e + 1 < n and used + rows[e + 1][2] <= MAX_CHUNK_TOKENS:
            e += 1
            used += rows[e][2]
        yield s, e
        if e >= n - 1:
            break
        keep = min(OVERLAP, (e - s + 1) // 3)
        s = max(e - keep + 1, s + 1)


def is_secret(rel):
    name = rel.rsplit("/", 1)[-1].lower()
    return any(fnmatch.fnmatch(name, p) for p in SECRET_PATTERNS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="ingest/out_v2", help="output folder, relative to the project root")
    ap.add_argument("--repo", default=None, help="index only this repo (a name from repos.json), e.g. hyperswitch")
    args = ap.parse_args()
    out = ROOT / args.out
    repos = [r for r in REPOS if args.repo in (None, r["name"])]
    if not repos:
        raise SystemExit(f"unknown repo {args.repo!r}; choose from {[r['name'] for r in REPOS]}")
    chunks_dir = out / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    for old in chunks_dir.glob("*.txt"):
        old.unlink()

    manifest = {"repos": [], "indexed": [], "skipped": [], "settings": {
        "max_chunk_tokens": MAX_CHUNK_TOKENS, "line_max_tokens": LINE_MAX_TOKENS, "overlap": OVERLAP}}
    for repo in repos:
        root = repo["path"]
        manifest["repos"].append({"name": repo["name"], "sha": repo["sha"]})
        matched = set()
        for pattern in repo["include"]:
            matched.update(p for p in root.glob(pattern) if p.is_file())
        for f in sorted(matched):
            rel = f.relative_to(root).as_posix()
            if is_secret(rel):
                manifest["skipped"].append({"repo": repo["name"], "path": rel, "why": "secret-like name"})
                continue
            try:
                lines = f.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                manifest["skipped"].append({"repo": repo["name"], "path": rel, "why": "not utf-8"})
                continue
            sections = section_by_line(lines, f.suffix)
            rows = build_rows(lines)
            safe = re.sub(r"[^A-Za-z0-9]+", "_", f"{repo['name']}_{rel}")
            n_chunks = 0
            for idx, (s, e) in enumerate(chunk_rows(rows, repo["name"], repo["sha"], rel, sections, len(lines)), 1):
                a, b = rows[s][0], rows[e][0]
                text = build_header(repo["name"], repo["sha"], rel, sections[a], a, b) + "\n".join(r[1] for r in rows[s:e + 1]) + "\n"
                (chunks_dir / f"{safe}__{idx:04d}__{a}-{b}.txt").write_text(text, encoding="utf-8")
                n_chunks += 1
            manifest["indexed"].append({"repo": repo["name"], "path": rel, "lines": len(lines), "rows": len(rows),
                                        "split_parts": sum(1 for r in rows if r[3]), "chunks": n_chunks})

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    total = sum(x["chunks"] for x in manifest["indexed"])
    print(f"files indexed: {len(manifest['indexed'])}, skipped: {len(manifest['skipped'])}, chunks written: {total}  -> {out.relative_to(ROOT)}")
    for r in manifest["repos"]:
        files = [x for x in manifest["indexed"] if x["repo"] == r["name"]]
        print(f"  {r['name']}: {len(files)} files, {sum(x['chunks'] for x in files)} chunks, {sum(x['split_parts'] for x in files)} split-line parts")


if __name__ == "__main__":
    main()
