"""Create a vector store and upload chunk files to it.

  python scripts/upload_chunks.py --name codecompass-test --test     # 20 hand-picked chunks
  python scripts/upload_chunks.py --name codecompass-full            # all chunks
"""
import argparse
import time
from pathlib import Path

from common import ROOT, project_client

CHUNKS = ROOT / "ingest" / "out" / "chunks"


def pick_test_files():
    """10 Hyperswitch pm_filters chunks + 10 active_merchant stripe.rb chunks (answerable test)."""
    hs = []
    for f in sorted(CHUNKS.glob("hyperswitch_config_development_toml__*.txt")):
        text = f.read_text()
        if "[pm_filters" in text or "SECTION: [pm_filters" in text:
            hs.append(f)
    stripe = sorted(CHUNKS.glob("active_merchant_lib_active_merchant_billing_gateways_stripe_rb__*.txt"))
    return hs[:10] + stripe[:10]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--batch", type=int, default=100)
    args = ap.parse_args()

    files = pick_test_files() if args.test else sorted(CHUNKS.glob("*.txt"))
    print(f"uploading {len(files)} files to a new vector store '{args.name}'")

    oc = project_client().get_openai_client()
    vs = oc.vector_stores.create(name=args.name)
    print("vector store id:", vs.id)

    t0 = time.time()
    for i in range(0, len(files), args.batch):
        part = files[i:i + args.batch]
        handles = [open(p, "rb") for p in part]
        try:
            b = oc.vector_stores.file_batches.upload_and_poll(vector_store_id=vs.id, files=handles)
        finally:
            for h in handles:
                h.close()
        print(f"  batch {i // args.batch + 1}: {b.status} {b.file_counts.completed}/{len(part)} ok, {b.file_counts.failed} failed")

    vs = oc.vector_stores.retrieve(vs.id)
    print(f"done in {time.time() - t0:.0f}s: {vs.file_counts.completed} completed, {vs.file_counts.failed} failed; usage_bytes={vs.usage_bytes}")


if __name__ == "__main__":
    main()
