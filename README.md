# SAR Datasets

This repository contains a GitHub-sized packaging of software architecture recovery (SAR) benchmark data.

The package is intentionally a pruned dataset, not a full source-code mirror. Each archive contains the source files referenced by the dependency matrix and any reference-decomposition entries that resolve to files, together with the corresponding reference decomposition and dependency matrix. Full source snapshots may be archived separately later, for example through Zenodo.

## Contents

```text
archives/gt-deps-source/        Per-system source subsets as .tar.xz archives
metadata/reference-decompositions/
                                Reference architecture/module decompositions
metadata/dependency-matrices/   Dependency matrices as compressed JSON
metadata/method-dependency-matrices/
                                Method-level dependency matrices and manifest
metadata/dataset-summary.tsv    Per-system file counts and archive sizes
metadata/method-dependency-summary.tsv
                                Method-node, edge, and generation status summary
docs/provenance.json            Traceability records for source snapshots and labels
checksums/SHA256SUMS            SHA-256 checksums for repository artifacts
scripts/                        Helper scripts
```

## Quick Start

Verify the packaged artifacts:

```sh
./scripts/verify-checksums.sh
```

Unpack all source subsets into `data/`:

```sh
./scripts/unpack.sh data
```

Unpack a dependency matrix for inspection:

```sh
xz -dk metadata/dependency-matrices/chromium_deps.json.xz
```

Unpack a method-level dependency matrix:

```sh
xz -dk metadata/method-dependency-matrices/argouml_method_deps.json.xz
```

Validate every packaged method matrix against its generation manifest:

```sh
python3 scripts/verify-method-dependencies.py
```

## Dataset Scope

The archives under `archives/gt-deps-source/` are GT+deps subsets. They preserve:

- files listed in each dependency matrix's `variables`;
- files from the reference decomposition that resolve to source paths;
- the per-system reference decomposition JSON;
- the per-system dependency matrix JSON.

The Commons Imaging package is pinned to commit
`a2d77b8fa6fba0993fb11f177f5ca8373d3791f9`. Its reference decomposition was
contributed by Apache Commons Imaging maintainer Bruno P. Kinoshita; the exact
source and label provenance is recorded in `docs/provenance.json`.

Three packages carry corrected operational lineage discovered during later audit:

- ArchStudio4 is pinned to initial commit
  `afdcb17df90d44b121cdb300f283ef13e063c904`, excluding a later unrelated
  `Test.java` that had entered dependency extraction.
- ArgoUML uses the original 19-module Brunet/Bittencourt package model applied
  to the packaged r13713 source with explicit most-specific-rule precedence.
- Lucene preserves `lucene_gt.json` as historical material and additionally
  provides `lucene_brunet_r1075001_gt.json`, the operational literal-path
  reference generated from all seven rules in the original Brunet model.

The raw Bash and Chromium JSON references are intentionally not rewritten:
Bash requires a documented single-label precedence rule for seven overlapping
history-library files, while Chromium's complete author-published RSF remains
the reference authority. These boundaries are recorded in `docs/provenance.json`.

They do not aim to preserve complete, buildable upstream projects. Binary-content files, nested Git repositories, and unrelated files outside the selected source set were removed to keep the repository small and suitable for GitHub.

## Method-level dependencies

Method-level matrices are available for 14 systems. Chromium is intentionally
pending because its extraction is substantially more expensive and was deferred
so that experiments over the other systems could begin.

All matrices were generated with the shipped Depends 0.9.7 JAR using its legacy
ANTLR Java parser. The exact JAR SHA-256 is
`004b232f258b15a85195accb37905a339a01de7b99ea5029be3fc0ea8d3664e7`.
Java matrices are the native `method` output. Depends 0.9.7 has a method-output
generator defect for C/C++: it emits method nodes but no edges even though its
detailed `structure` output contains function-to-function relations. The Bash,
HDC, HDF, and libxml matrices therefore retain the native method-node universe
and deterministically project only those function-to-function relations already
emitted by the unmodified parser. Every projected endpoint was matched to a
native method node.

See `metadata/method-dependency-matrices/generation-manifest.json` for per-system
counts, hashes, source snapshot identifiers, and extraction modes. The complete
procedure and reproduction command are in
`docs/method-dependency-generation.md`.

## Traceability

See `docs/provenance.json` for source snapshot identifiers, local roots used during packaging, metadata files, and provenance status. Some upstream URLs and retrieval methods still need verification before a release is cited as archival.

## Known Caveats

- Several reference decompositions use entity names rather than file paths. Those entities remain in the JSON metadata, but only entries that resolve to files are copied into source subset archives.
- The current archives are suitable for file-level embedding and probing experiments over labelled/dependency-referenced files, not for rebuilding the original systems.
