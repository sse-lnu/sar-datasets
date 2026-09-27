#!/usr/bin/env python3
"""Project Depends 0.9.7 structure relations onto its method node universe.

Depends 0.9.7's FunctionDependencyGenerator omits relations attached directly
to FunctionEntity instances. Its detailed structure matrix contains those
relations. This script retains the native method variables and reconstructs
only function-to-function cells from the detailed structure relations.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


FUNCTION_TYPES = {"function", "functionimpl", "functionproto"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", required=True, type=Path)
    parser.add_argument("--structure", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--name", required=True)
    return parser.parse_args()


def is_function(endpoint: dict[str, object]) -> bool:
    return str(endpoint.get("type", "")).lower() in FUNCTION_TYPES


def method_name(endpoint: dict[str, object]) -> str:
    return f"{endpoint['file']}({endpoint['object']})"


def main() -> None:
    args = parse_args()
    method = json.loads(args.method.read_text(encoding="utf-8"))
    structure = json.loads(args.structure.read_text(encoding="utf-8"))

    variables = method["variables"]
    # Match Depends 0.9.7's OrderedMatrixGenerator: when display names collide
    # (for example overloads), the last index wins.
    node_index = {name: index for index, name in enumerate(variables)}
    cells: dict[tuple[int, int], dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    projected_relations = 0
    missing: set[str] = set()

    for cell in structure["cells"]:
        for detail in cell.get("details", []):
            source = detail["src"]
            destination = detail["dest"]
            if not (is_function(source) and is_function(destination)):
                continue
            source_name = method_name(source)
            destination_name = method_name(destination)
            if source_name not in node_index:
                missing.add(source_name)
                continue
            if destination_name not in node_index:
                missing.add(destination_name)
                continue
            relation = detail["type"]
            cells[(node_index[source_name], node_index[destination_name])][relation] += 1.0
            projected_relations += 1

    if missing:
        examples = "\n".join(sorted(missing)[:20])
        raise SystemExit(
            f"{len(missing)} projected method endpoints are absent from the "
            f"native method node universe:\n{examples}"
        )

    output = {
        "schemaVersion": method.get("schemaVersion", "1.0"),
        "name": args.name,
        "variables": variables,
        "cells": [
            {"src": source, "dest": destination, "values": dict(sorted(values.items()))}
            for (source, destination), values in sorted(cells.items())
        ],
    }
    args.output.write_text(
        json.dumps(output, separators=(",", ":")), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "method_nodes": len(variables),
                "method_cells": len(output["cells"]),
                "projected_relations": projected_relations,
                "unmatched_endpoints": 0,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
