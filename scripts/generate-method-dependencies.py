#!/usr/bin/env python3
"""Generate method dependency matrices with the shipped Depends 0.9.7 JAR."""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import shutil
import subprocess
import time
from pathlib import Path


JAR_SHA256 = "004b232f258b15a85195accb37905a339a01de7b99ea5029be3fc0ea8d3664e7"

# language, path relative to the full-snapshot root, Depends output basename
SYSTEMS = {
    "ant": ("java", "ant/apache-ant-r584500", "ant-r584500-source-depends"),
    "archstudio4": ("java", "archstudio4", "archstudio4-depends"),
    "argouml": ("java", "argouml/argouml-r13713", "argouml-r13713-source-generated-depends"),
    "bash-4.2": ("cpp", "bash-4.2", "bash-4.2-generated-depends"),
    "chromium": ("cpp", "chromium/src", "chromium-browser-23.0.1271.97-src-depends-full"),
    "commons-imaging": ("java", "commons-imaging", "commons-imaging-a2d77b8-depends"),
    "hadoop": ("java", "hadoop", "hadoop-0.19.0-built-depends"),
    "hdc": ("cpp", "hdc", "hdc-distributed_camera-depends"),
    "hdf": ("cpp", "hdf", "hdf-core-depends"),
    "jabref": ("java", "jabref", "jabref-v3.7-generated-depends"),
    "libxml": ("cpp", "libxml", "libxml2-2.4.22-depends"),
    "lucene": ("java", "lucene/lucene-r1075001", "lucene-r1075001-source-depends"),
    "oodt": ("java", "oodt", "oodt-0.2-tag-depends"),
    "sweethome3d": ("java", "sweethome3d/sweethome3d-r002382", "sweethome3d-r002382-source-depends"),
    "teammates": ("java", "teammates", "teammates-5.110-depends"),
}
DEFAULT_SYSTEMS = tuple(system for system in SYSTEMS if system != "chromium")


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def source_file_count(path: Path, language: str) -> int:
    suffixes = {".java"} if language == "java" else {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp"
    }
    return sum(
        1 for item in path.rglob("*")
        if item.is_file() and item.suffix.lower() in suffixes
    )


def run_one(
    *,
    system: str,
    language: str,
    source: Path,
    base: str,
    jar: Path,
    work: Path,
    output: Path,
    projector: Path,
    memory: str,
) -> dict[str, object]:
    system_work = work / system
    system_work.mkdir(parents=True, exist_ok=False)
    command = ["java", f"-Xmx{memory}", "-jar", str(jar), "-s"]
    mode = "native_method"
    if language == "cpp":
        command.extend(["--auto-include", "--detail", "-f=json", "-g=method,structure"])
        mode = "structure_projection"
    else:
        command.extend(["-f=json", "-g=method"])
    command.extend([f"-d={system_work}", language, str(source), base])

    print(f"START {system}", flush=True)
    started = time.time()
    log = system_work / "depends.log"
    with log.open("wb") as stream:
        completed = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    elapsed = time.time() - started
    if completed.returncode:
        raise SystemExit(f"Depends failed for {system}; see {log}")

    native_method = system_work / f"{base}-method.json"
    final_json = system_work / f"{system}_method_deps.json"
    projection_summary = None
    if language == "cpp":
        structure = system_work / f"{base}-structure.json"
        projection = subprocess.run(
            [
                "python3", str(projector),
                "--method", str(native_method),
                "--structure", str(structure),
                "--output", str(final_json),
                "--name", f"{base}-method-sdsm",
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        projection_summary = json.loads(projection.stdout)
    else:
        shutil.copyfile(native_method, final_json)

    matrix = json.loads(final_json.read_text(encoding="utf-8"))
    final_xz = output / f"{system}_method_deps.json.xz"
    if final_xz.exists():
        raise SystemExit(f"refusing to overwrite {final_xz}")
    with final_json.open("rb") as source_stream, lzma.open(
        final_xz, "wb", preset=9 | lzma.PRESET_EXTREME
    ) as target_stream:
        shutil.copyfileobj(source_stream, target_stream)

    record = {
        "system": system,
        "language": language,
        "mode": mode,
        "source_root": str(source),
        "source_file_count": source_file_count(source, language),
        "command": command,
        "elapsed_seconds": round(elapsed, 3),
        "method_nodes": len(matrix["variables"]),
        "method_cells": len(matrix["cells"]),
        "relation_weight": sum(
            sum(float(value) for value in cell["values"].values())
            for cell in matrix["cells"]
        ),
        "matrix_name": matrix["name"],
        "output_file": final_xz.name,
        "output_sha256": digest(final_xz),
        "uncompressed_json_sha256": digest(final_json),
        "projection_summary": projection_summary,
        "depends_log": str(log),
    }
    print(
        f"DONE {system} nodes={record['method_nodes']} "
        f"cells={record['method_cells']} seconds={record['elapsed_seconds']}",
        flush=True,
    )
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jar", required=True, type=Path)
    parser.add_argument("--datasets", required=True, type=Path)
    parser.add_argument("--commons-root", type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--memory", default="32g")
    parser.add_argument("--systems", nargs="+", choices=tuple(SYSTEMS), default=DEFAULT_SYSTEMS)
    args = parser.parse_args()

    if digest(args.jar) != JAR_SHA256:
        raise SystemExit("Depends JAR hash does not match the frozen 0.9.7 artifact")
    args.work.mkdir(parents=True, exist_ok=False)
    args.output.mkdir(parents=True, exist_ok=True)
    projector = Path(__file__).with_name("project-cpp-method-dependencies.py")

    records = []
    for system in args.systems:
        language, relative, base = SYSTEMS[system]
        if system == "commons-imaging" and args.commons_root is not None:
            source = args.commons_root
        else:
            source = args.datasets / relative
        if not source.is_dir():
            raise SystemExit(f"missing source root for {system}: {source}")
        records.append(
            run_one(
                system=system,
                language=language,
                source=source,
                base=base,
                jar=args.jar,
                work=args.work,
                output=args.output,
                projector=projector,
                memory=args.memory,
            )
        )

    manifest = {
        "schema_version": "1.0.0",
        "depends_version": "0.9.7",
        "depends_jar_sha256": JAR_SHA256,
        "java_version": subprocess.run(
            ["java", "-version"], text=True, capture_output=True, check=True
        ).stderr.splitlines()[0],
        "systems": records,
    }
    manifest_path = args.output / "generation-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"COMPLETE manifest={manifest_path}", flush=True)


if __name__ == "__main__":
    main()
