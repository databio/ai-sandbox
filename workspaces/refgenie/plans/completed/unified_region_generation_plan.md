# Plan: Unify Region Generation for Benchmarks

## Goal

**Strict separation between data generation and benchmarking:**

1. `./run_benchmark.py setup` - Generates ALL data (FASTA files + BED files)
2. `./run_benchmark.py run ...` - Runs benchmarks on pre-generated data (no generation)

Currently, region generation is embedded inside benchmark scripts. This violates separation of concerns and causes:
- Different regions per batch size
- Different regions per tool
- Cross-language inconsistency (R vs Python)
- Can't re-run benchmarks on same data

**After this change:** Run `setup` once, then `run` benchmarks repeatedly on identical data.

## Context Files to Read

- `refgetstore_benchmark/cli.py` - Current setup/run commands
- `refgetstore_benchmark/benchmarks/region_extraction.py` - Python benchmark with embedded `generate_random_regions()`
- `refgetstore_benchmark/benchmarks/rsamtools_benchmark.R` - R benchmark with embedded `generate_random_regions()`
- `refgetstore_benchmark/benchmarks/biostrings_benchmark.R` - R benchmark with embedded `generate_random_regions()`
- `refgetstore_benchmark/generators/bed.py` - Existing BED file generator
- `refgetstore_benchmark/utils.py` - Contains `generate_synthetic_bed()` and `load_bed()`

## Architecture

```
./run_benchmark.py setup [--run-dir DIR]
    │
    ├── Generate FASTA files (generators/fasta.py)
    │   └── data/baseline/genome_ucsc.fa
    │   └── data/naming_variants/*.fa.gz
    │   └── data/pangenome/*.fa.gz
    │
    └── Generate BED files (4 sizes x 2 region sizes = 8 files)
        └── bed_files/regions_1k_100bp.bed      # 1,000 regions x 100bp
        └── bed_files/regions_1k_1kb.bed        # 1,000 regions x 1kb
        └── bed_files/regions_10k_100bp.bed     # 10,000 regions x 100bp
        └── bed_files/regions_10k_1kb.bed       # 10,000 regions x 1kb
        └── bed_files/regions_100k_100bp.bed    # 100,000 regions x 100bp
        └── bed_files/regions_100k_1kb.bed      # 100,000 regions x 1kb
        └── bed_files/regions_1m_100bp.bed      # 1,000,000 regions x 100bp
        └── bed_files/regions_1m_1kb.bed        # 1,000,000 regions x 1kb

./run_benchmark.py run region [--run-dir DIR]
    │
    └── Loads pre-generated BED files (NO GENERATION)
        └── For batch_size=100: load regions_1k_1kb.bed[:100]
        └── For batch_size=1000: load regions_1k_1kb.bed[:1000]
        └── For batch_size=10000: load regions_10k_1kb.bed[:10000]
        └── etc.
```

## BED File Sizing Strategy

**4 region counts:** 1k, 10k, 100k, 1M
**2 region sizes:** 100bp, 1kb

Benchmarks select the smallest file that contains enough regions:
- batch_size ≤ 1,000 → use `regions_1k_*.bed`
- batch_size ≤ 10,000 → use `regions_10k_*.bed`
- batch_size ≤ 100,000 → use `regions_100k_*.bed`
- batch_size ≤ 1,000,000 → use `regions_1m_*.bed`

## Current Problem

### Setup generates BED files, but benchmarks ignore them:

**cli.py `_run_setup()` (lines 63-71):**
```python
configs = [
    ("sparse_100bp", 100, 100),
    ("medium_1kb", 10000, 1000),
    # ...
]
for name, n_regions, size in configs:
    generate_synthetic_bed(chrom_sizes, n_regions, size, ctx.bed_files / f"{name}.bed")
```

**But region_extraction.py generates its own (line 401):**
```python
regions = generate_random_regions(chroms, region_size, batch_size)  # WRONG
```

**And R scripts generate their own (rsamtools line 178, biostrings line 175):**
```r
regions <- generate_random_regions(chrom_names, chrom_lengths, region_size, batch_size)  # WRONG
```

## Implementation Steps

### Step 1: Update BED file configs in `cli.py`

Update `_run_setup()` to generate BED files with standardized region counts:

```python
def _run_setup(ctx: RunContext):
    # ... existing FASTA generation ...

    # Generate BED files: 4 sizes x 2 region sizes
    # Naming: regions_{count}_{size}.bed
    region_counts = [1_000, 10_000, 100_000, 1_000_000]  # 1k, 10k, 100k, 1M
    region_sizes = [100, 1000]  # 100bp, 1kb

    for count in region_counts:
        for size in region_sizes:
            # Format count: 1000 -> "1k", 10000 -> "10k", 1000000 -> "1m"
            count_str = f"{count // 1000}k" if count < 1_000_000 else "1m"
            size_str = "100bp" if size == 100 else "1kb"
            filename = f"regions_{count_str}_{size_str}.bed"
            generate_synthetic_bed(chrom_sizes, count, size, ctx.bed_files / filename)
```

### Step 2: Add helper to select appropriate BED file

Add to `utils.py`:

```python
def get_bed_file_for_batch(bed_dir: Path, batch_size: int, region_size: int) -> Path:
    """Select the smallest BED file that contains enough regions.

    Args:
        bed_dir: Directory containing BED files
        batch_size: Number of regions needed
        region_size: Size of each region (100 or 1000)

    Returns:
        Path to appropriate BED file
    """
    size_str = "100bp" if region_size < 1000 else "1kb"

    # Select smallest file that has enough regions
    if batch_size <= 1_000:
        count_str = "1k"
    elif batch_size <= 10_000:
        count_str = "10k"
    elif batch_size <= 100_000:
        count_str = "100k"
    else:
        count_str = "1m"

    return bed_dir / f"regions_{count_str}_{size_str}.bed"
```

### Step 3: Update Python benchmark to ONLY load (no generate)

**region_extraction.py** - Remove `generate_random_regions()` function entirely. Update `run_random_benchmark()`:

```python
from ..utils import get_bed_file_for_batch, load_bed

def run_random_benchmark(
    fasta_path: Path,
    stores_dir: Path,
    bed_dir: Path,          # NEW: required
    region_size: int,
    batch_sizes: list[int],
    parallel: bool,
) -> list[dict]:
    """Run random region extraction benchmark using pre-generated BED files."""

    results = []

    for batch_size in batch_sizes:
        # Select appropriate BED file for this batch size
        bed_file = get_bed_file_for_batch(bed_dir, batch_size, region_size)

        if not bed_file.exists():
            print(f"ERROR: BED file not found: {bed_file}")
            print("Run './run_benchmark.py setup' first to generate test data.")
            return []

        all_regions = load_bed(bed_file)
        regions = all_regions[:batch_size]
        print(f"Loaded {len(regions)} regions from {bed_file.name}")

        # ... rest of benchmark ...
```

Delete:
- `generate_random_regions()` function (lines 48-63)
- `get_chromosome_info()` function (lines 40-45) - no longer needed

### Step 4: Update R benchmarks to ONLY load (no generate)

**rsamtools_benchmark.R and biostrings_benchmark.R:**

Add `--bed-dir` command line option:
```r
option_list <- list(
  # ... existing options ...
  make_option(c("--bed-dir"), type = "character", default = NULL,
              help = "Directory containing pre-generated BED files (required)")
)
```

Replace `generate_random_regions()` with `load_regions_from_bed()`:
```r
load_regions_from_bed <- function(bed_dir, region_size, count) {
  # Select smallest file that has enough regions
  size_str <- if (region_size >= 1000) "1kb" else "100bp"

  if (count <= 1000) {
    count_str <- "1k"
  } else if (count <= 10000) {
    count_str <- "10k"
  } else if (count <= 100000) {
    count_str <- "100k"
  } else {
    count_str <- "1m"
  }

  filename <- sprintf("regions_%s_%s.bed", count_str, size_str)
  filepath <- file.path(bed_dir, filename)

  if (!file.exists(filepath)) {
    stop(sprintf("BED file not found: %s\nRun './run_benchmark.py setup' first.", filepath))
  }

  # Read BED file (0-based, half-open coordinates)
  regions <- read.table(filepath, sep="\t", header=FALSE,
                        col.names=c("chrom", "start", "end"),
                        stringsAsFactors=FALSE)

  # Take first `count` regions
  regions <- head(regions, count)

  # Convert to 1-based for R/Bioconductor
  regions$start <- regions$start + 1

  return(regions)
}
```

Update benchmark loop:
```r
# OLD:
regions <- generate_random_regions(chrom_names, chrom_lengths, opt$`region-size`, batch_size)

# NEW:
regions <- load_regions_from_bed(opt$`bed-dir`, opt$`region-size`, batch_size)
```

Delete the old `generate_random_regions()` function from both R scripts.

### Step 5: Update CLI to pass BED directory to R scripts

**cli.py** - Modify `_run_r_benchmark()`:

```python
def _run_r_benchmark(ctx: RunContext, name: str):
    script = Path(__file__).parent / "benchmarks" / f"{name}_benchmark.R"
    subprocess.run([
        "Rscript", str(script),
        "--run-dir", str(ctx.run_dir),
        "--bed-dir", str(ctx.bed_files),  # NEW: pass BED directory
    ], check=True)
```

### Step 6: Update `run()` function in region_extraction.py

Pass `bed_dir` through to `run_random_benchmark()`:

```python
def run(ctx: "RunContext", random: bool = True, bed: bool = False, ...):
    # ...
    if random:
        results = run_random_benchmark(
            fasta_path=fasta_path,
            stores_dir=ctx.stores,
            bed_dir=ctx.bed_files,  # NEW: pass BED directory
            region_size=region_size,
            batch_sizes=batch_sizes,
            parallel=True,
        )
```

### Step 7: Delete duplicate code

Remove entirely:
- `region_extraction.py`: `generate_random_regions()` (lines 48-63)
- `region_extraction.py`: `get_chromosome_info()` (lines 40-45)
- `rsamtools_benchmark.R`: `generate_random_regions()` (lines 102-127)
- `biostrings_benchmark.R`: `generate_random_regions()` (lines 100-126)

## File Changes Summary

| File | Action |
|------|--------|
| `cli.py` | EDIT - Update BED generation to 4 sizes x 2 region sizes, pass `--bed-dir` to R |
| `utils.py` | EDIT - Add `get_bed_file_for_batch()` helper |
| `benchmarks/region_extraction.py` | EDIT - Load from BED files, delete `generate_random_regions()`, delete `get_chromosome_info()` |
| `benchmarks/rsamtools_benchmark.R` | EDIT - Add `--bed-dir`, use `load_regions_from_bed()`, delete `generate_random_regions()` |
| `benchmarks/biostrings_benchmark.R` | EDIT - Add `--bed-dir`, use `load_regions_from_bed()`, delete `generate_random_regions()` |

## Generated BED Files

| File | Regions | Region Size | Use Case |
|------|---------|-------------|----------|
| `regions_1k_100bp.bed` | 1,000 | 100bp | Small batches, short regions |
| `regions_1k_1kb.bed` | 1,000 | 1kb | Small batches, typical regions |
| `regions_10k_100bp.bed` | 10,000 | 100bp | Medium batches, short regions |
| `regions_10k_1kb.bed` | 10,000 | 1kb | Medium batches, typical regions |
| `regions_100k_100bp.bed` | 100,000 | 100bp | Large batches, short regions |
| `regions_100k_1kb.bed` | 100,000 | 1kb | Large batches, typical regions |
| `regions_1m_100bp.bed` | 1,000,000 | 100bp | Stress test, short regions |
| `regions_1m_1kb.bed` | 1,000,000 | 1kb | Stress test, typical regions |

## Usage After Implementation

```bash
# Generate all test data once
./run_benchmark.py setup

# Run benchmarks (can repeat on same data)
./run_benchmark.py run region --random --count 100      # uses regions_1k_1kb.bed
./run_benchmark.py run region --random --count 1000     # uses regions_1k_1kb.bed
./run_benchmark.py run region --random --count 10000    # uses regions_10k_1kb.bed
./run_benchmark.py run region --random --count 100000   # uses regions_100k_1kb.bed
./run_benchmark.py run region --random --count 1000000  # uses regions_1m_1kb.bed

./run_benchmark.py run rsamtools
./run_benchmark.py run biostrings

# Re-run with different parameters (same data)
./run_benchmark.py run region --random --count 5000 --region-size 100
```

## Before/After Comparison

| Metric | Before | After |
|--------|--------|-------|
| Data generation in benchmarks | YES (3 places) | NO (setup only) |
| Region generators | 3 (2 R + 1 Python) | 1 (`cli.py` setup) |
| Re-runnable on same data | NO | YES |
| Cross-tool consistency | NO | YES (all read same BED files) |
| Lines of duplicate code | ~80 | 0 |
| Region count options | arbitrary | 1k, 10k, 100k, 1M |

## DO NOT MAINTAIN BACKWARDS COMPATIBILITY

This is developmental software. Delete the old inline `generate_random_regions()` functions entirely. Benchmarks that try to generate data should fail with a clear error message directing users to run `setup` first.

## Final Step: Summarize Changes

After implementation, report:
1. Lines of code removed vs added
2. Confirm benchmarks fail gracefully if BED files don't exist
3. Confirm benchmarks can be re-run repeatedly on same generated data
