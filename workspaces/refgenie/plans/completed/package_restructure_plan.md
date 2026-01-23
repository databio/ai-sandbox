# Package Restructure Plan: refgetstore-benchmark

## Overview

This plan restructures the refgetstore-benchmark project from a flat script-based layout into a proper Python package with `src/` layout. This enables proper imports, testability, and distribution.

**IMPORTANT: DO NOT MAINTAIN BACKWARDS COMPATIBILITY.** This is developmental software. Old import paths, CLI patterns, and directory structures should be replaced, not preserved. The goal is a clean new structure, not a migration path from the old one.

## Current Structure

```
refgetstore-benchmark/
├── analysis/
│   ├── __init__.py
│   ├── figures.py
│   ├── generate_report.py
│   └── report_templates.py
├── bed_files/
│   ├── generate_synthetic.py
│   └── synthetic/           # Generated BED files (gitignored)
├── benchmarks/
│   ├── __init__.py
│   ├── utils.py
│   ├── deduplication.py
│   ├── storage_size.py
│   ├── region_extraction.py
│   ├── export_fasta.py
│   ├── scaling.py
│   ├── verify_setup.py
│   ├── rsamtools_benchmark.R
│   └── biostrings_benchmark.R
├── data/
│   └── generate_test_data.py
├── runs/                    # Outputs (gitignored)
├── run_all_docker.sh
├── run_docker.sh
├── clean.sh
├── pyproject.toml
├── Dockerfile
└── README.md
```

## Target Structure

```
refgetstore-benchmark/
├── src/
│   └── refgetstore_benchmark/
│       ├── __init__.py
│       ├── utils.py                    # Shared utilities (from benchmarks/utils.py)
│       ├── generators/
│       │   ├── __init__.py
│       │   ├── fasta.py                # from data/generate_test_data.py
│       │   └── bed.py                  # from bed_files/generate_synthetic.py
│       ├── benchmarks/
│       │   ├── __init__.py
│       │   ├── deduplication.py
│       │   ├── storage_size.py
│       │   ├── region_extraction.py
│       │   ├── export_fasta.py
│       │   ├── scaling.py
│       │   ├── verify_setup.py
│       │   ├── rsamtools_benchmark.R
│       │   └── biostrings_benchmark.R
│       └── analysis/
│           ├── __init__.py
│           ├── figures.py
│           ├── generate_report.py
│           └── report_templates.py
├── runs/                    # Outputs (gitignored)
├── run_all_docker.sh
├── run_docker.sh
├── clean.sh
├── pyproject.toml
├── Dockerfile
└── README.md
```

---

## Step 1: Create Directory Structure

Create the new `src/refgetstore_benchmark/` directory hierarchy:

```bash
mkdir -p src/refgetstore_benchmark/generators
mkdir -p src/refgetstore_benchmark/benchmarks
mkdir -p src/refgetstore_benchmark/analysis
```

---

## Step 2: File Moves

### 2.1 Move utils.py to package root

| Old Path | New Path |
|----------|----------|
| `benchmarks/utils.py` | `src/refgetstore_benchmark/utils.py` |

### 2.2 Move benchmark modules

| Old Path | New Path |
|----------|----------|
| `benchmarks/deduplication.py` | `src/refgetstore_benchmark/benchmarks/deduplication.py` |
| `benchmarks/storage_size.py` | `src/refgetstore_benchmark/benchmarks/storage_size.py` |
| `benchmarks/region_extraction.py` | `src/refgetstore_benchmark/benchmarks/region_extraction.py` |
| `benchmarks/export_fasta.py` | `src/refgetstore_benchmark/benchmarks/export_fasta.py` |
| `benchmarks/scaling.py` | `src/refgetstore_benchmark/benchmarks/scaling.py` |
| `benchmarks/verify_setup.py` | `src/refgetstore_benchmark/benchmarks/verify_setup.py` |
| `benchmarks/rsamtools_benchmark.R` | `src/refgetstore_benchmark/benchmarks/rsamtools_benchmark.R` |
| `benchmarks/biostrings_benchmark.R` | `src/refgetstore_benchmark/benchmarks/biostrings_benchmark.R` |

### 2.3 Move analysis modules

| Old Path | New Path |
|----------|----------|
| `analysis/figures.py` | `src/refgetstore_benchmark/analysis/figures.py` |
| `analysis/generate_report.py` | `src/refgetstore_benchmark/analysis/generate_report.py` |
| `analysis/report_templates.py` | `src/refgetstore_benchmark/analysis/report_templates.py` |

### 2.4 Move generator modules

| Old Path | New Path |
|----------|----------|
| `data/generate_test_data.py` | `src/refgetstore_benchmark/generators/fasta.py` |
| `bed_files/generate_synthetic.py` | `src/refgetstore_benchmark/generators/bed.py` |

### 2.5 Delete old directories

After moving all files, delete:
- `benchmarks/` (entire directory)
- `analysis/` (entire directory)
- `data/generate_test_data.py` (keep `data/` for output if needed)
- `bed_files/generate_synthetic.py` (keep `bed_files/` for output)

---

## Step 3: Import Statement Updates

### 3.1 Package root `__init__.py`

**New file: `src/refgetstore_benchmark/__init__.py`**

```python
"""RefgetStore Benchmarking Suite.

A comprehensive benchmarking toolkit for comparing RefgetStore against
traditional sequence storage formats.
"""

__version__ = "0.1.0"

from .utils import (
    BenchmarkResult,
    Tools,
    benchmark_function,
    create_bgzipped_fasta,
    create_refgetstore_variants,
    create_seqrepo,
    create_single_refgetstore,
    format_bytes,
    format_time,
    get_directory_size,
    load_bed,
    print_header,
    save_results,
    RunDirectory,
)
```

### 3.2 Generators `__init__.py`

**New file: `src/refgetstore_benchmark/generators/__init__.py`**

```python
"""Data generators for benchmarks."""

from .fasta import main as generate_fasta
from .bed import main as generate_bed

__all__ = ["generate_fasta", "generate_bed"]
```

### 3.3 Benchmarks `__init__.py`

**New file: `src/refgetstore_benchmark/benchmarks/__init__.py`**

```python
"""RefgetStore Benchmarking Suite."""

from ..utils import (
    BenchmarkResult,
    benchmark_function,
    get_directory_size,
    load_bed,
    save_results,
)

__all__ = [
    "BenchmarkResult",
    "benchmark_function",
    "get_directory_size",
    "load_bed",
    "save_results",
]
```

### 3.4 Analysis `__init__.py`

**New file: `src/refgetstore_benchmark/analysis/__init__.py`**

```python
"""Analysis module for RefgetStore benchmarks.

Contains:
- figures.py: Generate publication figures from CSV results
- generate_report.py: Generate narrative benchmark report
- report_templates.py: Text templates for report sections
"""
```

### 3.5 utils.py updates

**File: `src/refgetstore_benchmark/utils.py`**

No changes needed to the content - the file already uses standard library and third-party imports only.

### 3.6 Benchmark module import updates

**All benchmark modules need their relative imports updated from:**

```python
from .utils import (...)
```

**To:**

```python
from ..utils import (...)
```

**Files requiring this change:**
- `src/refgetstore_benchmark/benchmarks/deduplication.py`
- `src/refgetstore_benchmark/benchmarks/storage_size.py`
- `src/refgetstore_benchmark/benchmarks/region_extraction.py`
- `src/refgetstore_benchmark/benchmarks/export_fasta.py`
- `src/refgetstore_benchmark/benchmarks/scaling.py`

**`verify_setup.py`** has no internal imports to update.

**`storage_size.py`** - also has local gtars/seqrepo imports that should use the centralized `Tools` class:

Replace:
```python
# Try to import gtars
try:
    from gtars.refget import RefgetStore
    GTARS_AVAILABLE = True
except ImportError:
    GTARS_AVAILABLE = False
    print("WARNING: gtars not available. Will skip RefgetStore measurement.")

# Try to import seqrepo
try:
    from biocommons.seqrepo import SeqRepo
    SEQREPO_AVAILABLE = True
except ImportError:
    SEQREPO_AVAILABLE = False
    print("WARNING: seqrepo not available. Will skip seqrepo measurement.")
```

With:
```python
from ..utils import Tools
```

Then use `Tools.gtars`, `Tools.RefgetStore`, `Tools.seqrepo`, `Tools.SeqRepo` throughout.

### 3.7 Analysis module import updates

**File: `src/refgetstore_benchmark/analysis/generate_report.py`**

Update:
```python
from .report_templates import (...)
```

No change needed - this is already correct relative import within the analysis subpackage.

### 3.8 Generator module updates

**File: `src/refgetstore_benchmark/generators/fasta.py`** (was `data/generate_test_data.py`)

No internal imports to update. May want to add:
```python
from ..utils import print_header  # Optional, for consistency
```

**File: `src/refgetstore_benchmark/generators/bed.py`** (was `bed_files/generate_synthetic.py`)

Add imports if using shared utilities:
```python
from ..utils import generate_synthetic_bed  # If moving this function to utils
```

Actually, `bed_files/generate_synthetic.py` is standalone. Consider whether to:
1. Keep it standalone (current approach)
2. Move `generate_synthetic_bed()` from `utils.py` into `generators/bed.py` and export it

**Recommendation:** Keep `generate_synthetic_bed()` in utils.py since it's used by `run_all_docker.sh` inline.

---

## Step 4: pyproject.toml Updates

**Current content (relevant sections):**

```toml
[project]
name = "refgetstore-benchmark"
version = "0.1.0"

[tool.setuptools.packages.find]
include = ["benchmarks*", "analysis*"]
```

**Updated content:**

```toml
[project]
name = "refgetstore-benchmark"
version = "0.1.0"
description = "Benchmarking RefgetStore against traditional FASTA storage methods"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Nathan Sheffield"}
]

dependencies = [
    # RefgetStore (via gtars)
    "gtars",
    # Comparison tools
    "pyfaidx>=0.8.0",
    "biopython>=1.80",
    # Data handling
    "pandas>=2.0",
    "numpy>=1.24",
    # Plotting
    "matplotlib>=3.7",
    "seaborn>=0.12",
    # Config and utilities
    "pyyaml>=6.0",
    "tqdm>=4.65",
    "psutil>=5.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "black",
    "ruff",
]

[project.scripts]
refgetstore-benchmark = "refgetstore_benchmark.cli:main"
generate-fasta = "refgetstore_benchmark.generators.fasta:main"
generate-bed = "refgetstore_benchmark.generators.bed:main"
benchmark-deduplication = "refgetstore_benchmark.benchmarks.deduplication:main"
benchmark-storage = "refgetstore_benchmark.benchmarks.storage_size:main"
benchmark-regions = "refgetstore_benchmark.benchmarks.region_extraction:main"
benchmark-export = "refgetstore_benchmark.benchmarks.export_fasta:main"
benchmark-scaling = "refgetstore_benchmark.benchmarks.scaling:main"
benchmark-figures = "refgetstore_benchmark.analysis.figures:main"
benchmark-report = "refgetstore_benchmark.analysis.generate_report:main"

[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
include = ["refgetstore_benchmark*"]

[tool.black]
line-length = 100
target-version = ["py310", "py311"]

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "W"]
ignore = ["E501"]
```

---

## Step 5: run_all_docker.sh Updates

The script currently uses `-m` module execution syntax. Update all Python invocations:

### Old patterns:

```bash
python data/generate_test_data.py --output-dir $RUN_DIR/data
python -m benchmarks.deduplication --dataset naming_variants --run-dir $RUN_DIR
python -m benchmarks.storage_size --run-dir $RUN_DIR
python -m benchmarks.region_extraction --random --bed --region-size 1000 --run-dir $RUN_DIR
python -m benchmarks.export_fasta --run-dir $RUN_DIR
python -m benchmarks.scaling --run-dir $RUN_DIR
python -m analysis.figures --run-dir $RUN_DIR
python -m analysis.generate_report --run-dir $RUN_DIR
```

### New patterns:

```bash
python -m refgetstore_benchmark.generators.fasta --output-dir $RUN_DIR/data
python -m refgetstore_benchmark.benchmarks.deduplication --dataset naming_variants --run-dir $RUN_DIR
python -m refgetstore_benchmark.benchmarks.storage_size --run-dir $RUN_DIR
python -m refgetstore_benchmark.benchmarks.region_extraction --random --bed --region-size 1000 --run-dir $RUN_DIR
python -m refgetstore_benchmark.benchmarks.export_fasta --run-dir $RUN_DIR
python -m refgetstore_benchmark.benchmarks.scaling --run-dir $RUN_DIR
python -m refgetstore_benchmark.analysis.figures --run-dir $RUN_DIR
python -m refgetstore_benchmark.analysis.generate_report --run-dir $RUN_DIR
```

### Inline BED generation update:

Change:
```bash
from benchmarks.utils import generate_synthetic_bed
```

To:
```bash
from refgetstore_benchmark.utils import generate_synthetic_bed
```

### Full sed replacements for run_all_docker.sh:

```bash
# Replace module paths
sed -i 's/python data\/generate_test_data.py/python -m refgetstore_benchmark.generators.fasta/g' run_all_docker.sh
sed -i 's/python -m benchmarks\./python -m refgetstore_benchmark.benchmarks./g' run_all_docker.sh
sed -i 's/python -m analysis\./python -m refgetstore_benchmark.analysis./g' run_all_docker.sh
sed -i 's/from benchmarks\.utils/from refgetstore_benchmark.utils/g' run_all_docker.sh
```

---

## Step 6: README.md Updates

Update all command examples to use new module paths:

### Old:

```bash
python -m benchmarks.deduplication --run-dir $RUN_DIR --dataset naming_variants
python -m benchmarks.storage_size --run-dir $RUN_DIR
python -m benchmarks.region_extraction --run-dir $RUN_DIR
python -m analysis.figures --run-dir $RUN_DIR
python -m analysis.generate_report --run-dir $RUN_DIR
python data/generate_test_data.py --output-dir runs/latest/data
```

### New:

```bash
python -m refgetstore_benchmark.benchmarks.deduplication --run-dir $RUN_DIR --dataset naming_variants
python -m refgetstore_benchmark.benchmarks.storage_size --run-dir $RUN_DIR
python -m refgetstore_benchmark.benchmarks.region_extraction --run-dir $RUN_DIR
python -m refgetstore_benchmark.analysis.figures --run-dir $RUN_DIR
python -m refgetstore_benchmark.analysis.generate_report --run-dir $RUN_DIR
python -m refgetstore_benchmark.generators.fasta --output-dir runs/latest/data
```

Or with entry points (after `pip install -e .`):

```bash
benchmark-deduplication --run-dir $RUN_DIR --dataset naming_variants
benchmark-storage --run-dir $RUN_DIR
benchmark-regions --run-dir $RUN_DIR
benchmark-figures --run-dir $RUN_DIR
benchmark-report --run-dir $RUN_DIR
generate-fasta --output-dir runs/latest/data
generate-bed --fasta runs/latest/data/baseline/genome_ucsc.fa
```

Update project structure section:

### Old:

```
refgetstore-benchmark/
├── run_all_docker.sh
├── benchmarks/
│   ├── deduplication.py
│   ├── storage_size.py
│   ├── region_extraction.py
│   ├── export_fasta.py
│   ├── scaling.py
│   └── utils.py
├── analysis/
│   ├── figures.py
│   └── generate_report.py
├── data/
│   └── generate_test_data.py
└── runs/
```

### New:

```
refgetstore-benchmark/
├── run_all_docker.sh
├── src/
│   └── refgetstore_benchmark/
│       ├── __init__.py
│       ├── utils.py
│       ├── generators/
│       │   ├── fasta.py      # Test data generation
│       │   └── bed.py        # Synthetic BED generation
│       ├── benchmarks/
│       │   ├── deduplication.py
│       │   ├── storage_size.py
│       │   ├── region_extraction.py
│       │   ├── export_fasta.py
│       │   ├── scaling.py
│       │   └── verify_setup.py
│       └── analysis/
│           ├── figures.py
│           └── generate_report.py
└── runs/
```

---

## Step 7: Dockerfile Updates

The Dockerfile may need updates if it copies specific paths. Check for:

```dockerfile
COPY benchmarks/ /app/benchmarks/
COPY analysis/ /app/analysis/
```

Update to:

```dockerfile
COPY src/ /app/src/
COPY pyproject.toml /app/
```

And ensure `pip install -e .` or `pip install .` is run to install the package.

---

## Step 8: Verify R Scripts Still Work

The R scripts (`rsamtools_benchmark.R`, `biostrings_benchmark.R`) are moved but their invocation from shell scripts needs updating.

In `run_all_docker.sh`, the R scripts are called as:

```bash
Rscript benchmarks/rsamtools_benchmark.R $RUN_DIR
Rscript benchmarks/biostrings_benchmark.R $RUN_DIR
```

Update to:

```bash
Rscript src/refgetstore_benchmark/benchmarks/rsamtools_benchmark.R $RUN_DIR
Rscript src/refgetstore_benchmark/benchmarks/biostrings_benchmark.R $RUN_DIR
```

---

## Migration Strategy

Since this is developmental software with no backwards compatibility requirement:

1. **Create new structure in one commit**
   - Create all `src/refgetstore_benchmark/` directories
   - Move files to new locations
   - Update all imports
   - Update pyproject.toml
   - Update shell scripts
   - Update README

2. **Delete old directories in the same commit**
   - Remove `benchmarks/`
   - Remove `analysis/`
   - Remove `data/generate_test_data.py`
   - Remove `bed_files/generate_synthetic.py`

3. **Test locally**
   - Run `pip install -e .` in the project root
   - Test each command with new module paths
   - Run `./run_all_docker.sh` to verify Docker workflow

---

## Summary of Changes

| Change Type | Count |
|-------------|-------|
| Files moved | 13 |
| New `__init__.py` files | 4 |
| Import updates in Python files | 6 |
| pyproject.toml updates | 1 |
| run_all_docker.sh updates | ~15 lines |
| README.md updates | ~30 lines |
| Dockerfile updates | ~3 lines |
| Directories to delete | 2 (benchmarks/, analysis/) |
| Files to delete | 2 (data/generate_test_data.py, bed_files/generate_synthetic.py) |

---

## Complete File Move Summary

```
benchmarks/__init__.py          -> DELETE (replaced by new src/__init__.py)
benchmarks/utils.py             -> src/refgetstore_benchmark/utils.py
benchmarks/deduplication.py     -> src/refgetstore_benchmark/benchmarks/deduplication.py
benchmarks/storage_size.py      -> src/refgetstore_benchmark/benchmarks/storage_size.py
benchmarks/region_extraction.py -> src/refgetstore_benchmark/benchmarks/region_extraction.py
benchmarks/export_fasta.py      -> src/refgetstore_benchmark/benchmarks/export_fasta.py
benchmarks/scaling.py           -> src/refgetstore_benchmark/benchmarks/scaling.py
benchmarks/verify_setup.py      -> src/refgetstore_benchmark/benchmarks/verify_setup.py
benchmarks/rsamtools_benchmark.R-> src/refgetstore_benchmark/benchmarks/rsamtools_benchmark.R
benchmarks/biostrings_benchmark.R-> src/refgetstore_benchmark/benchmarks/biostrings_benchmark.R
analysis/__init__.py            -> DELETE (replaced by new analysis/__init__.py)
analysis/figures.py             -> src/refgetstore_benchmark/analysis/figures.py
analysis/generate_report.py     -> src/refgetstore_benchmark/analysis/generate_report.py
analysis/report_templates.py    -> src/refgetstore_benchmark/analysis/report_templates.py
data/generate_test_data.py      -> src/refgetstore_benchmark/generators/fasta.py
bed_files/generate_synthetic.py -> src/refgetstore_benchmark/generators/bed.py
```

---

## Complete Import Update Summary

### src/refgetstore_benchmark/benchmarks/deduplication.py

```python
# OLD
from .utils import (...)

# NEW
from ..utils import (...)
```

### src/refgetstore_benchmark/benchmarks/storage_size.py

```python
# OLD
from .utils import (...)
try:
    from gtars.refget import RefgetStore
    GTARS_AVAILABLE = True
except ImportError:
    GTARS_AVAILABLE = False
try:
    from biocommons.seqrepo import SeqRepo
    SEQREPO_AVAILABLE = True
except ImportError:
    SEQREPO_AVAILABLE = False

# NEW
from ..utils import (
    Tools,
    format_bytes,
    get_directory_size,
    get_file_size,
    print_header,
    save_results,
)
# Then use Tools.gtars, Tools.RefgetStore, etc. throughout
```

### src/refgetstore_benchmark/benchmarks/region_extraction.py

```python
# OLD
from .utils import (...)

# NEW
from ..utils import (...)
```

### src/refgetstore_benchmark/benchmarks/export_fasta.py

```python
# OLD
from .utils import (...)

# NEW
from ..utils import (...)
```

### src/refgetstore_benchmark/benchmarks/scaling.py

```python
# OLD
from .utils import (...)

# NEW
from ..utils import (...)
```

### src/refgetstore_benchmark/analysis/generate_report.py

```python
# Already correct - uses local relative import
from .report_templates import (...)
```
