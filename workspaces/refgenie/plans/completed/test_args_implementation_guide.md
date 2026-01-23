# Test Args Pattern: Comprehensive Implementation Guide

**Status**: Reference documentation

This guide explains the `test_args` pattern for making Python CLI tools testable without subprocess overhead. Based on analysis of looper, markmeld, and geniml implementations.

---

## Problem Statement

### The Challenge of Testing CLIs

Command-line interfaces present unique testing challenges:

1. **Subprocess Overhead**: Running `subprocess.run(["myapp", "cmd", "--flag"])` is slow, requires the package to be installed, and complicates debugging with no direct stack traces.

2. **Output Parsing**: Asserting on stdout/stderr requires string parsing, which is fragile and doesn't provide structured access to results.

3. **Exit Code Limitations**: Exit codes convey limited information (0=success, 1=error), requiring additional mechanisms to understand what happened.

4. **State Isolation**: Each subprocess is isolated, making it difficult to mock dependencies, inject test data, or inspect internal state.

5. **Debugging Difficulty**: When tests fail via subprocess, you lose access to debuggers, coverage tools, and meaningful stack traces.

### The Goal

We want to test CLI tools:
- **Without subprocess**: Call Python functions directly
- **With real argument parsing**: Exercise the actual argparse/click/typer code
- **With structured returns**: Assert on dictionaries, not strings
- **With test isolation**: Use pytest fixtures and mocking normally
- **With full debuggability**: Stack traces, breakpoints, coverage all work

---

## Two Implementation Approaches

Analysis of three codebases revealed two distinct patterns for `test_args`:

### Approach A: List of Strings (Looper Pattern)

`test_args` is a list of strings that exactly mimics `sys.argv[1:]`.

```python
# Production call (sys.argv = ["looper", "run", "--config", "proj.yaml"])
main()  # Parses sys.argv

# Test call
main(test_args=["run", "--config", "proj.yaml", "--dry-run"])
```

**Pros:**
- Exact same argument parsing as production
- Easy to understand - just list the CLI args
- Copy-paste from actual CLI invocations
- Catches argument parsing bugs

**Cons:**
- Still goes through argparse (good for testing, but slightly slower)
- Requires helper functions to build arg lists
- Verbose for complex commands with many options

### Approach B: Dictionary Override (Markmeld/Geniml Pattern)

`test_args` is a dictionary that directly updates the argparse namespace.

```python
# Production call
main()  # Parses sys.argv

# Test call
main(test_args={"config": "proj.yaml", "target": "pdf", "list": True})
```

**Pros:**
- More concise for tests
- Directly sets parsed values
- Can set values argparse might not accept (edge cases)

**Cons:**
- Bypasses argument parsing - won't catch CLI parsing bugs
- Must know argparse destination names (not always CLI flag names)
- Doesn't test argument validation, defaults, or mutual exclusivity

### Recommendation: Use Approach A (List of Strings)

**Approach A is preferred** because it exercises the full argument parsing pipeline. If your argument parser has bugs (wrong defaults, bad validation, missing required args), Approach A catches them; Approach B bypasses them entirely.

---

## Implementation Guide (Approach A)

### Step 1: Modify the Entry Point

**Before:**
```python
def main():
    parser = build_argparser()
    args = parser.parse_args()
    return run_command(args)
```

**After:**
```python
def main(test_args=None):
    """
    Main CLI entry point.

    Args:
        test_args: Optional list of CLI argument strings for testing.
                   If None, uses sys.argv. Example: ["run", "--verbose"]

    Returns:
        Structured result dict for testing assertions.
    """
    parser = build_argparser()

    if test_args is not None:
        args = parser.parse_args(test_args)
    else:
        args = parser.parse_args()

    return run_command(args)
```

**Key changes:**
1. Add `test_args=None` parameter
2. Pass `test_args` to `parser.parse_args()` when provided
3. Return structured data instead of (or in addition to) printing

### Step 2: Return Structured Data

Instead of just printing to stdout, return a dictionary with results:

```python
def run_command(args):
    """Execute the CLI command and return structured results."""

    if args.command == "digest":
        digest = compute_digest(args.file)

        # Print for CLI users
        print(json.dumps({"digest": digest}, indent=2))

        # Return for test assertions
        return {
            "success": True,
            "digest": digest,
            "file": str(args.file),
        }

    elif args.command == "compare":
        result = compare_collections(args.a, args.b)
        print(json.dumps(result, indent=2))
        return {
            "success": True,
            "compatible": result["compatible"],
            "shared": result["shared_sequences"],
        }
```

### Step 3: Create Test Helpers in conftest.py

```python
# tests/conftest.py

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional

from mypackage.cli import main

# ============================================================
# CLI Test Helpers
# ============================================================

def run_cli(*args: str) -> dict:
    """
    Run CLI with given arguments.

    Args:
        *args: CLI arguments as separate strings

    Returns:
        Result dictionary from main()

    Example:
        result = run_cli("fasta", "digest", "genome.fa")
        assert result["digest"] == "abc123..."
    """
    return main(test_args=list(args))


def run_cli_expect_success(*args: str) -> dict:
    """Run CLI and assert success."""
    result = run_cli(*args)
    assert result.get("success", False), f"Expected success: {result}"
    return result


def run_cli_expect_failure(*args: str, exit_code: int = None) -> dict:
    """Run CLI and expect failure."""
    result = run_cli(*args)
    assert not result.get("success", True), "Expected failure"
    if exit_code is not None:
        assert result.get("exit_code") == exit_code
    return result


def run_cli_expect_exit(*args: str):
    """Run CLI and expect SystemExit (argument errors)."""
    with pytest.raises(SystemExit):
        run_cli(*args)


def build_args(
    cmd: str,
    config: Optional[str] = None,
    *extra_args: str,
    dry_run: bool = True
) -> List[str]:
    """
    Build CLI argument list.

    Args:
        cmd: Subcommand name
        config: Optional config file path
        *extra_args: Additional arguments
        dry_run: Whether to add --dry-run flag

    Returns:
        List of argument strings

    Example:
        args = build_args("run", config="proj.yaml", "--limit", "10")
        # Returns: ["run", "--config", "proj.yaml", "--limit", "10", "--dry-run"]
    """
    result = [cmd]
    if config:
        result.extend(["--config", config])
    result.extend(extra_args)
    if dry_run:
        result.append("--dry-run")
    return result


# ============================================================
# File Fixtures
# ============================================================

@pytest.fixture
def temp_dir():
    """Create and cleanup temporary directory."""
    d = tempfile.mkdtemp(prefix="myapp_test_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_file(temp_dir):
    """Create sample test file."""
    f = temp_dir / "sample.txt"
    f.write_text("test content")
    return f
```

### Step 4: Write Tests

```python
# tests/test_cli.py

from conftest import run_cli, run_cli_expect_success, run_cli_expect_exit


class TestDigestCommand:
    """Tests for: myapp digest <file>"""

    def test_digest_basic(self, sample_fasta):
        """Compute digest of file."""
        result = run_cli_expect_success("digest", str(sample_fasta))
        assert "digest" in result
        assert result["digest"].startswith("abc")

    def test_digest_verbose(self, sample_fasta):
        """Digest with verbose output."""
        result = run_cli("digest", str(sample_fasta), "--verbose")
        assert result["success"]
        assert "metadata" in result

    def test_digest_missing_file(self):
        """Error on missing file."""
        result = run_cli("digest", "/nonexistent/file.fa")
        assert not result["success"]
        assert result["exit_code"] == 2

    def test_digest_no_args(self):
        """Error when file argument missing."""
        run_cli_expect_exit("digest")  # Missing required arg


class TestCompareCommand:
    """Tests for: myapp compare <a> <b>"""

    def test_compare_identical(self, sample_fasta):
        """Compare file with itself."""
        result = run_cli_expect_success(
            "compare", str(sample_fasta), str(sample_fasta)
        )
        assert result["compatible"]
        assert result["match"] == "exact"

    def test_compare_different(self, sample_fasta, other_fasta):
        """Compare different files."""
        result = run_cli_expect_success(
            "compare", str(sample_fasta), str(other_fasta)
        )
        assert "compatible" in result
        # May or may not be compatible


class TestWorkflows:
    """Integration tests with multiple commands."""

    def test_digest_then_compare(self, sample_fasta, temp_dir):
        """Workflow: digest file, use digest in compare."""
        # Step 1: Get digest
        result1 = run_cli_expect_success("digest", str(sample_fasta))
        digest = result1["digest"]

        # Step 2: Compare using digest
        result2 = run_cli_expect_success(
            "compare", str(sample_fasta), digest
        )
        assert result2["match"] == "exact"
```

---

## Implementation Guide (Approach B - Dictionary)

If you prefer the dictionary approach (simpler but less thorough):

### Entry Point

```python
def main(test_args=None):
    parser = build_argparser()
    args, _ = parser.parse_known_args()

    # Override with test args if provided
    if test_args:
        args.__dict__.update(test_args)

    return run_command(args)
```

### Tests

```python
def test_digest():
    result = main(test_args={
        "command": "digest",
        "file": "genome.fa",
        "verbose": True,
    })
    assert result["success"]
```

---

## Handling Subcommands

For CLIs with subcommands (like `git commit` or `refget store add`):

### Parser Setup

```python
def build_argparser():
    parser = argparse.ArgumentParser(prog="myapp")
    subparsers = parser.add_subparsers(dest="command")

    # Subcommand: store
    store_parser = subparsers.add_parser("store")
    store_sub = store_parser.add_subparsers(dest="store_command")

    # Subcommand: store add
    add_parser = store_sub.add_parser("add")
    add_parser.add_argument("file")
    add_parser.add_argument("--path", default="~/.myapp/store")

    return parser
```

### Test Calls

```python
# List approach - natural
run_cli("store", "add", "genome.fa", "--path", "/tmp/store")

# Dictionary approach - must know internal names
main(test_args={
    "command": "store",
    "store_command": "add",
    "file": "genome.fa",
    "path": "/tmp/store",
})
```

---

## Exit Codes and Exceptions

### Pattern: Return exit_code in result

```python
def run_command(args):
    try:
        result = do_work(args)
        return {"success": True, "exit_code": 0, **result}
    except FileNotFoundError as e:
        return {"success": False, "exit_code": 2, "error": str(e)}
    except ValueError as e:
        return {"success": False, "exit_code": 1, "error": str(e)}
```

### Pattern: Let exceptions propagate

```python
def run_command(args):
    # Let exceptions bubble up for pytest to catch
    result = do_work(args)
    return {"success": True, **result}

# In tests:
def test_missing_file():
    with pytest.raises(FileNotFoundError):
        run_cli("digest", "/nonexistent.fa")
```

### Pattern: SystemExit for argument errors

Argparse raises `SystemExit` for argument errors. Catch with pytest:

```python
def test_missing_required_arg():
    with pytest.raises(SystemExit):
        run_cli("digest")  # Missing file argument
```

---

## E2E Tests (Subprocess)

For critical paths, also test via subprocess to ensure the installed CLI works:

```python
# tests/e2e/test_installed_cli.py

import subprocess
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_E2E_TESTS"),
    reason="E2E tests disabled"
)

def test_cli_installed():
    """Verify CLI is installed and responds to --help."""
    result = subprocess.run(
        ["myapp", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()

def test_cli_exit_codes():
    """Verify exit codes work correctly."""
    result = subprocess.run(
        ["myapp", "digest", "/nonexistent.fa"],
        capture_output=True
    )
    assert result.returncode == 2  # File not found
```

---

## Complete Example

Here's a complete minimal implementation:

```python
# mypackage/cli.py

import argparse
import json
import sys


def build_argparser():
    parser = argparse.ArgumentParser(
        prog="myapp",
        description="Example CLI with test_args support"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # digest command
    digest = subparsers.add_parser("digest", help="Compute file digest")
    digest.add_argument("file", help="Input file")
    digest.add_argument("-v", "--verbose", action="store_true")

    # compare command
    compare = subparsers.add_parser("compare", help="Compare two items")
    compare.add_argument("a", help="First item")
    compare.add_argument("b", help="Second item")

    return parser


def main(test_args=None):
    """
    Main entry point.

    Args:
        test_args: Optional list of CLI args for testing.
                   Example: ["digest", "file.txt", "--verbose"]

    Returns:
        Dict with structured results for test assertions.
    """
    parser = build_argparser()

    try:
        if test_args is not None:
            args = parser.parse_args(test_args)
        else:
            args = parser.parse_args()
    except SystemExit:
        raise  # Let argparse errors propagate

    # Dispatch to command handlers
    if args.command == "digest":
        return handle_digest(args)
    elif args.command == "compare":
        return handle_compare(args)
    else:
        return {"success": False, "error": f"Unknown command: {args.command}"}


def handle_digest(args):
    """Handle digest command."""
    try:
        # Compute digest (placeholder)
        digest = f"digest_of_{args.file}"

        result = {
            "success": True,
            "digest": digest,
            "file": args.file,
        }

        if args.verbose:
            result["metadata"] = {"size": 12345}

        # Print JSON for CLI users
        print(json.dumps(result, indent=2))
        return result

    except FileNotFoundError:
        result = {
            "success": False,
            "exit_code": 2,
            "error": f"File not found: {args.file}",
        }
        print(json.dumps(result, indent=2), file=sys.stderr)
        return result


def handle_compare(args):
    """Handle compare command."""
    result = {
        "success": True,
        "a": args.a,
        "b": args.b,
        "compatible": args.a == args.b,
        "match": "exact" if args.a == args.b else "different",
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result.get("success") else result.get("exit_code", 1))
```

---

## Summary

| Aspect | Approach A (List) | Approach B (Dict) |
|--------|-------------------|-------------------|
| Implementation | `parser.parse_args(test_args)` | `args.__dict__.update(test_args)` |
| Test call | `main(["cmd", "--flag"])` | `main({"command": "cmd", "flag": True})` |
| Argument validation | ✅ Tested | ❌ Bypassed |
| Default values | ✅ From argparse | ⚠️ Must specify |
| Mutual exclusivity | ✅ Tested | ❌ Bypassed |
| Natural CLI syntax | ✅ Yes | ❌ Need arg names |
| Production repos | looper | markmeld, geniml |

**Recommendation**: Use Approach A (list of strings) for thorough testing of the actual CLI interface.

---

## References

- Looper: `/home/nsheff/code/looper/looper/cli_pydantic.py` - list-based test_args
- Markmeld: `/repos/sciquill/markmeld/markmeld/cli.py` - dict-based test_args
- Geniml: `/repos/geniml_dev/geniml/cli.py` - dict-based test_args
- pytest argparse testing: https://docs.pytest.org/en/stable/
