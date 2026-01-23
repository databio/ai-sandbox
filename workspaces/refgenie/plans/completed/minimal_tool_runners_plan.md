# Plan: Minimal Benchmark Orchestration

## Goal

`region_extraction.py` becomes a thin orchestrator (~50-100 lines). Each tool is a CLI command. The benchmark just loops over tools and times them.

## Target Architecture

```python
# region_extraction.py

TOOLS = [
    {
        "name": "pyfaidx",
        "setup": "python -m tools.pyfaidx_setup --fasta {fasta} --output {index}",
        "run": "python -m tools.pyfaidx_extract --fasta {fasta} --bed {bed}",
    },
    {
        "name": "RefgetStore (Encoded)",
        "setup": "refget store init --path {store} && refget store add {fasta} --path {store} --mode encoded",
        "run": "python -m tools.refgetstore_extract --store {store} --bed {bed}",
    },
    {
        "name": "Rsamtools",
        "setup": "samtools faidx {fasta}",  # or None if no setup needed
        "run": "Rscript tools/rsamtools_extract.R {fasta} {bed}",
    },
    # ...
]

def run(ctx, bed_file):
    results = []

    # Phase 1: Setup data structures
    for tool in TOOLS:
        if tool["setup"]:
            subprocess.run(tool["setup"].format(...))

    # Phase 2: Run benchmarks
    for tool in TOOLS:
        start = time.perf_counter()
        subprocess.run(tool["run"].format(...))
        elapsed = time.perf_counter() - start
        results.append({"tool": tool["name"], "elapsed": elapsed})

    save_results(results)
```

## Context Files to Read

- `refgetstore_benchmark/benchmarks/region_extraction.py` - Current 600-line behemoth

## What's Wrong with Current `region_extraction.py`

It's ~600 lines doing:
- Tool availability checking (move to utils)
- Inline extraction functions for each tool (move to tool scripts)
- Parallel execution logic (unnecessary complexity)
- Multiple benchmark modes (random vs BED - simplify)
- Inline RefgetStore/pyfaidx/seqrepo code (should be CLI)

## Implementation Steps

### Step 1: Create tool runner scripts

Each tool gets a minimal CLI script that:
1. Takes inputs (fasta, bed, store path, etc.)
2. Extracts all regions
3. Exits (timing done by orchestrator)

**`tools/pyfaidx_extract.py` (~15 lines):**
```python
#!/usr/bin/env python3
"""Extract regions using pyfaidx."""
import sys
from pyfaidx import Fasta

fasta_path, bed_path = sys.argv[1], sys.argv[2]
fa = Fasta(fasta_path)

with open(bed_path) as f:
    for line in f:
        chrom, start, end = line.strip().split("\t")[:3]
        _ = str(fa[chrom][int(start):int(end)])
```

**`tools/refgetstore_extract.py` (~20 lines):**
```python
#!/usr/bin/env python3
"""Extract regions using RefgetStore."""
import sys
from gtars.refget import RefgetStore

store_path, bed_path, collection_digest = sys.argv[1], sys.argv[2], sys.argv[3]
store = RefgetStore.load_local(store_path)

with open(bed_path) as f:
    for line in f:
        chrom, start, end = line.strip().split("\t")[:3]
        rec = store.get_sequence_by_collection_and_name(collection_digest, chrom)
        if rec:
            _ = store.get_substring(rec.metadata.sha512t24u, int(start), int(end))
```

**`tools/seqrepo_extract.py` (~15 lines):**
```python
#!/usr/bin/env python3
"""Extract regions using seqrepo."""
import sys
from biocommons.seqrepo import SeqRepo

seqrepo_path, bed_path = sys.argv[1], sys.argv[2]
sr = SeqRepo(seqrepo_path)

with open(bed_path) as f:
    for line in f:
        chrom, start, end = line.strip().split("\t")[:3]
        _ = sr.fetch(chrom, int(start), int(end))
```

**`tools/rsamtools_extract.R` (~15 lines):**
```r
#!/usr/bin/env Rscript
suppressPackageStartupMessages(library(Rsamtools))
args <- commandArgs(trailingOnly = TRUE)
fa <- FaFile(args[1])
open(fa)
regions <- read.table(args[2], sep="\t", col.names=c("chrom","start","end"))
regions$start <- regions$start + 1
for (i in seq_len(nrow(regions))) {
  gr <- GRanges(seqnames=regions$chrom[i], ranges=IRanges(start=regions$start[i], end=regions$end[i]))
  scanFa(fa, gr)
}
close(fa)
```

**`tools/biostrings_extract.R` (~15 lines):**
```r
#!/usr/bin/env Rscript
suppressPackageStartupMessages(library(Biostrings))
args <- commandArgs(trailingOnly = TRUE)
seqs <- readDNAStringSet(args[1])
regions <- read.table(args[2], sep="\t", col.names=c("chrom","start","end"))
regions$start <- regions$start + 1
for (i in seq_len(nrow(regions))) {
  idx <- which(names(seqs) == regions$chrom[i])
  subseq(seqs[[idx]], start=regions$start[i], end=regions$end[i])
}
```

**`tools/samtools_extract.sh` (~5 lines):**
```bash
#!/bin/bash
# Extract regions using samtools faidx
FASTA=$1
BED=$2
while IFS=$'\t' read -r chrom start end _; do
  samtools faidx "$FASTA" "${chrom}:$((start+1))-${end}" > /dev/null
done < "$BED"
```

### Step 2: Rewrite `region_extraction.py` as thin orchestrator

```python
#!/usr/bin/env python3
"""Region extraction benchmark - thin orchestrator."""
import subprocess
import time
from pathlib import Path

TOOLS = [
    {
        "name": "pyfaidx",
        "setup": None,  # pyfaidx indexes on first access
        "run": ["python", "-m", "tools.pyfaidx_extract", "{fasta}", "{bed}"],
        "available": lambda: _check_python("pyfaidx"),
    },
    {
        "name": "RefgetStore (Encoded)",
        "setup": ["refget", "store", "init", "--path", "{store_encoded}"],
        "setup2": ["refget", "store", "add", "{fasta}", "--path", "{store_encoded}", "--mode", "encoded"],
        "run": ["python", "-m", "tools.refgetstore_extract", "{store_encoded}", "{bed}", "{digest_encoded}"],
        "available": lambda: _check_python("gtars"),
    },
    {
        "name": "RefgetStore (Raw)",
        "setup": ["refget", "store", "init", "--path", "{store_raw}"],
        "setup2": ["refget", "store", "add", "{fasta}", "--path", "{store_raw}", "--mode", "raw"],
        "run": ["python", "-m", "tools.refgetstore_extract", "{store_raw}", "{bed}", "{digest_raw}"],
        "available": lambda: _check_python("gtars"),
    },
    {
        "name": "seqrepo",
        "setup": ["python", "-m", "tools.seqrepo_setup", "{fasta}", "{seqrepo_path}"],
        "run": ["python", "-m", "tools.seqrepo_extract", "{seqrepo_path}", "{bed}"],
        "available": lambda: _check_python("biocommons.seqrepo"),
    },
    {
        "name": "samtools",
        "setup": ["samtools", "faidx", "{fasta}"],
        "run": ["bash", "tools/samtools_extract.sh", "{fasta}", "{bed}"],
        "available": lambda: _check_cli("samtools"),
    },
    {
        "name": "Rsamtools",
        "setup": ["samtools", "faidx", "{fasta}"],  # needs .fai
        "run": ["Rscript", "tools/rsamtools_extract.R", "{fasta}", "{bed}"],
        "available": lambda: _check_r("Rsamtools"),
    },
    {
        "name": "Biostrings",
        "setup": None,  # loads FASTA into memory
        "run": ["Rscript", "tools/biostrings_extract.R", "{fasta}", "{bed}"],
        "available": lambda: _check_r("Biostrings"),
    },
]


def run(ctx, bed_file: Path):
    """Run region extraction benchmark."""
    fasta = ctx.data / "baseline" / "genome_ucsc.fa"

    # Build paths dict for formatting
    paths = {
        "fasta": str(fasta),
        "bed": str(bed_file),
        "store_encoded": str(ctx.stores / "encoded"),
        "store_raw": str(ctx.stores / "raw"),
        "seqrepo_path": str(ctx.stores / "seqrepo"),
        # digests filled in during setup
    }

    # Filter to available tools
    tools = [t for t in TOOLS if t["available"]()]
    print(f"Available tools: {[t['name'] for t in tools]}")

    # Phase 1: Setup
    print("\n=== Setup ===")
    for tool in tools:
        if tool.get("setup"):
            cmd = [arg.format(**paths) for arg in tool["setup"]]
            print(f"  {tool['name']}: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True)
            # Capture digest if RefgetStore
            if "store_add" in str(cmd):
                # parse digest from output...
                pass
        if tool.get("setup2"):
            cmd = [arg.format(**paths) for arg in tool["setup2"]]
            subprocess.run(cmd, capture_output=True)

    # Phase 2: Benchmark
    print("\n=== Benchmark ===")
    results = []
    for tool in tools:
        cmd = [arg.format(**paths) for arg in tool["run"]]

        start = time.perf_counter()
        subprocess.run(cmd, capture_output=True)
        elapsed = time.perf_counter() - start

        print(f"  {tool['name']}: {elapsed:.3f}s")
        results.append({
            "tool": tool["name"],
            "total_seconds": elapsed,
            "bed_file": bed_file.name,
        })

    return results
```

### Step 3: Delete bloated code from current `region_extraction.py`

Remove:
- `extract_with_refgetstore()` (~20 lines)
- `extract_with_pyfaidx()` (~10 lines)
- `extract_with_seqrepo()` (~10 lines)
- `extract_with_samtools_batch()` (~35 lines)
- `extract_with_bedtools()` (~30 lines)
- `benchmark_regions()` (~100 lines)
- `setup_tools()` (~25 lines)
- `run_random_benchmark()` (~60 lines)
- `run_bed_benchmark()` (~50 lines)
- Parallel execution logic
- ThreadPoolExecutor usage

### Step 4: Update CLI

The `run region` command becomes simpler:

```python
@run_app.command("region")
def run_region(
    run_dir: Optional[Path] = typer.Option(None, "--run-dir"),
    bed: str = typer.Option("regions_10k_1kb.bed", "--bed", help="BED file to use"),
):
    """Benchmark region extraction across all tools."""
    ctx = _get_or_create_context(run_dir)
    bed_file = ctx.bed_files / bed

    if not bed_file.exists():
        typer.echo(f"BED file not found: {bed_file}")
        typer.echo("Run './run_benchmark.py setup' first.")
        raise typer.Exit(1)

    from .benchmarks import region_extraction
    results = region_extraction.run(ctx, bed_file)
    save_results(results, ctx.results / "region_extraction.csv")
```

## File Changes Summary

| File | Action |
|------|--------|
| `tools/pyfaidx_extract.py` | CREATE (~15 lines) |
| `tools/refgetstore_extract.py` | CREATE (~20 lines) |
| `tools/seqrepo_extract.py` | CREATE (~15 lines) |
| `tools/seqrepo_setup.py` | CREATE (~15 lines) |
| `tools/samtools_extract.sh` | CREATE (~5 lines) |
| `tools/rsamtools_extract.R` | CREATE (~15 lines) |
| `tools/biostrings_extract.R` | CREATE (~15 lines) |
| `benchmarks/region_extraction.py` | REWRITE (600 → ~80 lines) |
| `benchmarks/rsamtools_benchmark.R` | DELETE (~225 lines) |
| `benchmarks/biostrings_benchmark.R` | DELETE (~220 lines) |
| `cli.py` | EDIT - Simplify `run region`, remove R-specific commands |

## Before/After Line Counts

| Component | Before | After |
|-----------|--------|-------|
| `region_extraction.py` | ~600 | ~80 |
| `rsamtools_benchmark.R` | ~225 | 0 (deleted) |
| `biostrings_benchmark.R` | ~220 | 0 (deleted) |
| Tool scripts | 0 | ~100 (7 small scripts) |
| **Total** | **~1045** | **~180** |

## Key Simplifications

1. **No inline extraction code** - all tools are CLI commands
2. **No parallel execution** - just sequential timing (simpler, more predictable)
3. **No multiple benchmark modes** - just takes a BED file
4. **No ThreadPoolExecutor** - unnecessary complexity
5. **Tools list is data** - easy to add/remove tools

## DO NOT MAINTAIN BACKWARDS COMPATIBILITY

Delete all the old code. No `--legacy` mode.
