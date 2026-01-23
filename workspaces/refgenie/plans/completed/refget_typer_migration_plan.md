# Refget CLI Migration: argparse → Typer

**Status**: Plan - Ready for implementation
**Date**: 2026-01-18

## Goal

Migrate the refget CLI from argparse to Typer, implementing the complete command structure defined in `refget_cli_command_structure.md`. This migration will:

1. Replace the current 4-command argparse CLI with a modern Typer-based CLI
2. Implement all 5 command groups (config, store, fasta, seqcol, admin)
3. Enable built-in `CliRunner` testing without custom `test_args` infrastructure
4. Support type-hint-based argument definitions for cleaner code

**IMPORTANT: DO NOT MAINTAIN BACKWARDS COMPATIBILITY.** This is developmental software. The old argparse CLI will be completely replaced, not deprecated alongside the new one.

---

## Context Files to Read

Before implementation, read these files to understand the current state and design:

1. **Current CLI implementation**: `/repos/refget/refget/refget.py` (532 lines)
2. **Planned command structure**: `/plans/refget_cli_command_structure.md`
3. **Testing patterns**: `/plans/test_args_implementation_guide.md`
4. **Package setup**: `/repos/refget/setup.py` (entry point definition)
5. **Processing module**: `/repos/refget/refget/processing/` (gtars integration)

---

## Current State Analysis

### Current CLI (argparse)

- **Location**: `refget/refget.py` (single 532-line file)
- **Framework**: argparse via `ubiquerg.VersionInHelpParser`
- **Commands**: 4 admin-focused commands
  - `load` → database loading
  - `register` → S3 upload + DRS registration
  - `load-and-register` → combined workflow
  - `digest-fasta` → compute seqcol digest
- **Entry point**: `refget = refget.refget:main`

### Target CLI (Typer)

- **Framework**: Typer (built on Click)
- **Commands**: 5 command groups, ~30 subcommands
- **Structure**: Multi-module architecture
- **Testing**: Built-in CliRunner support

---

## Implementation Steps

### Step 1: Add Typer Dependency

**File**: `/repos/refget/setup.py`

Add Typer to install_requires:

```python
install_requires=[
    "typer>=0.9.0",
    "rich>=13.0.0",  # For pretty output (Typer uses this)
    # ... existing deps
],
```

Remove `ubiquerg` from dependencies (no longer needed for CLI).

### Step 2: Create CLI Module Structure

**Create new directory structure**:

```
refget/
├── cli/
│   ├── __init__.py          # Main Typer app, exports `app`
│   ├── config.py            # config subcommands
│   ├── store.py             # store subcommands
│   ├── fasta.py             # fasta subcommands
│   ├── seqcol.py            # seqcol subcommands
│   ├── admin.py             # admin subcommands (migrated from refget.py)
│   └── _helpers.py          # Shared utilities (output formatting, config loading)
```

### Step 3: Implement Main App (`cli/__init__.py`)

```python
"""Refget CLI - GA4GH reference sequence access and management."""
import typer

from . import config, store, fasta, seqcol, admin

app = typer.Typer(
    name="refget",
    help="GA4GH refget CLI - reference sequence access and management",
    no_args_is_help=True,
)

# Register subcommand groups
app.add_typer(config.app, name="config", help="Configuration management")
app.add_typer(store.app, name="store", help="Local/remote RefgetStore operations")
app.add_typer(fasta.app, name="fasta", help="Standalone FASTA file utilities")
app.add_typer(seqcol.app, name="seqcol", help="Sequence collection API operations")
app.add_typer(admin.app, name="admin", help="Server infrastructure (PostgreSQL)")

def main():
    """Entry point for console script."""
    app()
```

### Step 4: Implement Config Commands (`cli/config.py`)

```python
"""Configuration management commands."""
import typer
from pathlib import Path
from typing import Optional

app = typer.Typer(no_args_is_help=True)

@app.command()
def init():
    """Interactive configuration setup wizard."""
    # Implementation: prompt for store path, servers, etc.
    pass

@app.command()
def show():
    """Display current configuration."""
    pass

@app.command()
def get(key: str):
    """Get a specific configuration value."""
    pass

@app.command("set")  # 'set' is reserved in Python
def set_value(key: str, value: str):
    """Set a configuration value."""
    pass

@app.command()
def add(
    item_type: str = typer.Argument(..., help="Type: seqcol_server or remote_store"),
    url: str = typer.Argument(..., help="URL to add"),
    name: Optional[str] = typer.Option(None, help="Optional name for the entry"),
):
    """Add a server or store to configuration."""
    pass

@app.command()
def remove(
    item_type: str = typer.Argument(..., help="Type: seqcol_server or remote_store"),
    name: str = typer.Argument(..., help="Name of entry to remove"),
):
    """Remove a server or store from configuration."""
    pass
```

### Step 5: Implement FASTA Commands (`cli/fasta.py`)

```python
"""Standalone FASTA file utilities."""
import typer
from pathlib import Path
from typing import Optional
import json

app = typer.Typer(no_args_is_help=True)

@app.command()
def digest(
    file: Path = typer.Argument(..., help="Path to FASTA file"),
):
    """Compute seqcol digest of a FASTA file."""
    from refget.processing.fasta import fasta_to_digest
    result = fasta_to_digest(str(file))
    typer.echo(json.dumps({"digest": result, "file": str(file)}, indent=2))

@app.command()
def seqcol(
    file: Path = typer.Argument(..., help="Path to FASTA file"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Output file"),
):
    """Compute full seqcol JSON from FASTA."""
    from refget.processing.fasta import fasta_to_seqcol_dict
    result = fasta_to_seqcol_dict(str(file))
    json_output = json.dumps(result, indent=2)
    if output:
        output.write_text(json_output)
        typer.echo(f"Written to {output}")
    else:
        typer.echo(json_output)

@app.command()
def fai(
    file: Path = typer.Argument(..., help="Path to FASTA file"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Output file"),
):
    """Compute FAI index from FASTA."""
    pass  # Implementation using gtars compute_fai

@app.command("chrom-sizes")
def chrom_sizes(
    file: Path = typer.Argument(..., help="Path to FASTA file"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Output file"),
):
    """Compute chromosome sizes from FASTA."""
    pass

@app.command()
def index(
    file: Path = typer.Argument(..., help="Path to FASTA file"),
):
    """Generate ALL derived files at once (.fai, .seqcol.json, .chrom.sizes, .rgsi, .rgci)."""
    pass

@app.command()
def stats(
    file: Path = typer.Argument(..., help="Path to FASTA file"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Display FASTA file statistics."""
    pass

@app.command()
def rgsi(
    file: Path = typer.Argument(..., help="Path to FASTA file"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Output file"),
):
    """Compute .rgsi (sequence index) from FASTA."""
    pass

@app.command()
def rgci(
    file: Path = typer.Argument(..., help="Path to FASTA file"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Output file"),
):
    """Compute .rgci (collection index) from FASTA."""
    pass
```

### Step 6: Implement Store Commands (`cli/store.py`)

```python
"""RefgetStore operations - local and remote."""
import typer
from pathlib import Path
from typing import Optional

app = typer.Typer(no_args_is_help=True)

@app.command()
def init(
    path: Optional[Path] = typer.Option(None, "--path", help="Store directory path"),
):
    """Initialize a local RefgetStore."""
    pass

@app.command()
def add(
    fasta: Path = typer.Argument(..., help="FASTA file to import"),
    path: Optional[Path] = typer.Option(None, "--path", help="Store path (uses config default)"),
):
    """Import a FASTA file into the local store."""
    pass

@app.command("list")
def list_collections(
    path: Optional[Path] = typer.Option(None, "--path", help="Store path"),
):
    """List collections in the store."""
    pass

@app.command()
def pull(
    digest: str = typer.Argument(..., help="Collection digest to pull"),
    file: Optional[Path] = typer.Option(None, "--file", help="File with list of digests"),
    server: Optional[str] = typer.Option(None, "--server", help="Override server URL"),
):
    """Pull a collection from remote store."""
    pass

@app.command()
def export(
    digest: str = typer.Argument(..., help="Collection digest"),
    output: Path = typer.Option(..., "-o", "--output", help="Output FASTA file"),
    bed: Optional[Path] = typer.Option(None, "--bed", help="BED file for region extraction"),
    path: Optional[Path] = typer.Option(None, "--path", help="Store path"),
):
    """Export a collection as FASTA."""
    pass

@app.command()
def seq(
    digest: str = typer.Argument(..., help="Sequence or collection digest"),
    name: Optional[str] = typer.Option(None, "--name", help="Sequence name (for collection digest)"),
    start: Optional[int] = typer.Option(None, "--start", help="Start position"),
    end: Optional[int] = typer.Option(None, "--end", help="End position"),
    path: Optional[Path] = typer.Option(None, "--path", help="Store path"),
):
    """Get sequence or subsequence by digest."""
    pass

@app.command()
def fai(
    digest: str = typer.Argument(..., help="Collection digest"),
    output: Path = typer.Option(..., "-o", "--output", help="Output .fai file"),
    path: Optional[Path] = typer.Option(None, "--path", help="Store path"),
):
    """Generate .fai index from collection in store."""
    pass

@app.command("chrom-sizes")
def chrom_sizes(
    digest: str = typer.Argument(..., help="Collection digest"),
    output: Path = typer.Option(..., "-o", "--output", help="Output .chrom.sizes file"),
    path: Optional[Path] = typer.Option(None, "--path", help="Store path"),
):
    """Generate chrom.sizes from collection in store."""
    pass

@app.command()
def stats(
    path: Optional[Path] = typer.Option(None, "--path", help="Store path"),
):
    """Display store statistics."""
    pass
```

### Step 7: Implement SeqCol Commands (`cli/seqcol.py`)

```python
"""Sequence Collection API operations."""
import typer
from pathlib import Path
from typing import Optional

app = typer.Typer(no_args_is_help=True)

@app.command()
def show(
    digest: str = typer.Argument(..., help="Seqcol digest"),
    level: int = typer.Option(2, "--level", "-l", help="Output level (0, 1, or 2)"),
    server: Optional[str] = typer.Option(None, "--server", help="Override server URL"),
):
    """Get sequence collection by digest."""
    pass

@app.command()
def compare(
    a: str = typer.Argument(..., help="First seqcol (digest, file, or FASTA)"),
    b: str = typer.Argument(..., help="Second seqcol (digest, file, or FASTA)"),
    server: Optional[str] = typer.Option(None, "--server", help="Override server URL"),
):
    """Compare two sequence collections."""
    pass

@app.command("list")
def list_collections(
    server: Optional[str] = typer.Option(None, "--server", help="Override server URL"),
):
    """List collections on server."""
    pass

@app.command()
def search(
    names: Optional[str] = typer.Option(None, "--names", help="Search by names digest"),
    lengths: Optional[str] = typer.Option(None, "--lengths", help="Search by lengths digest"),
    server: Optional[str] = typer.Option(None, "--server", help="Override server URL"),
):
    """Search for collections by attribute."""
    pass

@app.command()
def attributes(
    attr: str = typer.Argument(..., help="Attribute name"),
    server: Optional[str] = typer.Option(None, "--server", help="Override server URL"),
):
    """List unique values for an attribute."""
    pass

@app.command()
def info(
    server: Optional[str] = typer.Option(None, "--server", help="Override server URL"),
):
    """Display server capabilities."""
    pass
```

### Step 8: Migrate Admin Commands (`cli/admin.py`)

Migrate existing business logic from `refget.py`, updating signatures to Typer style:

```python
"""Admin commands for server infrastructure (PostgreSQL)."""
import typer
from pathlib import Path
from typing import Optional

app = typer.Typer(no_args_is_help=True)

@app.command()
def load(
    input_file: Path = typer.Argument(..., help="FASTA or .seqcol.json file"),
    name: Optional[str] = typer.Option(None, "-n", "--name", help="Human-readable name"),
    pep: Optional[Path] = typer.Option(None, "-p", "--pep", help="PEP file for batch loading"),
    pephub: Optional[str] = typer.Option(None, "--pephub", help="PEPhub project"),
    fa_root: Optional[Path] = typer.Option(None, "-r", "--fa-root", help="FASTA root directory"),
):
    """Load seqcol metadata into PostgreSQL database."""
    # Migrate logic from refget.py add_fasta() and add_fasta_pep()
    pass

@app.command()
def register(
    fasta: Path = typer.Argument(..., help="FASTA file to upload"),
    bucket: str = typer.Option(..., "-b", "--bucket", help="S3 bucket name"),
    digest: Optional[str] = typer.Option(None, "-d", "--digest", help="Seqcol digest"),
    prefix: str = typer.Option("", "--prefix", help="S3 key prefix"),
    cloud: str = typer.Option("aws", "-c", "--cloud", help="Cloud provider"),
    region: str = typer.Option("us-east-1", "--region", help="Cloud region"),
    pep: Optional[Path] = typer.Option(None, "-p", "--pep", help="PEP file"),
    pephub: Optional[str] = typer.Option(None, "--pephub", help="PEPhub project"),
    fa_root: Optional[Path] = typer.Option(None, "-r", "--fa-root", help="FASTA root directory"),
):
    """Upload FASTA to cloud storage and register DRS access method."""
    # Migrate logic from refget.py register_fasta()
    pass

@app.command()
def ingest(
    fasta: Optional[Path] = typer.Argument(None, help="FASTA file"),
    bucket: str = typer.Option(..., "-b", "--bucket", help="S3 bucket name"),
    name: Optional[str] = typer.Option(None, "-n", "--name", help="Human-readable name"),
    prefix: str = typer.Option("", "--prefix", help="S3 key prefix"),
    cloud: str = typer.Option("aws", "-c", "--cloud", help="Cloud provider"),
    region: str = typer.Option("us-east-1", "--region", help="Cloud region"),
    pep: Optional[Path] = typer.Option(None, "-p", "--pep", help="PEP file"),
    pephub: Optional[str] = typer.Option(None, "--pephub", help="PEPhub project"),
    fa_root: Optional[Path] = typer.Option(None, "-r", "--fa-root", help="FASTA root directory"),
):
    """Full workflow: load metadata + upload to cloud + register access."""
    # Migrate logic from refget.py load-and-register command
    pass
```

### Step 9: Implement Helper Module (`cli/_helpers.py`)

```python
"""Shared CLI utilities."""
import json
import sys
from pathlib import Path
from typing import Any, Optional

import typer

# Config file handling
DEFAULT_CONFIG_PATH = Path.home() / ".refget" / "config.toml"

def load_config(config_path: Optional[Path] = None) -> dict:
    """Load configuration from file, env vars, and defaults."""
    pass

def get_store_path(override: Optional[Path] = None) -> Path:
    """Get store path from override, env var, config, or default."""
    pass

def output_json(data: Any, pretty: bool = True):
    """Output data as JSON."""
    indent = 2 if pretty else None
    typer.echo(json.dumps(data, indent=indent))

def check_dependency(name: str, install_hint: str):
    """Check if optional dependency is available, exit with helpful message if not."""
    try:
        __import__(name)
    except ImportError:
        typer.echo(f"Error: This command requires {name}.", err=True)
        typer.echo(f"Install with: {install_hint}", err=True)
        raise typer.Exit(1)
```

### Step 10: Update Entry Point

**File**: `/repos/refget/setup.py`

Change:
```python
entry_points={
    "console_scripts": ["refget = refget.refget:main"],
}
```

To:
```python
entry_points={
    "console_scripts": ["refget = refget.cli:main"],
}
```

### Step 11: Delete Old CLI File

**Delete**: `/repos/refget/refget/refget.py`

Move reusable business logic functions to appropriate modules:
- `add_fasta()` → `refget/admin/loader.py` or keep in `cli/admin.py`
- `register_fasta()` → `refget/admin/register.py` or keep in `cli/admin.py`
- `_upload_to_s3()` → `refget/utilities.py`
- `load_pep()` → `refget/utilities.py`

### Step 12: Implement Tests Using Typer's CliRunner

**File**: `/repos/refget/tests/test_cli.py`

```python
"""CLI tests using Typer's CliRunner."""
import pytest
from typer.testing import CliRunner

from refget.cli import app

runner = CliRunner()

class TestFastaCommands:
    """Tests for refget fasta subcommands."""

    def test_digest(self, sample_fasta):
        result = runner.invoke(app, ["fasta", "digest", str(sample_fasta)])
        assert result.exit_code == 0
        assert "digest" in result.stdout

    def test_digest_missing_file(self):
        result = runner.invoke(app, ["fasta", "digest", "/nonexistent.fa"])
        assert result.exit_code != 0

    def test_seqcol(self, sample_fasta, tmp_path):
        output = tmp_path / "test.seqcol.json"
        result = runner.invoke(app, ["fasta", "seqcol", str(sample_fasta), "-o", str(output)])
        assert result.exit_code == 0
        assert output.exists()


class TestConfigCommands:
    """Tests for refget config subcommands."""

    def test_show(self):
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0


class TestHelpOutput:
    """Test help displays correctly."""

    def test_main_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "config" in result.stdout
        assert "store" in result.stdout
        assert "fasta" in result.stdout
        assert "seqcol" in result.stdout
        assert "admin" in result.stdout

    def test_fasta_help(self):
        result = runner.invoke(app, ["fasta", "--help"])
        assert result.exit_code == 0
        assert "digest" in result.stdout
        assert "seqcol" in result.stdout
```

### Step 13: Update Package Exports

**File**: `/repos/refget/refget/__init__.py`

Ensure CLI is importable:
```python
from .cli import app as cli_app
```

---

## Summary of Changes

### Files to Create

| File | Purpose |
|------|---------|
| `refget/cli/__init__.py` | Main Typer app |
| `refget/cli/config.py` | Config subcommands |
| `refget/cli/store.py` | Store subcommands |
| `refget/cli/fasta.py` | FASTA subcommands |
| `refget/cli/seqcol.py` | SeqCol subcommands |
| `refget/cli/admin.py` | Admin subcommands |
| `refget/cli/_helpers.py` | Shared utilities |
| `tests/test_cli.py` | CliRunner tests |

### Files to Modify

| File | Change |
|------|--------|
| `setup.py` | Add typer dep, change entry point |
| `refget/__init__.py` | Export CLI app |

### Files to Delete

| File | Reason |
|------|--------|
| `refget/refget.py` | Replaced by `refget/cli/` module |

### Before/After Comparison

| Metric | Before (argparse) | After (Typer) |
|--------|-------------------|---------------|
| CLI file(s) | 1 file, 532 lines | 7 files, ~600 lines |
| Commands | 4 | ~30 |
| Command groups | 0 | 5 |
| Testing | Custom `test_args` | Built-in CliRunner |
| Type hints | None | Full coverage |
| Help generation | Manual | Automatic |
| Dependencies | ubiquerg | typer, rich |

---

## Verification

After implementation, verify:

1. **All commands work**: `refget --help` shows all 5 groups
2. **Tests pass**: `pytest tests/test_cli.py`
3. **Migration complete**: Old commands map correctly
   - `refget load` → `refget admin load`
   - `refget register` → `refget admin register`
   - `refget load-and-register` → `refget admin ingest`
   - `refget digest-fasta` → `refget fasta digest`
4. **No backwards compatibility**: Old commands should NOT work

---

## References

- Typer documentation: https://typer.tiangolo.com/
- Typer testing: https://typer.tiangolo.com/tutorial/testing/
- Command structure plan: `plans/refget_cli_command_structure.md`
- Testing patterns: `plans/test_args_implementation_guide.md`
