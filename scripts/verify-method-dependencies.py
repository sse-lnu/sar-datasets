#!/usr/bin/env python3
"""Validate the packaged method dependency matrices and their manifest."""

from __future__ import annotations

import hashlib
import json
import lzma
from pathlib import Path


EXPECTED = {
    "ant", "archstudio4", "argouml", "bash-4.2", "commons-imaging",
    "hadoop", "hdc", "hdf", "jabref", "libxml", "lucene", "oodt",
    "sweethome3d", "teammates",
}


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    matrix_root = root / "metadata" / "method-dependency-matrices"
    manifest = json.loads(
        (matrix_root / "generation-manifest.json").read_text(encoding="utf-8")
    )
    records = {record["system"]: record for record in manifest["systems"]}
    if set(records) != EXPECTED:
        raise SystemExit(
            f"manifest systems differ: expected={sorted(EXPECTED)} "
            f"actual={sorted(records)}"
        )

    for system in sorted(EXPECTED):
        record = records[system]
        recorded_path = Path(record["output_file"])
        path = (
            matrix_root / recorded_path
            if len(recorded_path.parts) == 1
            else root / recorded_path
        )
        if digest(path) != record["output_sha256"]:
            raise SystemExit(f"checksum mismatch: {path}")
        with lzma.open(path, "rt", encoding="utf-8") as stream:
            matrix = json.load(stream)
        variables = matrix["variables"]
        cells = matrix["cells"]
        if len(variables) != record["method_nodes"]:
            raise SystemExit(f"node-count mismatch: {system}")
        if len(cells) != record["method_cells"]:
            raise SystemExit(f"cell-count mismatch: {system}")
        if not cells:
            raise SystemExit(f"empty method dependency matrix: {system}")
        if matrix["name"] != record["matrix_name"]:
            raise SystemExit(f"matrix-name mismatch: {system}")
        if any(variable.startswith("/") for variable in variables):
            raise SystemExit(f"absolute method node path: {system}")
        size = len(variables)
        if any(
            not (0 <= cell["src"] < size and 0 <= cell["dest"] < size)
            or not cell["values"]
            for cell in cells
        ):
            raise SystemExit(f"invalid dependency cell: {system}")
        projection = record.get("projection_summary")
        if projection and projection["unmatched_endpoints"] != 0:
            raise SystemExit(f"unmatched projected endpoint: {system}")
        print(f"ok {system}: nodes={len(variables)} cells={len(cells)}")

    if (matrix_root / "chromium_method_deps.json.xz").exists():
        raise SystemExit("Chromium is present but not registered in this generation")
    print("ok chromium: intentionally pending")


if __name__ == "__main__":
    main()
