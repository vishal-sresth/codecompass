#!/usr/bin/env bash
# Re-creates the two third-party source repos at the exact commits we indexed.
# They are not stored in this repo (their licenses are their own: Apache-2.0 and MIT).
set -euo pipefail
cd "$(dirname "$0")/.."

clone_at() {  # url dir sha
  if [ -d "$2/.git" ]; then echo "$2 exists, skipping"; return; fi
  mkdir -p "$2" && git -C "$2" init -q && git -C "$2" remote add origin "$1"
  git -C "$2" fetch -q --depth 1 origin "$3" && git -C "$2" checkout -q FETCH_HEAD
  echo "$2 at $(git -C "$2" rev-parse --short HEAD)"
}

clone_at https://github.com/juspay/hyperswitch.git hyperswitch d03f8547d6367fab56690e4f5043590be4935dcd
clone_at https://github.com/activemerchant/active_merchant.git repos/active_merchant ca45b1b063ce2e1495e1427e0a1d42dcb482d57d
