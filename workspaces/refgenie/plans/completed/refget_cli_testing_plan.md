# Refget CLI Testing Plan

**Status**: Ready for implementation
**Updated**: 2026-01-18

This plan adds **new CLI-specific tests** to the refget project using Typer's CliRunner. These complement the existing library unit tests.

## What This Plan Covers

This plan adds **CLI tests** - a new category that doesn't currently exist in the refget test suite.

### Current Test Coverage

```
tests/
├── local/                         # Library unit tests (EXISTING)
│   ├── test_digest_functions.py   # sha512t24u, md5, fasta_digest
│   ├── test_local_models.py       # SequenceCollection, compare, validate
│   └── test_refget_clients.py     # Client classes
├── api/                           # API compliance tests (EXISTING)
│   └── test_compliance.py
├── integration/                   # Client integration (EXISTING)
│   └── test_seqcolapi_client.py
└── test_cli/                      # CLI tests (NEW - this plan)
    └── (doesn't exist yet)
```

### What's Missing

**There are no CLI tests.** The existing tests cover library functions and API compliance, but nothing tests the CLI itself:
- Does `refget --help` work?
- Does `refget fasta digest file.fa` output valid JSON?
- Does a missing file return exit code 2?
- Do all subcommands parse arguments correctly?

This plan fills that gap.

## Architecture Context

The CLI is a thin wrapper over library functions:

```
┌─────────────────────────────────────────┐
│  CLI Layer (refget/cli/)                │
│  - Argument parsing (Typer)             │
│  - Output formatting (JSON, plain)      │
│  - Exit codes                           │
│  ← THIS PLAN TESTS THIS LAYER           │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│  Library Layer                          │
│  - Core logic, returns structured data  │
│  ← Existing unit tests cover this       │
└─────────────────────────────────────────┘
```

## CLI Testing Principles

1. **Use CliRunner** - Typer's built-in test runner, not subprocess
2. **No production code modification** - CliRunner works with unmodified CLI
3. **Test CLI-specific concerns** - Argument parsing, output format, exit codes
4. **Don't duplicate library tests** - If library tests cover the logic, CLI tests just verify the wrapper
5. **Isolated test data** - Use pytest's `tmp_path` fixture

## Test Directory Structure

New CLI tests go in `tests/test_cli/`:

```
tests/
├── conftest.py                    # Shared fixtures (add CLI fixtures here)
├── data/                          # Test FASTA files (existing)
│
├── [existing unit tests]          # Library tests (already exist)
│
├── test_cli/                      # NEW: CLI wrapper tests
│   ├── test_fasta_commands.py     # refget fasta *
│   ├── test_store_commands.py     # refget store *
│   ├── test_seqcol_commands.py    # refget seqcol *
│   ├── test_config_commands.py    # refget config *
│   ├── test_admin_commands.py     # refget admin *
│   └── test_help.py               # Help text verification
│
└── test_cli_integration/          # NEW: Multi-command CLI workflows
    └── test_workflows.py          # End-to-end CLI workflows
```

## conftest.py - Shared Fixtures

```python
# tests/conftest.py

import pytest
import json
from pathlib import Path
from typer.testing import CliRunner

from refget.cli import app

# ============================================================
# CLI Runner Fixtures
# ============================================================

@pytest.fixture
def runner():
    """Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def cli(runner):
    """
    Convenience fixture for invoking CLI commands.

    Usage:
        result = cli("fasta", "digest", "file.fa")
        assert result.exit_code == 0
    """
    def invoke(*args):
        return runner.invoke(app, list(args))
    return invoke


# ============================================================
# Test Data Paths
# ============================================================

TEST_DATA_DIR = Path(__file__).parent / "data"
SMALL_FASTA = TEST_DATA_DIR / "small.fa"
SMALL_FASTA_GZ = TEST_DATA_DIR / "small.fa.gz"
MULTI_FASTA = TEST_DATA_DIR / "multi.fa"


# ============================================================
# FASTA File Fixtures
# ============================================================

@pytest.fixture
def sample_fasta(tmp_path):
    """Create sample FASTA in temp directory."""
    fasta = tmp_path / "sample.fa"
    fasta.write_text(">chr1\nACGTACGT\n>chr2\nGGCCGGCC\n")
    return fasta


@pytest.fixture
def sample_fasta_gz(tmp_path):
    """Create gzipped sample FASTA."""
    import gzip
    fasta = tmp_path / "sample.fa.gz"
    with gzip.open(fasta, 'wt') as f:
        f.write(">chr1\nACGTACGT\n>chr2\nGGCCGGCC\n")
    return fasta


@pytest.fixture
def large_fasta(tmp_path):
    """Create larger FASTA for performance tests."""
    fasta = tmp_path / "large.fa"
    seq = "ACGTACGTACGT" * 1000
    content = f">chr1\n{seq}\n>chr2\n{seq}\n"
    fasta.write_text(content)
    return fasta


# ============================================================
# Store Fixtures
# ============================================================

@pytest.fixture
def temp_store(tmp_path, cli):
    """Initialize a temporary RefgetStore."""
    store_path = tmp_path / "store"
    result = cli("store", "init", "--path", str(store_path))
    assert result.exit_code == 0, f"Failed to init store: {result.stdout}"
    return store_path


@pytest.fixture
def populated_store(temp_store, cli):
    """Store with test FASTA already loaded."""
    result = cli("store", "add", str(SMALL_FASTA), "--path", str(temp_store))
    assert result.exit_code == 0, f"Failed to add FASTA: {result.stdout}"

    # Parse digest from JSON output
    output = json.loads(result.stdout)
    return {
        "path": temp_store,
        "digest": output["digest"],
    }


# ============================================================
# Config Fixtures
# ============================================================

@pytest.fixture
def temp_config(tmp_path):
    """Create temporary config file."""
    config_path = tmp_path / "config.toml"
    config_path.write_text(f'''
[store]
path = "{tmp_path}/store"
''')
    return config_path


@pytest.fixture
def env_with_config(temp_config, monkeypatch):
    """Set REFGET_CONFIG env var to temp config."""
    monkeypatch.setenv("REFGET_CONFIG", str(temp_config))
    return temp_config


# ============================================================
# Assertion Helpers
# ============================================================

def assert_valid_digest(digest: str):
    """Assert string is valid seqcol digest format."""
    # Seqcol digests are typically 48 chars or start with specific prefix
    assert len(digest) >= 32, f"Invalid digest format: {digest}"


def assert_json_output(result, required_keys: list = None):
    """Assert CLI output is valid JSON with optional required keys."""
    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"Output is not valid JSON: {result.stdout}")

    if required_keys:
        for key in required_keys:
            assert key in data, f"Missing key '{key}' in output: {data}"

    return data
```

## CLI Tests (test_cli/)

### test_fasta_commands.py

```python
# tests/test_cli/test_fasta_commands.py

"""
Tests for refget fasta CLI commands.

These test the CLI wrapper behavior: output formatting, exit codes, argument parsing.
"""

import pytest
import json
from pathlib import Path

from conftest import SMALL_FASTA, SMALL_FASTA_GZ, assert_json_output, assert_valid_digest


class TestFastaDigest:
    """Tests for: refget fasta digest <file>"""

    def test_outputs_json(self, cli, sample_fasta):
        """Output is valid JSON with digest."""
        result = cli("fasta", "digest", str(sample_fasta))

        data = assert_json_output(result, ["digest", "file"])
        assert_valid_digest(data["digest"])

    def test_gzipped_file(self, cli, sample_fasta_gz):
        """Handles gzipped files seamlessly."""
        result = cli("fasta", "digest", str(sample_fasta_gz))

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "digest" in data

    def test_file_not_found_exit_code(self, cli):
        """Returns exit code 2 for missing file."""
        result = cli("fasta", "digest", "/nonexistent/file.fa")

        assert result.exit_code == 2
        assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()

    def test_missing_argument(self, cli):
        """Returns non-zero exit for missing argument."""
        result = cli("fasta", "digest")

        assert result.exit_code != 0
        assert "Missing argument" in result.stdout or "Usage:" in result.stdout


class TestFastaSeqcol:
    """Tests for: refget fasta seqcol <file>"""

    def test_outputs_seqcol_json(self, cli, sample_fasta):
        """Output is valid seqcol JSON."""
        result = cli("fasta", "seqcol", str(sample_fasta))

        data = assert_json_output(result, ["names", "lengths", "sequences"])
        assert isinstance(data["names"], list)

    def test_output_to_file(self, cli, sample_fasta, tmp_path):
        """Writes to file with -o option."""
        output = tmp_path / "out.seqcol.json"
        result = cli("fasta", "seqcol", str(sample_fasta), "-o", str(output))

        assert result.exit_code == 0
        assert output.exists()

        data = json.loads(output.read_text())
        assert "names" in data


class TestFastaFai:
    """Tests for: refget fasta fai <file>"""

    def test_outputs_fai_format(self, cli, sample_fasta, tmp_path):
        """Outputs valid FAI format."""
        output = tmp_path / "test.fa.fai"
        result = cli("fasta", "fai", str(sample_fasta), "-o", str(output))

        assert result.exit_code == 0
        assert output.exists()

        # FAI format: name\tlength\toffset\tline_bases\tline_width
        lines = output.read_text().strip().split("\n")
        assert len(lines) > 0
        for line in lines:
            parts = line.split("\t")
            assert len(parts) >= 2  # At least name and length


class TestFastaChromSizes:
    """Tests for: refget fasta chrom-sizes <file>"""

    def test_outputs_chrom_sizes(self, cli, sample_fasta, tmp_path):
        """Outputs valid chrom.sizes format."""
        output = tmp_path / "test.chrom.sizes"
        result = cli("fasta", "chrom-sizes", str(sample_fasta), "-o", str(output))

        assert result.exit_code == 0
        assert output.exists()

        # Format: name\tlength
        lines = output.read_text().strip().split("\n")
        for line in lines:
            parts = line.split("\t")
            assert len(parts) == 2
            assert parts[1].isdigit()


class TestFastaIndex:
    """Tests for: refget fasta index <file>"""

    def test_creates_all_files(self, cli, sample_fasta):
        """Creates .fai, .seqcol.json, .chrom.sizes."""
        result = cli("fasta", "index", str(sample_fasta))

        assert result.exit_code == 0

        # Check files created
        assert Path(str(sample_fasta) + ".fai").exists()
        assert (sample_fasta.parent / f"{sample_fasta.stem}.seqcol.json").exists()
        assert (sample_fasta.parent / f"{sample_fasta.stem}.chrom.sizes").exists()


class TestFastaStats:
    """Tests for: refget fasta stats <file>"""

    def test_outputs_stats(self, cli, sample_fasta):
        """Outputs statistics about FASTA."""
        result = cli("fasta", "stats", str(sample_fasta), "--json")

        data = assert_json_output(result, ["sequences", "total_length"])
        assert isinstance(data["sequences"], int)
        assert data["sequences"] > 0
```

### test_store_commands.py

```python
# tests/test_cli/test_store_commands.py

"""Tests for refget store CLI commands."""

import pytest
import json
from conftest import SMALL_FASTA, assert_json_output


class TestStoreInit:
    """Tests for: refget store init"""

    def test_creates_store(self, cli, tmp_path):
        """Initializes new store directory."""
        store_path = tmp_path / "new_store"
        result = cli("store", "init", "--path", str(store_path))

        assert result.exit_code == 0
        assert store_path.exists()

    def test_idempotent(self, cli, temp_store):
        """Re-init existing store succeeds."""
        result = cli("store", "init", "--path", str(temp_store))

        assert result.exit_code == 0


class TestStoreAdd:
    """Tests for: refget store add <fasta>"""

    def test_adds_fasta(self, cli, temp_store):
        """Adds FASTA and returns digest."""
        result = cli("store", "add", str(SMALL_FASTA), "--path", str(temp_store))

        data = assert_json_output(result, ["digest"])
        assert len(data["digest"]) > 0

    def test_idempotent(self, cli, temp_store):
        """Adding same file twice returns same digest."""
        result1 = cli("store", "add", str(SMALL_FASTA), "--path", str(temp_store))
        result2 = cli("store", "add", str(SMALL_FASTA), "--path", str(temp_store))

        digest1 = json.loads(result1.stdout)["digest"]
        digest2 = json.loads(result2.stdout)["digest"]
        assert digest1 == digest2


class TestStoreList:
    """Tests for: refget store list"""

    def test_empty_store(self, cli, temp_store):
        """Lists empty store."""
        result = cli("store", "list", "--path", str(temp_store))

        data = assert_json_output(result, ["collections"])
        assert data["collections"] == []

    def test_with_collections(self, cli, populated_store):
        """Lists store with collections."""
        result = cli("store", "list", "--path", str(populated_store["path"]))

        data = assert_json_output(result, ["collections"])
        assert len(data["collections"]) >= 1


class TestStoreExport:
    """Tests for: refget store export <digest>"""

    def test_exports_fasta(self, cli, populated_store, tmp_path):
        """Exports collection as FASTA."""
        output = tmp_path / "exported.fa"
        result = cli(
            "store", "export", populated_store["digest"],
            "-o", str(output),
            "--path", str(populated_store["path"])
        )

        assert result.exit_code == 0
        assert output.exists()
        content = output.read_text()
        assert content.startswith(">")


class TestStoreSeq:
    """Tests for: refget store seq <digest>"""

    def test_gets_sequence(self, cli, populated_store):
        """Gets sequence by name."""
        result = cli(
            "store", "seq", populated_store["digest"],
            "--name", "chr1",
            "--path", str(populated_store["path"])
        )

        assert result.exit_code == 0
        # Output should be raw sequence or FASTA
        assert len(result.stdout.strip()) > 0

    def test_substring(self, cli, populated_store):
        """Gets subsequence with range."""
        result = cli(
            "store", "seq", populated_store["digest"],
            "--name", "chr1",
            "--start", "0",
            "--end", "4",
            "--path", str(populated_store["path"])
        )

        assert result.exit_code == 0
        seq = result.stdout.strip()
        assert len(seq) <= 4


class TestStoreStats:
    """Tests for: refget store stats"""

    def test_outputs_stats(self, cli, populated_store):
        """Outputs store statistics."""
        result = cli("store", "stats", "--path", str(populated_store["path"]))

        data = assert_json_output(result, ["collections"])
        assert data["collections"] >= 1
```

### test_config_commands.py

```python
# tests/test_cli/test_config_commands.py

"""Tests for refget config CLI commands."""

import pytest
import json


class TestConfigShow:
    """Tests for: refget config show"""

    def test_shows_config(self, cli, env_with_config):
        """Displays current configuration."""
        result = cli("config", "show")

        assert result.exit_code == 0
        # Should show config as JSON or formatted output
        assert "store" in result.stdout.lower()


class TestConfigGet:
    """Tests for: refget config get <key>"""

    def test_gets_value(self, cli, env_with_config):
        """Gets specific config value."""
        result = cli("config", "get", "store.path")

        assert result.exit_code == 0

    def test_missing_key(self, cli, env_with_config):
        """Returns error for nonexistent key."""
        result = cli("config", "get", "nonexistent.key")

        assert result.exit_code != 0


class TestConfigSet:
    """Tests for: refget config set <key> <value>"""

    def test_sets_value(self, cli, temp_config, monkeypatch):
        """Sets config value."""
        monkeypatch.setenv("REFGET_CONFIG", str(temp_config))

        result = cli("config", "set", "store.path", "/new/path")
        assert result.exit_code == 0

        # Verify it was set
        result = cli("config", "get", "store.path")
        assert "/new/path" in result.stdout


class TestConfigInit:
    """Tests for: refget config init"""

    def test_interactive_init(self, runner, tmp_path, monkeypatch):
        """Interactive configuration wizard."""
        from refget.cli import app

        config_path = tmp_path / "config.toml"
        monkeypatch.setenv("REFGET_CONFIG", str(config_path))

        result = runner.invoke(
            app,
            ["config", "init"],
            input=f"{tmp_path}/store\nhttps://seqcolapi.databio.org\n\n"
        )

        assert result.exit_code == 0
```

### test_help.py

```python
# tests/test_cli/test_help.py

"""Tests for CLI help output."""

import pytest


class TestHelpOutput:
    """Verify help text displays correctly."""

    def test_main_help(self, cli):
        """Main help shows all command groups."""
        result = cli("--help")

        assert result.exit_code == 0
        assert "config" in result.stdout
        assert "store" in result.stdout
        assert "fasta" in result.stdout
        assert "seqcol" in result.stdout
        assert "admin" in result.stdout

    def test_fasta_help(self, cli):
        """Fasta subcommand help."""
        result = cli("fasta", "--help")

        assert result.exit_code == 0
        assert "digest" in result.stdout
        assert "seqcol" in result.stdout
        assert "fai" in result.stdout

    def test_store_help(self, cli):
        """Store subcommand help."""
        result = cli("store", "--help")

        assert result.exit_code == 0
        assert "init" in result.stdout
        assert "add" in result.stdout
        assert "export" in result.stdout

    def test_command_help(self, cli):
        """Individual command help."""
        result = cli("fasta", "digest", "--help")

        assert result.exit_code == 0
        assert "FILE" in result.stdout or "file" in result.stdout.lower()

    def test_version(self, cli):
        """Version flag works."""
        result = cli("--version")

        assert result.exit_code == 0
        # Should show version number
        assert "." in result.stdout  # e.g., "0.1.0"
```

## Integration Tests (test_integration/)

### test_workflows.py

```python
# tests/test_integration/test_workflows.py

"""
Integration tests for multi-command workflows.
"""

import pytest
import json
from conftest import SMALL_FASTA


class TestDigestAndCompare:
    """Test digest → compare workflow."""

    def test_compare_fasta_files(self, cli, sample_fasta, tmp_path):
        """Compare two FASTA files directly."""
        fasta2 = tmp_path / "other.fa"
        fasta2.write_text(">chr1\nACGTACGT\n>chr2\nGGCCGGCC\n")

        result = cli("seqcol", "compare", str(sample_fasta), str(fasta2))

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "compatible" in data or "match" in data

    def test_compute_then_compare(self, cli, sample_fasta, tmp_path):
        """Compute seqcol JSON, then compare."""
        seqcol_file = tmp_path / "test.seqcol.json"

        # Step 1: Compute seqcol
        result = cli("fasta", "seqcol", str(sample_fasta), "-o", str(seqcol_file))
        assert result.exit_code == 0

        # Step 2: Compare using seqcol file
        result = cli("seqcol", "compare", str(seqcol_file), str(sample_fasta))
        assert result.exit_code == 0


class TestStoreLifecycle:
    """Test complete store lifecycle."""

    def test_init_add_list_export(self, cli, tmp_path):
        """Full store workflow: init → add → list → export."""
        store = tmp_path / "store"
        output = tmp_path / "exported.fa"

        # Init
        result = cli("store", "init", "--path", str(store))
        assert result.exit_code == 0

        # Add
        result = cli("store", "add", str(SMALL_FASTA), "--path", str(store))
        assert result.exit_code == 0
        digest = json.loads(result.stdout)["digest"]

        # List
        result = cli("store", "list", "--path", str(store))
        assert result.exit_code == 0
        collections = json.loads(result.stdout)["collections"]
        assert len(collections) == 1

        # Export
        result = cli("store", "export", digest, "-o", str(output), "--path", str(store))
        assert result.exit_code == 0
        assert output.exists()

        # Stats
        result = cli("store", "stats", "--path", str(store))
        assert result.exit_code == 0


class TestFastaIndexWorkflow:
    """Test fasta index creates usable outputs."""

    def test_index_then_use_outputs(self, cli, sample_fasta):
        """Index creates files that can be used."""
        # Create all index files
        result = cli("fasta", "index", str(sample_fasta))
        assert result.exit_code == 0

        # Verify seqcol.json is valid
        seqcol_file = sample_fasta.parent / f"{sample_fasta.stem}.seqcol.json"
        assert seqcol_file.exists()

        seqcol = json.loads(seqcol_file.read_text())
        assert "names" in seqcol
        assert "lengths" in seqcol
```

## pytest Configuration

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    slow: marks tests as slow
    requires_network: marks tests requiring network

addopts = -v --tb=short

filterwarnings =
    ignore::DeprecationWarning
```

### pyproject.toml (test dependencies)

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov",
]
```

## Test Data Files

Create in `tests/data/`:

### small.fa
```
>chr1
ACGTACGTACGTACGT
>chr2
GGCCGGCCGGCCGGCC
```

### multi.fa
```
>chr1 description one
ACGTACGT
>chr2 description two
GGCCGGCC
>chr3
TTAATTAA
```

## Running Tests

```bash
# All tests
pytest

# Library tests only (fast)
pytest tests/test_processing/

# CLI tests only
pytest tests/test_cli/

# Integration tests
pytest tests/test_integration/

# With coverage
pytest --cov=refget --cov-report=html

# Specific test file
pytest tests/test_cli/test_fasta_commands.py

# Specific test class
pytest tests/test_cli/test_fasta_commands.py::TestFastaDigest

# Verbose output
pytest -v
```

## Summary

This plan adds CLI-specific tests using Typer's CliRunner.

| Test Category | Directory | Purpose |
|---------------|-----------|---------|
| CLI commands | `test_cli/` | Output formatting, exit codes, argument parsing |
| CLI workflows | `test_cli_integration/` | Multi-command sequences |

### Key Patterns

1. **CliRunner** - Typer's built-in test runner (no subprocess)
2. **`cli` fixture** - Convenient command invocation
3. **`assert_json_output`** - Validate JSON responses
4. **Fixture composition** - `tmp_path` → `temp_store` → `populated_store`

### Estimated New Test Count

| Category | Count |
|----------|-------|
| CLI (fasta) | ~15 |
| CLI (store) | ~12 |
| CLI (seqcol) | ~8 |
| CLI (config) | ~6 |
| CLI (admin) | ~5 |
| CLI (help) | ~5 |
| CLI integration | ~10 |
| **Total new CLI tests** | **~61** |
