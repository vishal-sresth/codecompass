"""Verify a generated chunk set before it is uploaded. Local only (no Azure calls).

Checks the properties everything downstream depends on:
  1. every chunk starts with a complete header (REPO / COMMIT / PATH / LINES / ----)
  2. every numbered row matches the real source line (split parts are re-joined before comparing)
  3. every line of every indexed source file appears in at least one chunk (no gaps)
  4. no chunk is over 800 tokens by either tokenizer (the service re-splits above that); reports the maximum
  5. a known case: Stripe's own methods after the nested token class are labelled StripeGateway, not StripePaymentToken
Run: python ingest/verify_chunks.py [--out ingest/out_v2]
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import REPOS, ROOT, count_tokens  # noqa: E402

ROW = re.compile(r"^\s*(\d+)(?: \[part (\d+)/(\d+)\])? \| ?(.*)$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="ingest/out_v2")
    out = ROOT / ap.parse_args().out / "chunks"
    files = sorted(out.glob("*.txt"))
    roots = {r["name"]: r["path"] for r in REPOS}
    problems, max_tokens, over600, rows_checked = [], 0, 0, 0
    parts = {}      # (repo, path, line) -> {part_k: text}
    seen = {}       # (repo, path) -> set of line numbers covered
    stripe_labels = []
    print(f"chunk files read: {len(files)}")
    assert files, "no chunks found: stop (a check that read nothing proves nothing)"

    for f in files:
        text = f.read_text(encoding="utf-8")
        head, _, body = text.partition("----\n")
        meta = dict(l.split(": ", 1) for l in head.strip().split("\n") if ": " in l)
        if not all(k in meta for k in ("REPO", "COMMIT", "PATH", "LINES")):
            problems.append(f"{f.name}: incomplete header")
            continue
        t = count_tokens(text)
        max_tokens = max(max_tokens, t)
        over600 += t > 600
        if t > 800:
            problems.append(f"{f.name}: {t} tokens (over 800)")
        key = (meta["REPO"], meta["PATH"])
        seen.setdefault(key, set())
        for row in body.split("\n"):
            if not row or row.startswith(">> line "):
                continue
            m = ROW.match(row)
            if not m:
                problems.append(f"{f.name}: unparseable row {row[:50]!r}")
                continue
            no, k, n, txt = int(m.group(1)), int(m.group(2) or 1), int(m.group(3) or 1), m.group(4)
            parts.setdefault((meta["REPO"], meta["PATH"], no), {})[k] = (n, txt)
            seen[key].add(no)
            rows_checked += 1
        if meta["PATH"].endswith("gateways/stripe.rb"):
            a = int(meta["LINES"].split("-")[0])
            if a >= 300:
                stripe_labels.append(meta.get("SECTION", "none"))

    # 2 + 3: compare with source, check coverage
    src_cache = {}
    for (repo, path, no), segs in parts.items():
        lines = src_cache.setdefault((repo, path), (roots[repo] / path).read_text(encoding="utf-8").splitlines())
        n = max(v[0] for v in segs.values())
        joined = "".join(segs[k][1] for k in sorted(segs))
        if len(segs) != n or joined.rstrip() != lines[no - 1].rstrip():
            problems.append(f"{repo}:{path}:{no}: row text differs from source (parts {sorted(segs)} of {n})")
    for (repo, path), covered in seen.items():
        total = len((roots[repo] / path).read_text(encoding="utf-8").splitlines())
        missing = sorted(set(range(1, total + 1)) - covered)
        # a line that is entirely empty is still emitted as a row, so every line must be present
        if missing:
            problems.append(f"{repo}:{path}: {len(missing)} lines never appear (first: {missing[:5]})")

    print(f"rows checked against source: {rows_checked}")
    print(f"max tokens in any chunk: {max_tokens} (both tokenizers, larger count); chunks over 600: {over600}")
    if stripe_labels:  # only meaningful when the active_merchant chunks are in this set
        wrong = [s for s in stripe_labels if "StripePaymentToken" in s]
        print(f"stripe.rb chunks after line 300 labelled StripePaymentToken: {len(wrong)} of {len(stripe_labels)} (must be 0)")
        if wrong:
            problems.append("stripe.rb nested-class label still wrong")
    else:
        print("stripe.rb nested-class check: n/a (no active_merchant chunks in this set)")
    print("PROBLEMS:", len(problems))
    for p in problems[:15]:
        print("  ", p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
