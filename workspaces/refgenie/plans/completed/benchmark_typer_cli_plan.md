# Typer CLI for RefgetStore Benchmarks

## Goal

Create a unified CLI using typer that:
- Runs individual benchmarks or all benchmarks
- Works both locally and in Docker
- Has clear, helpful documentation built into `--help`
- Keeps code DRY by extracting common patterns

## Architecture

```
refgetstore_benchmark/
├── cli.py              # Main typer app with all commands
├── _run_context.py     # Shared RunContext class for directory setup
├── benchmarks/
│   ├── deduplication.py   # Keep benchmark logic, remove argparse main()
│   ├── storage_size.py
│   ├── region_extraction.py
│   ├── scaling.py
│   ├── export_fasta.py
│   └── *.R                # R scripts (invoked via subprocess)
```

## CLI Structure

```
rsb                           # Short alias for refgetstore-benchmark
rsb --help                    # Show all commands
rsb run --help                # Show benchmark commands

rsb run all                   # Run complete suite (phases 1-4)
rsb run dedup                 # Deduplication benchmark
rsb run storage               # Storage size comparison
rsb run region                # Region extraction
rsb run scaling               # Scaling benchmark
rsb run export                # Export FASTA benchmark
rsb run rsamtools             # Rsamtools (R)
rsb run biostrings            # Biostrings (R)

rsb setup                     # Generate test data + BED files
rsb figures                   # Generate figures from results
rsb report                    # Generate report from results
rsb clean                     # Remove runs/ directory
```

## Implementation Plan

### 1. Create `_run_context.py` - Shared run directory logic

```python
"""Shared context for benchmark runs."""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json

@dataclass
class RunContext:
    """Manages paths for a benchmark run."""
    run_dir: Path

    @property
    def results(self) -> Path:
        return self.run_dir / "results"

    @property
    def plots(self) -> Path:
        return self.run_dir / "plots"

    @property
    def stores(self) -> Path:
        return self.run_dir / "stores"

    @property
    def data(self) -> Path:
        return self.run_dir / "data"

    @property
    def bed_files(self) -> Path:
        return self.run_dir / "bed_files"

    @classmethod
    def create(cls, base: Path = Path("runs")) -> "RunContext":
        """Create a new timestamped run directory."""
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        run_dir = base / timestamp
        ctx = cls(run_dir)
        ctx._init_dirs()
        ctx._update_latest_symlink(base)
        ctx._save_config()
        return ctx

    @classmethod
    def from_existing(cls, run_dir: Path) -> "RunContext":
        """Use an existing run directory."""
        ctx = cls(Path(run_dir))
        ctx._init_dirs()
        return ctx

    def _init_dirs(self):
        for d in [self.results, self.plots, self.stores, self.data, self.bed_files]:
            d.mkdir(parents=True, exist_ok=True)

    def _update_latest_symlink(self, base: Path):
        latest = base / "latest"
        latest.unlink(missing_ok=True)
        latest.symlink_to(self.run_dir.name)

    def _save_config(self):
        import subprocess
        config = {
            "timestamp": self.run_dir.name,
            "hostname": subprocess.getoutput("hostname"),
            "git_commit": subprocess.getoutput("git rev-parse HEAD 2>/dev/null || echo unknown"),
        }
        (self.run_dir / "config.json").write_text(json.dumps(config, indent=2))
```

### 2. Refactor benchmark modules

Each benchmark module gets a simple function interface (no argparse):

```python
# benchmarks/deduplication.py
def run(ctx: RunContext, dataset: str = "naming_variants") -> dict:
    """Run deduplication benchmark. Returns summary dict."""
    ...

# benchmarks/storage_size.py
def run(ctx: RunContext, fasta: Path | None = None) -> dict:
    """Run storage size benchmark."""
    ...

# benchmarks/region_extraction.py
def run(ctx: RunContext, random: bool = True, bed: bool = False,
        region_size: int = 1000, count: int = 1000) -> dict:
    """Run region extraction benchmark."""
    ...
```

Keep the existing `if __name__ == "__main__"` blocks for backwards compatibility, but they just parse args and call `run()`.

### 3. Create `cli.py` - Main typer app

```python
#!/usr/bin/env python3
"""RefgetStore Benchmark CLI."""
import typer
from pathlib import Path
from typing import Optional

from ._run_context import RunContext

app = typer.Typer(
    name="rsb",
    help="RefgetStore Benchmark Suite - Compare sequence storage formats.",
    no_args_is_help=True,
)
run_app = typer.Typer(help="Run benchmarks.")
app.add_typer(run_app, name="run")


# Common options as a callback
def resolve_context(
    run_dir: Optional[Path] = typer.Option(
        None, "--run-dir", "-r",
        help="Use existing run directory. Creates new timestamped dir if not specified."
    ),
    new: bool = typer.Option(
        False, "--new", "-n",
        help="Force create new run directory even if --run-dir specified."
    ),
) -> RunContext:
    """Resolve or create run context."""
    if run_dir and not new:
        return RunContext.from_existing(run_dir)
    return RunContext.create()


@run_app.command("all")
def run_all(
    run_dir: Optional[Path] = typer.Option(None, "--run-dir", "-r"),
    skip_r: bool = typer.Option(False, "--skip-r", help="Skip R benchmarks"),
):
    """Run complete benchmark suite (setup + all benchmarks + figures + report)."""
    ctx = RunContext.create() if not run_dir else RunContext.from_existing(run_dir)

    typer.echo(f"Run directory: {ctx.run_dir}")

    # Phase 1: Setup
    _run_setup(ctx)

    # Phase 2: Core benchmarks
    from .benchmarks import deduplication, storage_size, region_extraction
    deduplication.run(ctx, dataset="naming_variants")
    storage_size.run(ctx)
    region_extraction.run(ctx, random=True, bed=True)

    if not skip_r:
        _run_r_benchmark(ctx, "rsamtools")
        _run_r_benchmark(ctx, "biostrings")

    # Phase 3: Additional benchmarks
    from .benchmarks import export_fasta, scaling
    export_fasta.run(ctx)
    scaling.run(ctx)

    # Phase 4: Analysis
    from .analysis import figures, generate_report
    figures.run(ctx)
    generate_report.run(ctx)

    typer.echo(f"\nComplete! Results in: {ctx.run_dir}")


@run_app.command("dedup")
def run_dedup(
    run_dir: Optional[Path] = typer.Option(None, "--run-dir", "-r"),
    dataset: str = typer.Option(
        "naming_variants", "--dataset", "-d",
        help="Dataset: naming_variants (demos dedup) or pangenome (control)"
    ),
):
    """Benchmark sequence deduplication across genome naming variants."""
    ctx = _get_or_create_context(run_dir)
    from .benchmarks import deduplication
    deduplication.run(ctx, dataset=dataset)


@run_app.command("storage")
def run_storage(
    run_dir: Optional[Path] = typer.Option(None, "--run-dir", "-r"),
    fasta: Optional[Path] = typer.Option(None, "--fasta", "-f", help="Custom FASTA file"),
):
    """Compare storage sizes: FASTA, gzip, bgzip, 2bit, RefgetStore, seqrepo."""
    ctx = _get_or_create_context(run_dir)
    from .benchmarks import storage_size
    storage_size.run(ctx, fasta=fasta)


@run_app.command("region")
def run_region(
    run_dir: Optional[Path] = typer.Option(None, "--run-dir", "-r"),
    random: bool = typer.Option(True, "--random/--no-random", help="Test random regions"),
    bed: bool = typer.Option(False, "--bed/--no-bed", help="Test BED file regions"),
    region_size: int = typer.Option(1000, "--region-size", "-s"),
    count: int = typer.Option(1000, "--count", "-c", help="Number of random regions"),
):
    """Benchmark region extraction: RefgetStore vs pyfaidx vs seqrepo vs samtools."""
    ctx = _get_or_create_context(run_dir)
    from .benchmarks import region_extraction
    region_extraction.run(ctx, random=random, bed=bed, region_size=region_size, count=count)


@run_app.command("scaling")
def run_scaling(run_dir: Optional[Path] = typer.Option(None, "--run-dir", "-r")):
    """Benchmark scaling with genome size."""
    ctx = _get_or_create_context(run_dir)
    from .benchmarks import scaling
    scaling.run(ctx)


@run_app.command("export")
def run_export(run_dir: Optional[Path] = typer.Option(None, "--run-dir", "-r")):
    """Benchmark FASTA export from RefgetStore."""
    ctx = _get_or_create_context(run_dir)
    from .benchmarks import export_fasta
    export_fasta.run(ctx)


@run_app.command("rsamtools")
def run_rsamtools(run_dir: Optional[Path] = typer.Option(None, "--run-dir", "-r")):
    """Benchmark Bioconductor Rsamtools region extraction."""
    ctx = _get_or_create_context(run_dir)
    _run_r_benchmark(ctx, "rsamtools")


@run_app.command("biostrings")
def run_biostrings(run_dir: Optional[Path] = typer.Option(None, "--run-dir", "-r")):
    """Benchmark Bioconductor Biostrings region extraction."""
    ctx = _get_or_create_context(run_dir)
    _run_r_benchmark(ctx, "biostrings")


# Top-level commands

@app.command()
def setup(run_dir: Optional[Path] = typer.Option(None, "--run-dir", "-r")):
    """Generate test FASTA files and synthetic BED files."""
    ctx = _get_or_create_context(run_dir)
    _run_setup(ctx)
    typer.echo(f"Test data ready in: {ctx.data}")


@app.command()
def figures(run_dir: Path = typer.Option("runs/latest", "--run-dir", "-r")):
    """Generate figures from benchmark results."""
    ctx = RunContext.from_existing(run_dir)
    from .analysis import figures as fig_module
    fig_module.run(ctx)


@app.command()
def report(run_dir: Path = typer.Option("runs/latest", "--run-dir", "-r")):
    """Generate markdown report from benchmark results."""
    ctx = RunContext.from_existing(run_dir)
    from .analysis import generate_report
    generate_report.run(ctx)


@app.command()
def clean(
    all_runs: bool = typer.Option(False, "--all", "-a", help="Remove all runs/"),
    keep_latest: bool = typer.Option(False, "--keep-latest", "-k", help="Keep latest run"),
):
    """Remove benchmark output directories."""
    import shutil
    runs_dir = Path("runs")
    if not runs_dir.exists():
        typer.echo("Nothing to clean.")
        return

    if all_runs and not keep_latest:
        shutil.rmtree(runs_dir)
        typer.echo("Removed runs/")
    elif keep_latest:
        latest = (runs_dir / "latest").resolve()
        for d in runs_dir.iterdir():
            if d.is_dir() and d.resolve() != latest:
                shutil.rmtree(d)
        typer.echo(f"Cleaned old runs, kept: {latest.name}")
    else:
        typer.echo("Use --all to remove all runs, or --keep-latest to clean old runs only.")


# Helper functions

def _get_or_create_context(run_dir: Optional[Path]) -> RunContext:
    if run_dir:
        return RunContext.from_existing(run_dir)
    return RunContext.create()


def _run_setup(ctx: RunContext):
    """Generate test data."""
    from .generators import fasta as fasta_gen
    fasta_gen.generate_all(ctx.data)

    # Generate BED files
    from .utils import generate_synthetic_bed
    from pyfaidx import Fasta
    import random
    random.seed(42)

    fa = Fasta(str(ctx.data / "baseline" / "genome_ucsc.fa"))
    chrom_sizes = {name: len(fa[name]) for name in fa.keys()}
    fa.close()

    configs = [
        ("sparse_100bp", 100, 100),
        ("sparse_10kb", 100, 10000),
        ("medium_100bp", 10000, 100),
        ("medium_1kb", 10000, 1000),
        ("dense_10kb", 10000, 10000),
    ]
    for name, n_regions, size in configs:
        generate_synthetic_bed(chrom_sizes, n_regions, size, ctx.bed_files / f"{name}.bed")


def _run_r_benchmark(ctx: RunContext, name: str):
    """Run an R benchmark script."""
    import subprocess
    script = Path(__file__).parent / "benchmarks" / f"{name}_benchmark.R"
    subprocess.run(["Rscript", str(script), "--run-dir", str(ctx.run_dir)], check=True)


if __name__ == "__main__":
    app()
```

### 4. Update `pyproject.toml` entry point

```toml
[project.scripts]
rsb = "refgetstore_benchmark.cli:app"
refgetstore-benchmark = "refgetstore_benchmark.cli:app"
```

### 5. Update `run_all_docker.sh` to use new CLI

```bash
# Replace all the individual python -m calls with:
$DOCKER_RUN rsb run all
```

Or keep the shell script for the Docker boilerplate and call the Python CLI inside.

## Files to Modify

1. **Create**: `refgetstore_benchmark/_run_context.py`
2. **Create**: `refgetstore_benchmark/cli.py`
3. **Modify**: `refgetstore_benchmark/benchmarks/deduplication.py` - Extract `run()` function
4. **Modify**: `refgetstore_benchmark/benchmarks/storage_size.py` - Extract `run()` function
5. **Modify**: `refgetstore_benchmark/benchmarks/region_extraction.py` - Extract `run()` function
6. **Modify**: `refgetstore_benchmark/benchmarks/scaling.py` - Extract `run()` function
7. **Modify**: `refgetstore_benchmark/benchmarks/export_fasta.py` - Extract `run()` function
8. **Modify**: `refgetstore_benchmark/analysis/figures.py` - Extract `run()` function
9. **Modify**: `refgetstore_benchmark/analysis/generate_report.py` - Extract `run()` function
10. **Modify**: `pyproject.toml` - Add entry points
11. **Simplify**: `run_all_docker.sh` - Use `rsb run all`

## DRY Principles Applied

1. **RunContext** - Single class manages all path logic, no more `--run-dir` path assembly everywhere
2. **Common options** - `--run-dir` handled consistently via `_get_or_create_context()`
3. **R benchmark wrapper** - Single `_run_r_benchmark()` function for both R scripts
4. **Setup logic** - Single `_run_setup()` used by both `setup` command and `run all`

## Example Usage After Implementation

```bash
# Quick single benchmark
rsb run dedup

# Full suite
rsb run all

# Custom run directory
rsb run region --run-dir runs/my-test --bed --random

# Generate report from existing run
rsb report --run-dir runs/2026-01-18-143022

# Clean up
rsb clean --all
```
