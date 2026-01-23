# Benchmark Timing Calibration Guide

## Overview

The benchmark suite is structured as a Python package (`refgetstore_benchmark/`) with a unified run system. Each benchmark should complete in **10-60 seconds** - not too fast (indicating trivial tests) and not too slow (impractical for iteration).

## Prerequisites

1. **Docker** installed and running
2. **gtars source** available (needed for building the Docker image):
   ```bash
   export GTARS_PATH=/home/nsheff/Dropbox/workspaces/refgenie/repos/gtars
   ```

## Quick Start: Full Suite

Run everything with one command:

```bash
cd repos/refgetstore-benchmark
./run_all_docker.sh
```

This:
1. Copies gtars-python into the build context
2. Builds the Docker image with gtars baked in
3. Cleans up the gtars-python copy
4. Runs all benchmarks
5. Generates figures and report

Output goes to a timestamped `runs/` directory with `runs/latest` symlink.

Options:
```bash
./run_all_docker.sh --skip-build   # Skip Docker build if image exists
./run_all_docker.sh --no-log       # Don't write to log file
```

## Running Individual Benchmarks

Set up the common Docker command:

```bash
cd repos/refgetstore-benchmark
DOCKER_RUN="docker run --rm -v $(pwd):/app -w /app refgetstore-benchmark"
RUN_DIR="runs/latest"
```

### 1. Generate Test Data First

```bash
$DOCKER_RUN python -m refgetstore_benchmark.generators.fasta --output-dir $RUN_DIR/data
```

Creates ~25MB genomes:
- `naming_variants/` - 5 FASTAs with identical sequences, different naming (key deduplication demo)
- `pangenome/` - 3 haplotypes with ~0.1% SNP differences (control case)
- `baseline/` - Single uncompressed reference

### 2. Individual Benchmark Commands

| Benchmark | Command | Target Time |
|-----------|---------|-------------|
| Deduplication | `$DOCKER_RUN python -m refgetstore_benchmark.benchmarks.deduplication --dataset naming_variants --run-dir $RUN_DIR` | 10-30s |
| Storage Size | `$DOCKER_RUN python -m refgetstore_benchmark.benchmarks.storage_size --run-dir $RUN_DIR` | 10-30s |
| Region Extraction | `$DOCKER_RUN python -m refgetstore_benchmark.benchmarks.region_extraction --random --bed --run-dir $RUN_DIR` | 30-60s |
| Export FASTA | `$DOCKER_RUN python -m refgetstore_benchmark.benchmarks.export_fasta --run-dir $RUN_DIR` | 10-30s |
| Scaling | `$DOCKER_RUN python -m refgetstore_benchmark.benchmarks.scaling --run-dir $RUN_DIR` | 10-30s |
| Rsamtools (R) | `$DOCKER_RUN Rscript refgetstore_benchmark/benchmarks/rsamtools_benchmark.R $RUN_DIR` | 10-30s |
| Biostrings (R) | `$DOCKER_RUN Rscript refgetstore_benchmark/benchmarks/biostrings_benchmark.R $RUN_DIR` | 10-30s |

### 3. Generate Analysis

```bash
# Figures
$DOCKER_RUN python -m refgetstore_benchmark.analysis.figures --run-dir $RUN_DIR

# Report
$DOCKER_RUN python -m refgetstore_benchmark.analysis.generate_report --run-dir $RUN_DIR
```

## Timing Calibration Details

### Test Data Sizes (fasta.py)

Current chromosome sizes (~25MB total):
```python
sizes = {
    "chr1": 10_000_000,   # 10MB
    "chr2": 7_500_000,    # 7.5MB
    "chr3": 5_000_000,    # 5MB
    "chr4": 2_500_000,    # 2.5MB
    "chrM": 16500,        # ~16.5kb
}
```

### BED Region Counts

The run script generates these BED files:
```python
configs = [
    ('sparse_100bp', 100, 100),      # Quick validation
    ('sparse_10kb', 100, 10000),     # Quick validation
    ('medium_100bp', 10000, 100),    # Target: 10-20s
    ('medium_1kb', 10000, 1000),     # Target: 10-20s
    ('dense_10kb', 10000, 10000),    # Heavy workload: 30-60s
]
```

RefgetStore (Raw) processes ~1,000-2,000 regions/second, so:
- 2,000 regions = ~10-20 seconds
- 10,000 regions = ~30-60 seconds

## Adjusting If Timing Is Off

**If benchmark is too fast (<10 seconds):**
- Increase genome sizes in `refgetstore_benchmark/generators/fasta.py` (multiply by 2x)
- Increase region counts in the run script's BED generation
- Add more iterations to specific benchmarks

**If benchmark is too slow (>60 seconds):**
- Decrease region counts in BED files
- Use smaller test data
- Skip the heaviest BED files for quick iterations

## Verifying Results

Check `runs/latest/results/` for:
- `deduplication.csv` - RefgetStore size should be ~5-6MB (not 0), showing 5x savings
- `storage_size.csv` - Multiple format comparisons
- `random_access.csv` - Timing data for each tool
- `bed_extraction.csv` - Timing data per BED file
- `REPORT.md` - Full summary with statistics

### Troubleshooting RefgetStore Issues

If RefgetStore shows 0 bytes or fails silently:

1. **Test gtars directly:**
   ```python
   from gtars.refget import RefgetStore
   store = RefgetStore.on_disk("/tmp/test_store")
   store.add_sequence_collection_from_fasta("path/to/genome.fa.gz")
   # Should see loading output, store should be several MB
   ```

2. **Verify gtars is the dev version** (not PyPI release):
   ```bash
   ls $GTARS_PATH/gtars-python
   ```

3. **Rebuild the Docker image** to pick up gtars changes:
   ```bash
   ./run_all_docker.sh  # Without --skip-build
   ```

## Output Structure

Each run creates:
```
runs/2026-01-17-143022/
├── results/           # CSV benchmark data
├── plots/             # Generated figures
├── stores/            # RefgetStore instances
├── data/              # Test FASTAs
├── bed_files/         # BED files for queries
├── config.json        # Run metadata
└── benchmark.log      # Full execution log
```

The symlink `runs/latest` always points to the most recent run.

## Docker Image Architecture

gtars is baked into the Docker image at build time:

1. `run_all_docker.sh` copies the entire `$GTARS_PATH` to the build context (needed for workspace dependencies)
2. Dockerfile copies gtars and pip installs gtars-python from it
3. Build context copy is cleaned up after build

This means:
- No runtime gtars installation needed
- If you update gtars, rebuild the image (don't use `--skip-build`)
- gtars/ is in .gitignore (it's only there temporarily during builds)
