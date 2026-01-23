# RefgetStore-Benchmark Maintenance Plan

## Goal

Simplify and consolidate the refgetstore-benchmark codebase without removing features. Reduce code duplication, improve maintainability, and decrease total line count while preserving all benchmark functionality.

**DO NOT MAINTAIN BACKWARDS COMPATIBILITY.** This is developmental software. Legacy code, deprecated patterns, and compatibility shims should be removed, not preserved.

---

## Current State Baseline

```
$ find . -path './.venv' -prune -o -name '*.py' -type f -print | xargs wc -l | sort -n

     7 ./analysis/__init__.py
    17 ./benchmarks/__init__.py
   141 ./analysis/report_templates.py
   209 ./bed_files/generate_synthetic.py
   230 ./benchmarks/region_extraction.py
   249 ./benchmarks/utils.py
   269 ./benchmarks/verify_setup.py
   333 ./data/generate_test_data.py
   433 ./benchmarks/storage_size.py
   445 ./benchmarks/deduplication.py
   458 ./analysis/generate_report.py
   503 ./benchmarks/scaling.py
   583 ./analysis/figures.py
   606 ./benchmarks/export_fasta.py
   638 ./benchmarks/random_access.py
   774 ./benchmarks/bed_extraction.py
  5895 total
```

---

## Files to Read for Context

Before implementation, read these files to understand the patterns:

1. `benchmarks/utils.py` - Core utilities (formatting, timing, file operations)
2. `benchmarks/bed_extraction.py` - Largest file, most duplication
3. `benchmarks/random_access.py` - Second largest, parallel patterns
4. `benchmarks/deduplication.py` - Core benchmark demonstrating main value
5. `benchmarks/export_fasta.py` - seqrepo creation pattern duplicated here
6. `benchmarks/scaling.py` - Another seqrepo creation duplicate

---

## Identified Duplication Patterns

### 1. RefgetStore Setup (4 variants × 4 files = ~240 lines)

Each of `bed_extraction.py`, `random_access.py`, `storage_size.py`, and `export_fasta.py` contains ~60 lines of nearly identical code to create 4 RefgetStore variants (Encoded/Raw × disk/memory):

```python
# Pattern repeated in multiple files:
store_encoded_disk = RefgetStore.on_disk(str(store_path_encoded))
store_encoded_disk.set_encoding_mode(StorageMode.Encoded)
store_encoded_disk.add_sequence_collection_from_fasta(str(fasta_path))
cols = store_encoded_disk.collections()
if cols:
    col_digest_encoded_disk = cols[0].digest
# ... repeat for encoded_mem, raw_disk, raw_mem
```

### 2. SeqRepo Creation (~30 lines × 4 files = ~120 lines)

The `create_seqrepo_from_fasta()` function appears in:
- `bed_extraction.py:264-294`
- `random_access.py:234-264`
- `export_fasta.py:258-287`
- `scaling.py:75-116` (as `add_fasta_to_seqrepo`)

All versions are nearly identical: load FASTA with pyfaidx, iterate sequences, call `seqrepo.store()`, commit, return read-only instance.

### 3. Bgzipped FASTA Creation (~40 lines × 2 files = ~80 lines)

The `create_bgzipped_fasta()` function is duplicated between:
- `bed_extraction.py:297-337`
- `random_access.py:267-309`

Both check for bgzip/samtools, create bgzipped file, create indexes.

### 4. Tool Availability Checks (~50 lines scattered)

Each benchmark file independently checks tool availability at module level:
```python
try:
    from gtars.refget import RefgetStore, StorageMode
    GTARS_AVAILABLE = True
except ImportError:
    GTARS_AVAILABLE = False
    print("WARNING: gtars not available...")
```

This pattern repeats for gtars, seqrepo, pyfaidx, and CLI tools (samtools, bgzip, bedtools).

### 5. Benchmark Loop Pattern in bed_extraction.py (~180 lines)

Lines 495-676 contain highly repetitive tool benchmarking:
```python
if GTARS_AVAILABLE and store_encoded_disk is not None and collection_digest_encoded_disk is not None:
    print("RefgetStore (Encoded, disk)...", end=" ", flush=True)
    start_time = time.perf_counter()
    seqs = extract_with_refgetstore(store_encoded_disk, collection_digest_encoded_disk, regions)
    elapsed = time.perf_counter() - start_time
    regions_per_sec = n_regions / elapsed if elapsed > 0 else 0
    print(f"{elapsed:.3f}s ({regions_per_sec:.0f} regions/s)")
    results.append({...})
# Repeated 9 times for different tools
```

---

## Specific Changes to Make

### Step 1: Create Tool Factories in utils.py

Add to `benchmarks/utils.py`:

```python
# Tool availability registry
class Tools:
    gtars = False
    seqrepo = False
    pyfaidx = False
    samtools = False
    bgzip = False
    bedtools = False

try:
    from gtars.refget import RefgetStore, StorageMode
    Tools.gtars = True
except ImportError:
    pass

# ... similar for other tools

def create_refgetstore_variants(
    store_dir: Path,
    fasta_path: Path,
    variants: list[str] | None = None,
) -> dict[str, tuple[RefgetStore | None, str | None]]:
    """Create RefgetStore variants.

    Args:
        store_dir: Base directory for stores
        fasta_path: FASTA file to load
        variants: List of variants to create. Options:
                  "encoded_disk", "encoded_mem", "raw_disk", "raw_mem"
                  Default: all four

    Returns:
        Dict mapping variant name to (store, collection_digest) tuple
    """
    if not Tools.gtars:
        return {}
    # Implementation...

def create_seqrepo(fasta_path: Path, seqrepo_path: Path) -> SeqRepo | None:
    """Create seqrepo from FASTA, returning read-only instance."""
    if not Tools.seqrepo:
        return None
    # Implementation...

def create_bgzipped_fasta(fasta_path: Path) -> tuple[Path, Path] | None:
    """Create bgzipped FASTA with indexes."""
    if not Tools.bgzip or not Tools.samtools:
        return None
    # Implementation...
```

**Estimated savings**: ~300 lines removed from individual benchmark files.

### Step 2: Create Result Recording Helper

Add to `benchmarks/utils.py`:

```python
def record_benchmark_result(
    tool_name: str,
    elapsed: float,
    count: int,
    **extra_fields,
) -> dict:
    """Create a standardized benchmark result dict."""
    return {
        "tool": tool_name,
        "total_seconds": elapsed,
        "count": count,
        "throughput": count / elapsed if elapsed > 0 else 0,
        **extra_fields,
    }
```

### Step 3: Refactor bed_extraction.py Benchmark Loop

Replace the 180-line repeated benchmark loop with a data-driven approach:

```python
# Define tool configurations
TOOL_CONFIGS = [
    ("RefgetStore (Encoded, disk)", lambda: (store_encoded_disk, col_digest_encoded_disk), extract_with_refgetstore),
    ("RefgetStore (Encoded, memory)", lambda: (store_encoded_mem, col_digest_encoded_mem), extract_with_refgetstore),
    # ... etc for other tools
]

# Run benchmarks
for tool_name, get_params, extract_func in TOOL_CONFIGS:
    params = get_params()
    if params[0] is None:
        continue
    print(f"{tool_name}...", end=" ", flush=True)
    start_time = time.perf_counter()
    seqs = extract_func(*params, regions)
    elapsed = time.perf_counter() - start_time
    results.append(record_benchmark_result(tool_name, elapsed, len(regions), ...))
```

**Estimated savings**: ~140 lines in bed_extraction.py.

### Step 4: Remove Legacy "test" Dataset Mapping

In `deduplication.py` (lines 415-418), remove:
```python
elif args.dataset == "test":
    # Legacy: map "test" to "naming_variants" for backward compatibility
    data_dir = Path(__file__).parent.parent / "data" / "test" / "naming_variants"
    args.dataset = "naming_variants"
```

Also remove "test" from the `choices` list in the argparser.

### Step 5: Consolidate random_access.py Task Definitions

Replace the 8 separate `run_*` functions (lines 451-505) with a dictionary-driven approach:

```python
BENCHMARK_TASKS = {
    "pyfaidx (uncompressed)": lambda: benchmark_pyfaidx_single(str(fasta_path), regions) if PYFAIDX_AVAILABLE else None,
    "pyfaidx (bgzipped)": lambda: benchmark_pyfaidx_single(str(bgzip_fasta_path), regions, str(bgzip_gzi_path)) if bgzip_fasta_path else None,
    # ... etc
}

for task_name, task_func in BENCHMARK_TASKS.items():
    result = task_func()
    if result is not None:
        # record result
```

**Estimated savings**: ~40 lines.

### Step 6: Simplify Report Templates

In `analysis/report_templates.py`, the interpretation templates for different dataset types are similar. Consider consolidating into a single template with conditional formatting.

---

## Items to Remove Completely

1. **Legacy "test" dataset support** in `deduplication.py` - Remove the "test" choice and mapping code
2. **Duplicate `create_seqrepo_from_fasta` functions** - Keep only in utils.py
3. **Duplicate `create_bgzipped_fasta` functions** - Keep only in utils.py
4. **Duplicate tool availability checks** - Consolidate in utils.py as `Tools` class

---

## Verification Steps

After each refactoring step:

1. **Run all benchmarks with --help** to verify CLI still works:
   ```bash
   python -m benchmarks.deduplication --help
   python -m benchmarks.random_access --help
   python -m benchmarks.bed_extraction --help
   python -m benchmarks.export_fasta --help
   python -m benchmarks.scaling --help
   ```

2. **Generate test data** and run a quick functional test:
   ```bash
   python data/generate_test_data.py
   python -m benchmarks.deduplication --dataset naming_variants
   ```

3. **Run report generation** to ensure analysis still works:
   ```bash
   python -m analysis.generate_report
   ```

4. **Diff CSV outputs** before and after refactoring to verify results are identical.

---

## Expected Outcomes

### Line Count Reduction Estimate

| File | Current | After | Reduction |
|------|---------|-------|-----------|
| utils.py | 249 | ~350 | +101 (consolidation target) |
| bed_extraction.py | 774 | ~500 | -274 |
| random_access.py | 638 | ~450 | -188 |
| export_fasta.py | 606 | ~450 | -156 |
| scaling.py | 503 | ~400 | -103 |
| deduplication.py | 445 | ~430 | -15 |
| **Total** | 5895 | ~5200 | **~700 lines** |

### Quality Improvements

- Single source of truth for tool availability checks
- Single source of truth for store/seqrepo creation
- Data-driven benchmark loops instead of copy-paste
- No legacy compatibility code to maintain
- Easier to add new tools to benchmarks

---

## Summary of Improvements

After implementation:

1. **Calculate new line counts**:
   ```bash
   find . -path './.venv' -prune -o -name '*.py' -type f -print | xargs wc -l | sort -n
   ```

2. **Document changes**:
   - Before/after line counts
   - List of removed functions
   - New utilities added
   - Benchmarks verified working

---

## Critical Reminder

**DO NOT MAINTAIN BACKWARDS COMPATIBILITY.**

This is developmental software. When you encounter:
- Old argument names → Remove them
- Legacy dataset mappings → Remove them
- Deprecated function signatures → Change them directly
- Compatibility shims → Delete them

The goal is to eliminate technical debt, not preserve it.
