# Testing Typer CLIs: A Modern Approach

**Status**: Reference documentation
**Date**: 2026-01-18

This guide explains how to test Typer-based CLIs using the built-in CliRunner. It separates two orthogonal concerns:

1. **Part 1: Testing Framework** - How to invoke and test CLI commands
2. **Part 2: Output Design** - How to structure CLI output for testability (optional, separate decision)

---

## Why Typer?

Typer (built on Click) provides the industry-standard approach to CLI testing:

| Feature | argparse + test_args | Typer + CliRunner |
|---------|---------------------|-------------------|
| stdout/stderr capture | Manual (capsys) | Built-in |
| Exit code testing | Manual | Built-in |
| Filesystem isolation | Manual fixture | Built-in |
| Interactive input | Manual mock | Built-in |
| Modify production code | Yes (add test_args) | No |
| Industry adoption | Legacy projects | Modern standard |

**If you're starting a new CLI project, use Typer.** The testing story is dramatically better.

---

# Part 1: Testing Framework

This section covers how to invoke and test CLI commands. It is independent of how you design your CLI's output.

## The CliRunner Pattern

Typer's `CliRunner` invokes your CLI in an isolated environment and captures all output:

```python
from typer.testing import CliRunner
from myapp.cli import app

runner = CliRunner()

def test_basic_command():
    result = runner.invoke(app, ["fasta", "digest", "genome.fa"])

    assert result.exit_code == 0
    assert "digest" in result.stdout
    assert result.stderr == ""  # No errors
```

### What CliRunner Provides

- `result.exit_code` - The integer exit code
- `result.stdout` - Captured standard output
- `result.stderr` - Captured standard error (if `mix_stderr=False`)
- `result.output` - Combined stdout (default, stderr mixed in)
- `result.exception` - Any unhandled exception

---

## Basic Test Structure

### conftest.py

```python
# tests/conftest.py

import pytest
from pathlib import Path
from typer.testing import CliRunner

from myapp.cli import app

# ============================================================
# CLI Runner Fixture
# ============================================================

@pytest.fixture
def runner():
    """Typer CLI test runner."""
    return CliRunner()

@pytest.fixture
def cli(runner):
    """Convenience fixture that returns invoke function."""
    def invoke(*args):
        return runner.invoke(app, list(args))
    return invoke

# ============================================================
# Test Data Fixtures
# ============================================================

@pytest.fixture
def temp_dir(tmp_path):
    """Temporary directory for test files."""
    return tmp_path

@pytest.fixture
def sample_fasta(temp_dir):
    """Create a sample FASTA file."""
    fasta = temp_dir / "sample.fa"
    fasta.write_text(">chr1\nACGTACGT\n>chr2\nGGCCGGCC\n")
    return fasta

@pytest.fixture
def sample_config(temp_dir):
    """Create a sample config file."""
    config = temp_dir / "config.toml"
    config.write_text('[store]\npath = "/tmp/store"\n')
    return config
```

### Test File

```python
# tests/test_cli.py

class TestFastaDigest:
    """Tests for: myapp fasta digest <file>"""

    def test_digest_success(self, cli, sample_fasta):
        """Compute digest of valid FASTA."""
        result = cli("fasta", "digest", str(sample_fasta))

        assert result.exit_code == 0
        assert "digest" in result.stdout

    def test_digest_file_not_found(self, cli):
        """Error on missing file."""
        result = cli("fasta", "digest", "/nonexistent.fa")

        assert result.exit_code != 0
        assert "not found" in result.stdout.lower() or result.exception

    def test_digest_missing_argument(self, cli):
        """Error when file argument missing."""
        result = cli("fasta", "digest")

        assert result.exit_code != 0
        assert "Missing argument" in result.stdout
```

---

## Testing Exit Codes

Typer commands should use `raise typer.Exit(code)` for non-zero exits:

```python
# In CLI implementation
@app.command()
def digest(file: Path):
    if not file.exists():
        typer.echo(f"Error: File not found: {file}", err=True)
        raise typer.Exit(2)
    # ... rest of command
```

```python
# In tests
def test_exit_codes(cli):
    # Success
    result = cli("fasta", "digest", "valid.fa")
    assert result.exit_code == 0

    # File not found
    result = cli("fasta", "digest", "/missing.fa")
    assert result.exit_code == 2

    # General error
    result = cli("fasta", "digest", "corrupt.fa")
    assert result.exit_code == 1
```

---

## Testing stdout and stderr

### Separate stdout and stderr

```python
def test_output_streams(runner, sample_fasta):
    # By default, stderr is mixed into stdout
    result = runner.invoke(app, ["fasta", "digest", str(sample_fasta)])
    assert "digest" in result.output  # stdout + stderr combined

    # To separate them:
    result = runner.invoke(
        app,
        ["fasta", "digest", str(sample_fasta)],
        mix_stderr=False
    )
    assert "digest" in result.stdout
    assert result.stderr == ""
```

### Testing error messages

```python
def test_error_message(cli):
    result = cli("fasta", "digest", "/missing.fa")

    assert result.exit_code == 2
    assert "File not found" in result.stdout or "Error" in result.stdout
```

---

## Testing with Environment Variables

```python
def test_with_env_var(runner, monkeypatch):
    """Test CLI respects environment variables."""
    monkeypatch.setenv("REFGET_STORE_PATH", "/custom/store")

    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    assert "/custom/store" in result.stdout
```

---

## Testing with Isolated Filesystem

CliRunner provides `isolated_filesystem()` for tests that create/modify files:

```python
def test_file_creation(runner):
    """Test command that creates files."""
    with runner.isolated_filesystem():
        # Create input file
        Path("input.fa").write_text(">chr1\nACGT\n")

        # Run command that creates output
        result = runner.invoke(app, ["fasta", "index", "input.fa"])

        assert result.exit_code == 0
        assert Path("input.fa.fai").exists()
        assert Path("input.seqcol.json").exists()
```

Or use the fixture approach:

```python
@pytest.fixture
def isolated_fs(runner, monkeypatch, tmp_path):
    """Isolate test in temporary directory."""
    monkeypatch.chdir(tmp_path)
    return tmp_path

def test_relative_paths(cli, isolated_fs):
    """Test with relative paths."""
    (isolated_fs / "genome.fa").write_text(">chr1\nACGT\n")

    result = cli("fasta", "digest", "genome.fa")  # Relative path
    assert result.exit_code == 0
```

---

## Testing Interactive Prompts

Typer prompts can be tested by providing input:

```python
def test_interactive_config(runner):
    """Test interactive configuration wizard."""
    result = runner.invoke(
        app,
        ["config", "init"],
        input="~/.refget/store\nhttps://seqcolapi.databio.org\n"
    )

    assert result.exit_code == 0
    assert "Configuration saved" in result.stdout
```

For confirmation prompts:

```python
def test_confirm_delete(runner):
    """Test delete confirmation."""
    # User confirms
    result = runner.invoke(app, ["store", "delete"], input="y\n")
    assert result.exit_code == 0

    # User declines
    result = runner.invoke(app, ["store", "delete"], input="n\n")
    assert result.exit_code == 1
    assert "Aborted" in result.stdout
```

---

## Testing Help Output

```python
class TestHelpOutput:
    """Verify help text is correct."""

    def test_main_help(self, cli):
        result = cli("--help")

        assert result.exit_code == 0
        assert "Usage:" in result.stdout
        assert "fasta" in result.stdout
        assert "store" in result.stdout
        assert "seqcol" in result.stdout

    def test_subcommand_help(self, cli):
        result = cli("fasta", "--help")

        assert result.exit_code == 0
        assert "digest" in result.stdout
        assert "seqcol" in result.stdout

    def test_command_help(self, cli):
        result = cli("fasta", "digest", "--help")

        assert result.exit_code == 0
        assert "FILE" in result.stdout  # Argument shown
```

---

## Testing Version

```python
def test_version(cli):
    result = cli("--version")

    assert result.exit_code == 0
    assert "0.1.0" in result.stdout  # Or use regex for semver
```

---

## E2E Tests with Subprocess

For smoke tests that verify the installed package works:

```python
# tests/e2e/test_installed.py

import subprocess
import pytest
import os

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_E2E_TESTS"),
    reason="E2E tests disabled (set RUN_E2E_TESTS=1)"
)

def test_cli_installed():
    """Verify CLI is installed and responds."""
    result = subprocess.run(
        ["refget", "--help"],
        capture_output=True,
        text=True,
        timeout=30
    )
    assert result.returncode == 0
    assert "Usage:" in result.stdout

def test_cli_version():
    """Verify version command works."""
    result = subprocess.run(
        ["refget", "--version"],
        capture_output=True,
        text=True,
        timeout=10
    )
    assert result.returncode == 0
```

---

## Complete Test Example

```python
# tests/test_fasta_commands.py

import json
import pytest
from pathlib import Path
from typer.testing import CliRunner

from refget.cli import app

runner = CliRunner()

class TestFastaDigest:
    """Tests for: refget fasta digest <file>"""

    def test_digest_basic(self, sample_fasta):
        result = runner.invoke(app, ["fasta", "digest", str(sample_fasta)])

        assert result.exit_code == 0
        # Output is JSON
        output = json.loads(result.stdout)
        assert "digest" in output
        assert output["file"] == str(sample_fasta)

    def test_digest_gzipped(self, sample_fasta_gz):
        """Gzipped files work seamlessly."""
        result = runner.invoke(app, ["fasta", "digest", str(sample_fasta_gz)])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert "digest" in output

    def test_digest_not_found(self):
        result = runner.invoke(app, ["fasta", "digest", "/no/such/file.fa"])

        assert result.exit_code == 2
        assert "not found" in result.stdout.lower()

    def test_digest_no_args(self):
        result = runner.invoke(app, ["fasta", "digest"])

        assert result.exit_code != 0
        assert "Missing argument" in result.stdout


class TestFastaSeqcol:
    """Tests for: refget fasta seqcol <file>"""

    def test_seqcol_stdout(self, sample_fasta):
        """Output to stdout by default."""
        result = runner.invoke(app, ["fasta", "seqcol", str(sample_fasta)])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert "names" in output
        assert "lengths" in output
        assert "sequences" in output

    def test_seqcol_to_file(self, sample_fasta, tmp_path):
        """Write to file with -o."""
        outfile = tmp_path / "out.seqcol.json"

        result = runner.invoke(app, [
            "fasta", "seqcol", str(sample_fasta),
            "-o", str(outfile)
        ])

        assert result.exit_code == 0
        assert outfile.exists()
        output = json.loads(outfile.read_text())
        assert "names" in output


class TestFastaIndex:
    """Tests for: refget fasta index <file>"""

    def test_index_creates_all_files(self, tmp_path):
        """Index creates .fai, .seqcol.json, .chrom.sizes."""
        fasta = tmp_path / "genome.fa"
        fasta.write_text(">chr1\nACGT\n>chr2\nGGCC\n")

        result = runner.invoke(app, ["fasta", "index", str(fasta)])

        assert result.exit_code == 0
        assert (tmp_path / "genome.fa.fai").exists()
        assert (tmp_path / "genome.seqcol.json").exists()
        assert (tmp_path / "genome.chrom.sizes").exists()

        # Digest printed to stdout
        assert len(result.stdout.strip()) > 0


class TestConfigCommands:
    """Tests for: refget config *"""

    def test_config_show(self, monkeypatch, tmp_path):
        """Show configuration."""
        config = tmp_path / "config.toml"
        config.write_text('[store]\npath = "/test/store"\n')
        monkeypatch.setenv("REFGET_CONFIG", str(config))

        result = runner.invoke(app, ["config", "show"])

        assert result.exit_code == 0
        assert "/test/store" in result.stdout

    def test_config_init_interactive(self):
        """Interactive config setup."""
        result = runner.invoke(
            app,
            ["config", "init"],
            input="~/.refget/store\nhttps://seqcolapi.databio.org\n\n"
        )

        assert result.exit_code == 0
        assert "saved" in result.stdout.lower()
```

---

# Part 2: Architecture - Library + CLI Separation

The CLI is a **thin wrapper** around a Python library. This separation of concerns means:

1. **Library functions** return structured data, raise exceptions
2. **CLI commands** call library functions, format output, set exit codes

```
┌─────────────────────────────────────────┐
│  CLI Layer (thin wrapper)               │
│  - Parses args (Typer handles this)     │
│  - Calls library functions              │
│  - Formats output (JSON, plain, etc.)   │
│  - Sets exit codes                      │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│  Library/API Layer                      │
│  - Functions return structured data     │
│  - Raises exceptions for errors         │
│  - No printing, no exit codes           │
│  - Usable without CLI                   │
└─────────────────────────────────────────┘
```

---

## The Correct Pattern

### Library Layer (no CLI concerns)

```python
# refget/processing/fasta.py

from pathlib import Path

def compute_digest(file: Path) -> dict:
    """
    Compute seqcol digest of a FASTA file.

    Returns structured data. No printing. Raises on error.

    Returns:
        dict with keys: digest, file, sequences, total_length
    """
    if not file.exists():
        raise FileNotFoundError(f"{file}")

    # Do the actual computation
    digest = _do_computation(file)

    return {
        "digest": digest,
        "file": str(file),
        "sequences": 25,
        "total_length": 3_000_000_000,
    }


def compute_seqcol(file: Path) -> dict:
    """Compute full seqcol JSON from FASTA."""
    if not file.exists():
        raise FileNotFoundError(f"{file}")

    return {
        "names": ["chr1", "chr2"],
        "lengths": [1000, 2000],
        "sequences": ["SQ.abc", "SQ.def"],
    }
```

### CLI Layer (thin wrapper)

```python
# refget/cli/fasta.py

import json
import typer
from pathlib import Path

from refget.processing.fasta import compute_digest, compute_seqcol

app = typer.Typer()

@app.command()
def digest(file: Path):
    """Compute seqcol digest of a FASTA file."""
    try:
        result = compute_digest(file)       # Call library function
        typer.echo(json.dumps(result, indent=2))  # Format for output
    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(2)


@app.command()
def seqcol(
    file: Path,
    output: Path = typer.Option(None, "-o", "--output"),
):
    """Compute full seqcol JSON from FASTA."""
    try:
        result = compute_seqcol(file)       # Call library function

        # Format output based on user request
        json_str = json.dumps(result, indent=2)
        if output:
            output.write_text(json_str)
            typer.echo(f"Written to {output}")
        else:
            typer.echo(json_str)

    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(2)
```

---

## Testing at Two Levels

### 1. Test Library Functions Directly (fast, focused)

```python
# tests/test_processing.py

import pytest
from pathlib import Path
from refget.processing.fasta import compute_digest, compute_seqcol


class TestComputeDigest:
    """Test library function directly."""

    def test_returns_structured_data(self, sample_fasta):
        result = compute_digest(sample_fasta)

        assert "digest" in result
        assert "file" in result
        assert "sequences" in result
        assert result["digest"].startswith("SQ.")

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            compute_digest(Path("/no/such/file.fa"))

    def test_gzipped_file(self, sample_fasta_gz):
        result = compute_digest(sample_fasta_gz)
        assert "digest" in result
```

### 2. Test CLI Wrapper (verifies formatting, exit codes)

```python
# tests/test_cli.py

from typer.testing import CliRunner
from refget.cli import app
import json

runner = CliRunner()


class TestFastaDigestCLI:
    """Test CLI wrapper behavior."""

    def test_outputs_json(self, sample_fasta):
        result = runner.invoke(app, ["fasta", "digest", str(sample_fasta)])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert "digest" in output

    def test_exit_code_on_missing_file(self):
        result = runner.invoke(app, ["fasta", "digest", "/missing.fa"])

        assert result.exit_code == 2
        assert "Error" in result.stdout

    def test_help_text(self):
        result = runner.invoke(app, ["fasta", "digest", "--help"])

        assert result.exit_code == 0
        assert "FASTA" in result.stdout
```

---

## Benefits of This Architecture

### 1. Library is independently usable

```python
# Users can use without CLI
from refget.processing.fasta import compute_digest

result = compute_digest(Path("genome.fa"))
print(result["digest"])
```

### 2. Clear separation of concerns

- Library: **what** to compute
- CLI: **how** to present it

### 3. Easier testing

- Library tests are fast, don't need CliRunner
- CLI tests focus on formatting/exit codes

### 4. Flexible output formatting

The CLI layer decides output format. Same library function can support:

```python
@app.command()
def stats(
    file: Path,
    json_output: bool = typer.Option(False, "--json"),
):
    """Display FASTA statistics."""
    result = compute_stats(file)  # Library returns dict

    if json_output:
        typer.echo(json.dumps(result, indent=2))
    else:
        # Human-readable table
        typer.echo(f"Sequences: {result['sequences']}")
        typer.echo(f"Total length: {result['total_length']:,}")
```

---

## Output Format Guidelines

The CLI layer chooses how to format library output:

| Command Type | Output Format | Example |
|-------------|---------------|---------|
| Returns data | JSON | `fasta digest`, `store stats` |
| Creates files | Plain (confirmation) | `fasta index` → "Created genome.fa.fai" |
| Retrieves sequence | Raw text | `store seq` → "ACGTACGT..." |
| Interactive | Plain prompts | `config init` |
| Errors | Plain to stderr | "Error: File not found" |

---

## Exception → Exit Code Mapping

```python
# In CLI layer, map exceptions to exit codes

EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_FILE_NOT_FOUND = 2
EXIT_INVALID_INPUT = 3

@app.command()
def digest(file: Path):
    try:
        result = compute_digest(file)
        typer.echo(json.dumps(result, indent=2))
    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(EXIT_FILE_NOT_FOUND)
    except ValueError as e:
        typer.echo(f"Invalid input: {e}", err=True)
        raise typer.Exit(EXIT_INVALID_INPUT)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(EXIT_ERROR)
```

---

## Summary

### Part 1: Testing (Use CliRunner)

```python
from typer.testing import CliRunner
runner = CliRunner()

result = runner.invoke(app, ["command", "arg", "--option", "value"])
assert result.exit_code == 0
assert "expected" in result.stdout
```

**Key features:**
- Captures stdout/stderr automatically
- Tests exit codes
- Supports isolated filesystem
- Handles interactive input
- No modification to production code

### Part 2: Architecture (Library + CLI Separation)

```
Library Layer              CLI Layer
─────────────              ─────────
- Returns dicts            - Calls library functions
- Raises exceptions        - Formats output (JSON, plain)
- No printing              - Sets exit codes
- Usable without CLI       - Thin wrapper only
```

**Test at two levels:**
1. Library functions directly (fast, focused)
2. CLI wrapper with CliRunner (formatting, exit codes)

---

## References

- [Typer Testing Documentation](https://typer.tiangolo.com/tutorial/testing/)
- [Click Testing Documentation](https://click.palletsprojects.com/en/stable/testing/)
- [pytest stdout/stderr capture](https://docs.pytest.org/en/stable/how-to/capture-stdout-stderr.html)
- [Typer main documentation](https://typer.tiangolo.com/)
