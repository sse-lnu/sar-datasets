# Method dependency generation

## Scope

This generation contains method-level dependency matrices for every packaged
system except Chromium. Chromium remains pending so downstream experiments can
start without waiting for its substantially longer extraction.

## Frozen extractor

- Tool: Depends 0.9.7
- JAR SHA-256: `004b232f258b15a85195accb37905a339a01de7b99ea5029be3fc0ea8d3664e7`
- JAR build date: 2022-11-04
- Runtime used for this generation: OpenJDK 11.0.25
- Java frontend: the legacy ANTLR parser exposed as `java` in version 0.9.7

The JAR is deliberately not committed. Supply a local copy whose hash matches
the value above; the generation script rejects any other artifact.

## Java matrices

Java systems use Depends' native method generator:

```text
java -Xmx32g -jar depends.jar -s -f=json -g=method \
  -d=<work/system> java <full-source-root> <matrix-base-name>
```

## C/C++ projection

Depends 0.9.7's native method generator emits method nodes but zero edges for
the C/C++ systems tested here. This is an output-generator defect: the same
unmodified parser records the function relations in its detailed structure
matrix. For example, the HDC pilot emitted 2,511 native method nodes and zero
native method cells, while the detailed structure result contained 1,634
function-to-function relations.

C/C++ extraction therefore requests both native node and detailed structure
outputs:

```text
java -Xmx32g -jar depends.jar -s --auto-include --detail \
  -f=json -g=method,structure -d=<work/system> cpp \
  <full-source-root> <matrix-base-name>
```

`scripts/project-cpp-method-dependencies.py` then:

1. retains the native method variable list;
2. selects details whose source and destination are both function entities;
3. maps their relative file-and-function names to native method nodes;
4. aggregates their original Depends relation types and weights; and
5. fails if any endpoint cannot be matched.

No source parser or extracted relation is replaced or supplemented. The
projection only repairs the released method generator's omission.

## Reproduction

The input root must contain the complete source snapshots at the paths encoded
in `scripts/generate-method-dependencies.py`. Commons Imaging may be supplied
separately because it was added after the original full-snapshot collection.

```sh
python3 scripts/generate-method-dependencies.py \
  --jar /path/to/depends-0.9.7.jar \
  --datasets /path/to/full-snapshots \
  --commons-root /path/to/commons-imaging-a2d77b8 \
  --work /path/to/new-empty-work-directory \
  --output /path/to/output-directory
```

The default system set is the 14-system non-Chromium generation. A future
Chromium-only extraction can use `--systems chromium` and must be added to a new
manifest rather than silently altering this one.

## Validation

Run:

```sh
python3 scripts/verify-method-dependencies.py
./scripts/verify-checksums.sh
```

The first command checks manifest membership, compressed hashes, matrix names,
node and cell counts, relative paths, index bounds, nonempty edge sets, and the
C/C++ unmatched-endpoint count. The second verifies repository-wide artifact
checksums.
