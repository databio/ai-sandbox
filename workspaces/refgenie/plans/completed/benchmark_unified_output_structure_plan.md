# Plan: Unified Output Directory Structure for refgetstore-benchmark

## Overview

Currently, benchmark outputs are scattered across multiple directories at the repository root:
- `results/` - CSV files and logs
- `plots/` - PNG/PDF figures
- `stores/` - RefgetStore and seqrepo instances
- `data/test/` - Generated test FASTAs
- `bed_files/synthetic/` - Generated BED files

This plan restructures all outputs into a single timestamped run directory, making each benchmark run self-contained and easily comparable.

## Target Structure

```
runs/
└── 2026-01-17-143022/          # Timestamped run directory
    ├── results/                 # CSV benchmark data
    │   ├── deduplication_naming_variants.csv
    │   ├── deduplication_pangenome.csv
    │   ├── storage_size.csv
    │   ├── region_extraction.csv
    │   ├── export_fasta.csv
    │   ├── scaling.csv
    │   └── REPORT.md
    │
    ├── plots/                   # Generated figures
    │   ├── deduplication_storage.png
    │   ├── storage_size_comparison.png
    │   └── ...
    │
    ├── stores/                  # RefgetStore/seqrepo instances
    │   ├── naming_variants_store/
    │   ├── naming_variants_seqrepo/
    │   └── ...
    │
    ├── data/                    # Generated test data
    │   ├── medium_genome_ucsc.fa.gz
    │   ├── naming_variants/
    │   └── pangenome/
    │
    ├── bed_files/               # Generated BED files
    │   ├── sparse_100bp.bed
    │   └── ...
    │
    ├── benchmark.log            # Full console output log
    └── config.json              # Run configuration (for reproducibility)
```

## Files to Read for Context

Before implementation, read these files:
1. `repos/refgetstore-benchmark/run_all_docker.sh` - Main orchestration script
2. `repos/refgetstore-benchmark/benchmarks/utils.py` - Shared utilities with path handling
3. `repos/refgetstore-benchmark/benchmarks/deduplication.py` - Example benchmark with output handling
4. `repos/refgetstore-benchmark/benchmarks/region_extraction.py` - Another benchmark example
5. `repos/refgetstore-benchmark/analysis/figures.py` - How figures are generated
6. `repos/refgetstore-benchmark/analysis/generate_report.py` - Report generation
7. `repos/refgetstore-benchmark/data/generate_test_data.py` - Test data generation
8. `repos/refgetstore-benchmark/clean.sh` - Current cleanup script

## Implementation Steps

### Step 1: Create run directory management in utils.py

Add to `benchmarks/utils.py`:

```python
def create_run_directory(base_dir: Path = Path("runs")) -> Path:
    """Create a timestamped run directory with all subdirectories."""
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    run_dir = base_dir / timestamp

    # Create all subdirectories
    (run_dir / "results").mkdir(parents=True, exist_ok=True)
    (run_dir / "plots").mkdir(parents=True, exist_ok=True)
    (run_dir / "stores").mkdir(parents=True, exist_ok=True)
    (run_dir / "data").mkdir(parents=True, exist_ok=True)
    (run_dir / "bed_files").mkdir(parents=True, exist_ok=True)

    return run_dir

def get_latest_run_directory(base_dir: Path = Path("runs")) -> Path:
    """Get the most recent run directory."""
    runs = sorted(base_dir.glob("*-*-*-*"))
    if not runs:
        raise FileNotFoundError("No run directories found")
    return runs[-1]
```

### Step 2: Update run_all_docker.sh

Replace the current directory creation with:

```bash
# Create timestamped run directory
RUN_TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
RUN_DIR="runs/$RUN_TIMESTAMP"
mkdir -p "$RUN_DIR"/{results,plots,stores,data,bed_files}

# Symlink 'latest' to current run
ln -sfn "$RUN_TIMESTAMP" runs/latest

# Update log file location
LOG_FILE="$RUN_DIR/benchmark.log"
```

Update all Docker commands to pass the run directory:

```bash
DOCKER_RUN="docker run --rm \
    -v $(pwd):/app \
    -v $GTARS_PATH:/gtars_src:ro \
    -e RUN_DIR=$RUN_DIR \
    -w /app \
    refgetstore-benchmark"
```

### Step 3: Update data/generate_test_data.py

Change output directory parameter:

```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Output directory for generated test data")
    args = parser.parse_args()

    output_dir = args.output_dir
    # ... rest of generation code uses output_dir instead of hardcoded "data/test/"
```

### Step 4: Update each benchmark script

Each benchmark script needs updated default arguments. Example for `deduplication.py`:

```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path,
                        help="Run directory (contains results/, stores/, data/ subdirs)")
    parser.add_argument("--data-dir", type=Path,
                        help="Override data directory")
    parser.add_argument("--output-dir", type=Path,
                        help="Override results output directory")
    parser.add_argument("--stores-dir", type=Path,
                        help="Override stores directory")
    args = parser.parse_args()

    # Resolve directories from run_dir or individual overrides
    if args.run_dir:
        data_dir = args.data_dir or args.run_dir / "data"
        output_dir = args.output_dir or args.run_dir / "results"
        stores_dir = args.stores_dir or args.run_dir / "stores"
    else:
        # Legacy fallback (for running individual benchmarks)
        data_dir = args.data_dir or Path("data/test")
        output_dir = args.output_dir or Path("results")
        stores_dir = args.stores_dir or Path("stores")
```

Apply similar changes to:
- `benchmarks/storage_size.py`
- `benchmarks/region_extraction.py`
- `benchmarks/export_fasta.py`
- `benchmarks/scaling.py`

### Step 5: Update analysis scripts

Update `analysis/figures.py`:

```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True,
                        help="Run directory containing results/ and plots/")
    args = parser.parse_args()

    results_dir = args.run_dir / "results"
    plots_dir = args.run_dir / "plots"
    # ... use these instead of hardcoded paths
```

Update `analysis/generate_report.py` similarly.

### Step 6: Update BED file generation

Move the inline Python in `run_all_docker.sh` to a proper script or update `data/generate_test_data.py` to also generate BED files:

```python
# In data/generate_test_data.py, add BED generation
def generate_bed_files(chrom_sizes: dict, output_dir: Path):
    """Generate synthetic BED files for benchmarking."""
    configs = [
        ('sparse_100bp', 100, 100),
        ('sparse_10kb', 100, 10000),
        ('medium_100bp', 10000, 100),
        ('medium_1kb', 10000, 1000),
        ('dense_10kb', 10000, 10000),
    ]
    for name, n_regions, size in configs:
        outpath = output_dir / f"{name}.bed"
        generate_synthetic_bed(chrom_sizes, n_regions, size, outpath)
```

### Step 7: Update clean.sh

Simplify cleanup to just remove runs directory:

```bash
#!/bin/bash
# Clean all benchmark runs

set -e
cd "$(dirname "$0")"

echo "Cleaning all benchmark runs..."
rm -rf runs/
echo "Done."
```

Optionally add a script to clean only old runs:

```bash
#!/bin/bash
# Keep only the N most recent runs
N=${1:-5}
cd "$(dirname "$0")"

if [ -d runs ]; then
    ls -dt runs/*-*-*-* | tail -n +$((N+1)) | xargs rm -rf 2>/dev/null || true
    echo "Kept $N most recent runs"
fi
```

### Step 8: Write run configuration

Add to `run_all_docker.sh` after creating the run directory:

```bash
# Save run configuration
cat > "$RUN_DIR/config.json" << EOF
{
    "timestamp": "$RUN_TIMESTAMP",
    "gtars_path": "$GTARS_PATH",
    "docker_image": "refgetstore-benchmark",
    "hostname": "$(hostname)",
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')"
}
EOF
```

### Step 9: Update README.md

Update documentation to reflect new structure:

```markdown
## Quick Start

./run_all_docker.sh

All outputs go to `runs/<timestamp>/`:
- `results/` - CSV benchmark data
- `plots/` - Generated figures
- `stores/` - RefgetStore instances
- `data/` - Test FASTAs
- `bed_files/` - Test BED files
- `benchmark.log` - Full log
- `config.json` - Run configuration

# Access latest run
ls runs/latest/

# Clean all runs
./clean.sh
```

### Step 10: Update .gitignore

```
# Benchmark outputs
runs/
```

Remove old entries for `results/`, `plots/`, `stores/`.

## Summary of Changes

| Before | After |
|--------|-------|
| `results/*.csv` | `runs/<timestamp>/results/*.csv` |
| `plots/*.png` | `runs/<timestamp>/plots/*.png` |
| `stores/` | `runs/<timestamp>/stores/` |
| `data/test/` | `runs/<timestamp>/data/` |
| `bed_files/synthetic/` | `runs/<timestamp>/bed_files/` |
| `results/benchmark_run_*.log` | `runs/<timestamp>/benchmark.log` |

## Files Modified

1. `run_all_docker.sh` - Main orchestration
2. `benchmarks/utils.py` - Add run directory utilities
3. `benchmarks/deduplication.py` - Add --run-dir argument
4. `benchmarks/storage_size.py` - Add --run-dir argument
5. `benchmarks/region_extraction.py` - Add --run-dir argument
6. `benchmarks/export_fasta.py` - Add --run-dir argument
7. `benchmarks/scaling.py` - Add --run-dir argument
8. `analysis/figures.py` - Add --run-dir argument
9. `analysis/generate_report.py` - Add --run-dir argument
10. `data/generate_test_data.py` - Add --output-dir argument, add BED generation
11. `clean.sh` - Simplify to remove runs/
12. `README.md` - Update documentation
13. `.gitignore` - Update entries

## DO NOT MAINTAIN BACKWARDS COMPATIBILITY

This is developmental software. Remove all support for the old directory structure:
- Delete fallback logic for old paths
- Remove old directory names from .gitignore
- Don't create symlinks to old locations
- Don't provide migration scripts

The new structure is cleaner and self-documenting. Users should simply run `./clean.sh` and start fresh with the new structure.

## Verification

After implementation:
1. Run `./clean.sh` to remove any old outputs
2. Run `./run_all_docker.sh`
3. Verify all outputs appear in `runs/<timestamp>/`
4. Verify `runs/latest` symlink works
5. Run a second time and verify both runs are preserved
6. Test individual benchmark scripts with `--run-dir` argument
