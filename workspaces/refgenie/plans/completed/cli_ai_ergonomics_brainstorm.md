# CLI Ergonomics Brainstorm: AI and Benchmarking Insights

**Status**: CONSOLIDATED into `refget_cli_command_structure.md`

The ideas below have been incorporated into the main CLI design document:
- JSON-first output → "Output Format by Command" section
- Meaningful exit codes → "Exit Codes" section
- Auto .gz handling → "Gzip Handling" section

**Not incorporated:**
- `check` command group → Decided against; use `seqcol compare` instead

---

*Original brainstorm preserved below for reference:*

This document captures ideas for improving the refget CLI ergonomics from two sources:
1. What an AI agent would want from a CLI
2. Patterns observed in refgetstore-benchmark that could be simplified

---

## Part 1: AI/Machine-Friendly Design

### JSON-First Output

All commands output pretty-printed JSON by default. No `--json` flag needed.

**Rationale:**
- Primary users are pipelines, scripts, and AI agents
- Pretty-printed JSON is human-readable too
- Consistent, parseable output everywhere
- Use `jq` to extract specific fields when needed

```bash
refget fasta digest genome.fa
# {
#   "digest": "abc123...",
#   "file": "genome.fa"
# }

refget fasta digest genome.fa | jq -r .digest
# abc123...
```

### Check Command Group

Consolidate validation and compatibility checking into one `check` group:

```bash
refget check <fasta> <digest>             # Does file match digest?
refget check <fasta> --fai <file>         # Does FAI match FASTA?
refget check <fasta> --seqcol <file>      # Does seqcol.json match?
refget check <a> <b>                      # Are these compatible?
```

**Auto-detection based on inputs:**
- File + digest → validation
- Two digests → compatibility check
- Two files → compute digests and compare
- File + .fai/.seqcol.json → validate index matches

**Example outputs:**

```json
{
  "valid": true,
  "file": "genome.fa",
  "expected": "abc123...",
  "actual": "abc123...",
  "match": "exact"
}
```

```json
{
  "compatible": true,
  "shared_sequences": 24,
  "a_only": 1,
  "b_only": 0,
  "recommendation": "compatible for most analyses"
}
```

### Meaningful Exit Codes

```
Exit 0 = success/valid/compatible
Exit 1 = invalid/incompatible/mismatch
Exit 2 = file not found or other error
```

### Commands NOT Needed (Covered Elsewhere)

- ~~`manifest`~~ → `fasta seqcol` already outputs the seqcol JSON, which IS the manifest
- ~~`identify`~~ → `seqcol search --names` and `seqcol search --lengths` already cover this

---

## Part 2: Benchmark Analysis - Repeated Patterns

Analysis of `/repos/refgetstore-benchmark` revealed patterns that should be simplified:

### Pattern A: Gzip Decompression Boilerplate (3 benchmarks, ~60 lines)

**Current:**
```python
def decompress_gzip_if_needed(fasta_path, temp_dir):
    if fasta_path.suffix == ".gz":
        # ... 20 lines of decompression logic
```

**Solution:** `refget store add` and `refget fasta *` commands should handle `.gz` files automatically.

### Pattern B: Store Creation + Load + Get Digest (5 benchmarks)

**Current (10+ lines):**
```python
store = RefgetStore.on_disk(path)
store.add_sequence_collection_from_fasta(fasta)
cols = store.collections()
digest = cols[0].digest
```

**CLI (1 line):**
```bash
refget store add genome.fa
# {"digest": "abc123...", "sequences": 25, "total_length": 3100000000}
```

### Pattern C: Find Collection by Chromosome Names

**Current (15 lines):**
```python
def find_matching_collection(store, regions):
    bed_chroms = set(chrom for chrom, _, _ in regions)
    for collection in store.collections():
        # ... matching logic
```

**CLI:**
```bash
refget store find --names chr1,chr2,chr3
# {"digest": "abc123...", "match": "exact", "matched_names": ["chr1", "chr2", "chr3"]}
```

### Pattern D: Store Statistics (scattered)

**Current:**
```python
def get_directory_size(path):
    # manual directory traversal
```

**CLI:**
```bash
refget store stats
# {"collections": 3, "sequences": 75, "total_size": "2.1 GB", "encoded": true}
```

---

## Summary: Two Key Additions

| Addition | Purpose | Impact |
|----------|---------|--------|
| **JSON-first output** | Machine-readable by default | All commands, enables AI/scripting |
| **`check` command group** | Validation + compatibility | New capability for verification workflows |

Plus one implementation fix:
- **Auto .gz handling** in `store add` and `fasta *` commands (~60 lines of boilerplate eliminated)

---

## Related Documents

- `refget_cli_command_structure.md` - Main CLI design plan
- `/repos/refgetstore-benchmark/` - Source of benchmark patterns
