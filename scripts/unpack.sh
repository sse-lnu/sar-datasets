#!/usr/bin/env bash
set -euo pipefail

dest="${1:-data}"
mkdir -p "$dest"

for archive in archives/gt-deps-source/*.tar.xz; do
  echo "unpacking $archive"
  tar -C "$dest" -xf "$archive"
done
