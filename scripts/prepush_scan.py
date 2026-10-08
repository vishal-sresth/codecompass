"""Pre-push scan: look for sensitive strings in every file git would commit. Local only.

  python scripts/prepush_scan.py            # scans tracked + untracked (non-ignored) files

Every pattern is proven against a planted sample before the real scan (a scan that cannot find anything proves nothing),
and the number of files read is printed. Exit code 1 if anything is found or a control fails.
Employer names are not hard-coded here (that would put them in the repo); pass them at run time:
  python scripts/prepush_scan.py --also "word1,word2"   (employer names, your own resource names or id prefixes)
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PATTERNS = {
    "guid (subscription / tenant / resource id)": r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    "email address": r"[\w.+-]+@[\w-]+\.[a-z]{2,}",
    "azure resource name": r"[a-z0-9-]+-resource\b|\brg-[a-z0-9.-]+",
    "vector store id": r"vs_[A-Za-z0-9]{20,}",
    "foundry endpoint": r"[a-z0-9-]+\.services\.ai\.azure\.com",
    "local absolute path": r"/Users/\w+|/home/\w+|C:\\Users",
    "key / token shape": r"sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9/+_-]{16,}",
}
# Planted samples are obviously fake and assembled at run time, so this file never contains a string that matches its own
# patterns (and never contains a real identifier). Personal strings (your own resource names, ids, employer) are passed with --also.
PLANTED = {
    "guid (subscription / tenant / resource id)": "0" * 8 + "-" + "0" * 4 + "-4" + "0" * 3 + "-8" + "0" * 3 + "-" + "0" * 12,
    "email address": "someone" + "@" + "example.com",
    "azure resource name": "demo-0000" + "-resource",
    "vector store id": "vs_" + "A" * 24,
    "foundry endpoint": "demo" + ".services.ai." + "azure.com",
    "local absolute path": "/Use" + "rs/demo",
    "key / token shape": "API_" + "KEY = " + "abcdefgh12345678",
}
# Known-public strings that are allowed to match (placeholders in templates, public examples).
ALLOW = {"<your-account>.services.ai.azure.com", "someone@example.com", "noreply@anthropic.com"}


def tracked_and_new() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / p for p in out.split("\0") if p and (ROOT / p).is_file() and not (ROOT / p).is_symlink()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--also", default="", help="extra comma-separated words to look for (for example employer names)")
    extra = [w.strip() for w in ap.parse_args().also.split(",") if w.strip()]
    patterns = dict(PATTERNS)
    planted = dict(PLANTED)
    for w in extra:
        patterns[f"extra word: {w[:2]}..."] = r"\b" + re.escape(w) + r"\b"
        planted[f"extra word: {w[:2]}..."] = w.upper()
    bad_controls = [k for k, v in planted.items() if not re.search(patterns[k], v, re.I)]
    if bad_controls:
        print("CONTROL FAILED for:", bad_controls)
        return 1
    files = tracked_and_new()
    print(f"files read: {len(files)} | pattern controls: all {len(patterns)} found their planted sample")
    hits, unreadable = [], 0
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            unreadable += 1
            continue
        for name, rx in patterns.items():
            for m in re.finditer(rx, text, re.I):
                if m.group(0).lower() in ALLOW:
                    continue
                hits.append((str(f.relative_to(ROOT)), name, text[max(0, m.start() - 25):m.end() + 25].replace("\n", " ")))
    print(f"binary/unreadable files skipped: {unreadable}")
    print("HITS:", len(hits))
    for h in hits[:40]:
        print("  ", h)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
