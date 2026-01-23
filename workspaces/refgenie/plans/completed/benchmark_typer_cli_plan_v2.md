# Implementation Plan for Typer CLI Benchmark Interface

## The Issue

The benchmark suite currently has:
- Multiple shell scripts (`run_all_docker.sh`, `build_docker.sh`) for orchestration
- Each Python benchmark module has its own `argparse` CLI in `if __name__ == "__main__"` blocks
- Inconsistent invocation patterns (`python -m benchmarks.X` vs shell scripts)
- Duplicated path logic for `--run-dir` handling across modules

**Goal**: Unified typer CLI (`rsb`) that replaces all the scattered entry points with a single, well-documented interface.

## Files to Read for Context

- `refgetstore_benchmark/benchmarks/deduplication.py` - Example of current argparse pattern
- `refgetstore_benchmark/benchmarks/storage_size.py` - Another benchmark module
- `refgetstore_benchmark/benchmarks/region_extraction.py` - Complex benchmark with many options
- `refgetstore_benchmark/benchmarks/scaling.py` - Simpler benchmark
- `refgetstore_benchmark/benchmarks/export_fasta.py` - Export benchmark
- `refgetstore_benchmark/analysis/figures.py` - Figure generation
- `refgetstore_benchmark/analysis/generate_report.py` - Report generation
- `refgetstore_benchmark/generators/fasta.py` - Test data generation
- `run_all_docker.sh` - Current orchestration script
- `pyproject.toml` - For entry point configuration

## Implementation Steps

### Step 1: Create `refgetstore_benchmark/_run_context.py`

Create a `RunContext` dataclass that centralizes all run directory path logic:
- Properties for `results`, `plots`, `stores`, `data`, `bed_files` subdirectories
- `create()` classmethod for new timestamped runs
- `from_existing()` classmethod for using existing run directories
- Handles directory creation, symlink updates, and config.json writing

### Step 2: Create `refgetstore_benchmark/cli.py`

Create the main typer app with:

**Subcommand group `run`:**
- `rsb run all` - Complete benchmark suite
- `rsb run dedup` - Deduplication benchmark
- `rsb run storage` - Storage size comparison
- `rsb run region` - Region extraction
- `rsb run scaling` - Scaling benchmark
- `rsb run export` - FASTA export benchmark
- `rsb run rsamtools` - R Rsamtools benchmark
- `rsb run biostrings` - R Biostrings benchmark

**Top-level commands:**
- `rsb setup` - Generate test data and BED files
- `rsb figures` - Generate figures from results
- `rsb report` - Generate markdown report
- `rsb clean` - Remove benchmark outputs

**Helper functions:**
- `_get_or_create_context()` - Consistent `--run-dir` handling
- `_run_setup()` - Shared setup logic
- `_run_r_benchmark()` - Wrapper for R script execution

### Step 3: Refactor `deduplication.py`

- Extract core logic into `run(ctx: RunContext, dataset: str) -> dict`
- Remove the `argparse` main block entirely
- Remove `if __name__ == "__main__"` block

### Step 4: Refactor `storage_size.py`

- Extract core logic into `run(ctx: RunContext, fasta: Path | None = None) -> dict`
- Remove the `argparse` main block entirely
- Remove `if __name__ == "__main__"` block

### Step 5: Refactor `region_extraction.py`

- Extract core logic into `run(ctx: RunContext, random: bool, bed: bool, region_size: int, count: int) -> dict`
- Remove the `argparse` main block entirely
- Remove `if __name__ == "__main__"` block

### Step 6: Refactor `scaling.py`

- Extract core logic into `run(ctx: RunContext) -> dict`
- Remove the `argparse` main block entirely
- Remove `if __name__ == "__main__"` block

### Step 7: Refactor `export_fasta.py`

- Extract core logic into `run(ctx: RunContext) -> dict`
- Remove the `argparse` main block entirely
- Remove `if __name__ == "__main__"` block

### Step 8: Refactor `analysis/figures.py`

- Extract core logic into `run(ctx: RunContext)`
- Remove any standalone entry point

### Step 9: Refactor `analysis/generate_report.py`

- Extract core logic into `run(ctx: RunContext)`
- Remove any standalone entry point

### Step 10: Update `pyproject.toml`

Add entry points:
```toml
[project.scripts]
rsb = "refgetstore_benchmark.cli:app"
```

### Step 11: Simplify `run_all_docker.sh`

Replace all the individual `python -m` calls with:
```bash
$DOCKER_RUN rsb run all
```

Keep only the Docker boilerplate (image check, volume mounts, file ownership fix).

### Step 12: Add typer dependency

Add `typer` to `pyproject.toml` dependencies.

## Backwards Compatibility

**Do not maintain backwards compatibility.**

This is developmental software. The old `python -m benchmarks.X` invocation pattern will be removed entirely. All `if __name__ == "__main__"` blocks will be deleted. Users should use the new `rsb` CLI exclusively.

## Cleanup

Once completed, move this plan to `plans/completed/benchmark_typer_cli_plan_v2.md`.
