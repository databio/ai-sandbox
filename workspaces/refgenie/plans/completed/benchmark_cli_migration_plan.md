# Benchmark CLI Migration Plan

**Status:** Proposed
**Date:** 2026-01-19

## Overview

Migrate the refgetstore-benchmark codebase from using the gtars Python API directly to using the `refget` CLI. This will:

1. Make benchmarks more representative of real-world usage
2. Provide apples-to-apples CLI comparisons (refget vs samtools vs bedtools)
3. Simplify the benchmark code by removing Python API imports
4. Test the CLI itself as part of benchmarking

## Context Files to Read

Before implementing, read these files to understand current state:

1. `refgetstore_benchmark/utils.py` - Tool availability checks, factory functions
2. `refgetstore_benchmark/benchmarks/region_extraction.py` - Main benchmark using Python API
3. `refgetstore_benchmark/benchmarks/deduplication.py` - Deduplication benchmark
4. `/home/nsheff/Dropbox/workspaces/refgenie/repos/refget/refget/cli/store.py` - CLI implementation

## Prerequisites (Must Be Done First)

Before this migration, the refget CLI needs one enhancement:

### Add `--mode` flag to CLI

The CLI currently lacks storage mode selection. Add to `refget/cli/store.py`:

```bash
refget store init --path /path --mode encoded|raw
refget store add genome.fa --path /path --mode encoded|raw
```

See `plans/cli_storage_mode_plan.md` for details.

## Migration Steps

### Step 1: Replace `create_refgetstore_variants()` with CLI calls

**Current (utils.py:94-182):**
```python
store = Tools.RefgetStore.on_disk(str(store_path))
store.set_encoding_mode(Tools.StorageMode.Encoded)
store.add_sequence_collection_from_fasta(str(fasta_path))
cols = store.collections()
digest = cols[0].digest if cols else None
```

**New:**
```python
def create_refgetstore_via_cli(
    store_path: Path,
    fasta_path: Path,
    mode: str = "encoded",
) -> str | None:
    """Create RefgetStore and add FASTA using CLI. Returns digest."""
    # Initialize store
    subprocess.run(
        ["refget", "store", "init", "--path", str(store_path), "--mode", mode],
        check=True, capture_output=True
    )
    # Add FASTA and get digest
    result = subprocess.run(
        ["refget", "store", "add", str(fasta_path), "--path", str(store_path)],
        check=True, capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    return data.get("digest")
```

### Step 2: Replace `extract_with_refgetstore()` with CLI calls

**Current (region_extraction.py:70-93):**
```python
seq = store.get_substring(chrom_to_digest[chrom], start, end)
```

**New:**
```python
def extract_with_refget_cli(
    store_path: Path,
    digest: str,
    regions: list[tuple[str, int, int]],
) -> tuple[float, int, list[str]]:
    """Extract sequences using refget CLI."""
    sequences = []
    start_time = time.perf_counter()

    for chrom, start, end in regions:
        result = subprocess.run(
            ["refget", "store", "seq", digest,
             "--name", chrom, "-s", str(start), "-e", str(end),
             "--path", str(store_path)],
            capture_output=True, text=True
        )
        sequences.append(result.stdout.strip())

    elapsed = time.perf_counter() - start_time
    return elapsed, len(sequences), sequences
```

### Step 3: Add batch extraction using BED export

For BED-based benchmarks, use `refget store export --bed`:

```python
def extract_with_refget_cli_bed(
    store_path: Path,
    digest: str,
    bed_path: Path,
) -> tuple[float, int, list[str]]:
    """Extract sequences using refget CLI with BED file."""
    start_time = time.perf_counter()
    result = subprocess.run(
        ["refget", "store", "export", digest,
         "--bed", str(bed_path), "--path", str(store_path)],
        capture_output=True, text=True
    )
    elapsed = time.perf_counter() - start_time

    # Parse FASTA output
    sequences = parse_fasta_output(result.stdout)
    return elapsed, len(sequences), sequences
```

### Step 4: Update deduplication benchmark

**Current (deduplication.py:184-187):**
```python
store.add_sequence_collection_from_fasta(str(fasta))
refgetstore_size = get_directory_size(store_path)
```

**New:**
```python
result = subprocess.run(
    ["refget", "store", "add", str(fasta), "--path", str(store_path)],
    check=True, capture_output=True, text=True
)
digest = json.loads(result.stdout)["digest"]
refgetstore_size = get_directory_size(store_path)
```

### Step 5: Remove Python API imports and Tool checks

Remove from `utils.py`:
- `from gtars.refget import RefgetStore, StorageMode`
- `Tools.RefgetStore`, `Tools.StorageMode` attributes
- `Tools.gtars` availability check via import

Replace with CLI availability check:
```python
Tools.refget_cli = shutil.which("refget") is not None
```

### Step 6: Simplify tool variants

Since CLI adds overhead anyway, simplify to fewer variants:

| Before | After |
|--------|-------|
| RefgetStore (Encoded, disk) | refget (encoded) |
| RefgetStore (Encoded, memory) | *(remove - can't do via CLI)* |
| RefgetStore (Raw, disk) | refget (raw) |
| RefgetStore (Raw, memory) | *(remove - can't do via CLI)* |

Memory variants are not testable via CLI, which is fine - users don't use in-memory stores from CLI.

### Step 7: Update benchmark comparison table

The benchmark now compares CLI tools directly:

| Tool | Command |
|------|---------|
| refget (encoded) | `refget store seq <digest> --name chr1 -s X -e Y` |
| refget (raw) | same, with `--mode raw` store |
| samtools | `samtools faidx genome.fa chr1:X-Y` |
| bedtools | `bedtools getfasta -fi genome.fa -bed regions.bed` |
| pyfaidx | *(Python library - keep for reference)* |

## Files to Modify

1. **`refgetstore_benchmark/utils.py`**
   - Remove gtars imports
   - Add `Tools.refget_cli` check
   - Replace `create_refgetstore_variants()` with CLI version
   - Remove `create_single_refgetstore()`

2. **`refgetstore_benchmark/benchmarks/region_extraction.py`**
   - Replace `extract_with_refgetstore()` with `extract_with_refget_cli()`
   - Add `extract_with_refget_cli_bed()` for BED mode
   - Update `setup_tools()` to use CLI
   - Remove in-memory variants from benchmark matrix

3. **`refgetstore_benchmark/benchmarks/deduplication.py`**
   - Replace direct store creation with CLI calls
   - Remove gtars-specific code

4. **`refgetstore_benchmark/benchmarks/storage_size.py`**
   - Replace `get_refgetstore_size()` to use CLI for store creation

## Summary of Improvements

**Before migration:**
- ~200 lines of Python API wrapper code in utils.py
- 4 RefgetStore variants (Encoded/Raw × disk/memory)
- Benchmarks Python library overhead, not CLI overhead
- Unfair comparison (Python API vs CLI tools)

**After migration:**
- ~50 lines of subprocess calls
- 2 RefgetStore variants (Encoded/Raw, disk only)
- Benchmarks actual CLI performance
- Fair comparison (CLI vs CLI)

## Important Notes

**DO NOT MAINTAIN BACKWARDS COMPATIBILITY.** This is developmental software. We are:
- Removing the Python API usage entirely
- Removing in-memory store benchmarks
- Removing the `Tools.gtars`, `Tools.RefgetStore`, `Tools.StorageMode` attributes
- Simplifying to CLI-only approach

The goal is a clean, simple benchmark that tests tools as users actually use them.
