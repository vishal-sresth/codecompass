"""CodeCompass ingest: turn repo files into small, line-numbered chunk files.

Why: File Search returns chunk text, not line numbers. So every chunk carries its own
REPO / PATH / LINES header and numbered lines, which lets the agent cite file:line and
lets our checker verify the citation against the real file.

Run:  python3 ingest/ingest.py
Out:  ingest/out/chunks/*.txt  (one file per chunk)  +  ingest/out/manifest.json
"""
import fnmatch
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # codecompass/
OUT = Path(__file__).resolve().parent / "out"

# --- To add a repo, add one entry here. -----------------------------------------
REPOS = [
    {
        "name": "hyperswitch",
        "path": ROOT / "hyperswitch",
        "sha": "d03f8547d6367fab56690e4f5043590be4935dcd",
        "include": [
            "config/development.toml",
            "config/config.example.toml",
            "config/deployments/production.toml",
            "config/payment_required_fields_v2.toml",
        ],
    },
    {
        "name": "active_merchant",
        "path": ROOT / "repos" / "active_merchant",
        "sha": "ca45b1b063ce2e1495e1427e0a1d42dcb482d57d",
        "include": ["lib/active_merchant/billing/gateways/*.rb"],
    },
]

# Never index files that look like secrets (PRD Section 7).
SECRET_PATTERNS = ["*.env", ".env*", "*.pem", "*.key", "*secret*", "*credential*"]

MAX_LINES = 60    # lines per chunk
MAX_CHARS = 2400  # about 600 tokens, so the service does not re-split a chunk
OVERLAP = 10      # lines repeated at the start of the next chunk (see LEARNINGS.md #4)

# A "section" is the nearest structural line above a chunk, e.g. [pm_filters.stripe] in TOML
# or `class StripeGateway` in Ruby. Without it, a chunk can lose which connector a rule belongs to.
SECTION_RE = {
    ".toml": re.compile(r"^\s*\[[^\]]+\]\s*$"),
    ".rb": re.compile(r"^\s*(class|module)\s+\S+"),
}


def find_section(lines, first_line, ext):
    """Nearest section header at or above first_line (1-based), or None."""
    rx = SECTION_RE.get(ext)
    if not rx:
        return None
    for i in range(first_line, 0, -1):
        if rx.match(lines[i - 1]):
            return lines[i - 1].strip()
    return None


def is_secret(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1].lower()
    return any(fnmatch.fnmatch(name, p) for p in SECRET_PATTERNS)


def chunk_lines(lines):
    """Yield (start_line, end_line, [lines]) with 1-based line numbers.

    Each chunk after the first re-includes the last OVERLAP lines of the previous one.
    """
    n, start = len(lines), 1
    while start <= n:
        end, size = start, len(lines[start - 1]) + 8
        while end < n and (end - start + 1) < MAX_LINES and size + len(lines[end]) + 8 <= MAX_CHARS:
            end += 1
            size += len(lines[end - 1]) + 8
        yield start, end, lines[start - 1:end]
        if end >= n:
            break
        # keep up to OVERLAP lines of context, but never more than a third of the chunk
        # (long-line files like Hyperswitch config have only ~4 lines per chunk)
        keep = min(OVERLAP, (end - start + 1) // 3)
        start = end - keep + 1


def main():
    chunks_dir = OUT / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    for old in chunks_dir.glob("*.txt"):
        old.unlink()

    manifest = {"repos": [], "indexed": [], "skipped": []}
    for repo in REPOS:
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

            n = 0
            for a, b, buf in chunk_lines(lines):
                width = len(str(b))
                body = "\n".join(f"{a + k:>{width}} | {t}" for k, t in enumerate(buf))
                section = find_section(lines, a, f.suffix)
                sec = f"SECTION: {section}\n" if section else ""
                header = f"REPO: {repo['name']}\nCOMMIT: {repo['sha'][:10]}\nPATH: {rel}\n{sec}LINES: {a}-{b}\n----\n"
                safe = re.sub(r"[^A-Za-z0-9]+", "_", f"{repo['name']}_{rel}")
                (chunks_dir / f"{safe}__{a}-{b}.txt").write_text(header + body + "\n", encoding="utf-8")
                n += 1
            manifest["indexed"].append({"repo": repo["name"], "path": rel, "lines": len(lines), "chunks": n})

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    total = sum(x["chunks"] for x in manifest["indexed"])
    print(f"files indexed: {len(manifest['indexed'])}, skipped: {len(manifest['skipped'])}, chunks written: {total}")
    for r in manifest["repos"]:
        files = [x for x in manifest["indexed"] if x["repo"] == r["name"]]
        print(f"  {r['name']}: {len(files)} files, {sum(x['chunks'] for x in files)} chunks")


if __name__ == "__main__":
    main()
