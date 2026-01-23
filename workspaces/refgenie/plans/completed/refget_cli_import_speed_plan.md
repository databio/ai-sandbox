# Plan: Improve refget CLI Import Speed

## Goal

Reduce refget CLI startup time from ~367ms to <100ms by implementing lazy imports.

## Problem Analysis

Current import times measured in Docker:
- `import refget`: **367ms** (full package)
- `import gtars.refget`: **2ms** (for comparison)

The import chain analysis shows:
- `typer`: 45ms
- `sqlmodel` (via models.py): **245ms** - THE MAIN CULPRIT
- `requests` (via clients.py): 51ms

The `refget/__init__.py` eagerly imports `models.py`, which imports `sqlmodel`, which imports `sqlalchemy` and `pydantic`. This happens even for CLI commands that don't need database models.

## Files to Read for Context

1. `/home/nsheff/Dropbox/workspaces/refgenie/repos/refget/refget/__init__.py` - Main package init
2. `/home/nsheff/Dropbox/workspaces/refgenie/repos/refget/refget/cli/main.py` - CLI entry point
3. `/home/nsheff/Dropbox/workspaces/refgenie/repos/refget/refget/cli/store.py` - Store commands (most used)
4. `/home/nsheff/Dropbox/workspaces/refgenie/repos/refget/refget/models.py` - Heavy imports here

## Implementation Steps

### Step 1: Create Lightweight CLI Entry Point

Create a new `refget/cli/entry.py` that doesn't import the main `refget` package:

```python
#!/usr/bin/env python3
"""Lightweight CLI entry point that avoids heavy imports."""

def main():
    # Import typer and CLI app only when needed
    from refget.cli.main import app
    app()

if __name__ == "__main__":
    main()
```

### Step 2: Fix Version Import in CLI

In `refget/cli/main.py`, change:
```python
# FROM:
from refget._version import __version__

# TO:
def _get_version():
    """Lazy load version to avoid triggering refget/__init__.py"""
    from refget._version import __version__
    return __version__
```

Or better, read it directly without triggering the package:
```python
import importlib.util
import os

def _get_version():
    spec = importlib.util.spec_from_file_location(
        "_version",
        os.path.join(os.path.dirname(__file__), "..", "_version.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.__version__
```

### Step 3: Lazy Import in CLI Submodules

In each CLI submodule (store.py, fasta.py, etc.), move heavy imports inside functions:

```python
# FROM (at top level):
from refget.models import SequenceCollection
from refget.clients import SequenceCollectionClient

# TO (inside functions that need them):
def some_command():
    from refget.models import SequenceCollection
    # ... use it
```

The `store.py` already does this well with `check_dependency()` and lazy `from refget.processing import RefgetStore`. Apply the same pattern everywhere.

### Step 4: Split refget/__init__.py

Create two levels of API:
1. `refget.core` - Lightweight utilities, clients, digest functions (no sqlmodel)
2. `refget` - Full API including models (for backwards compat, but lazy)

```python
# refget/__init__.py (new version)
"""
Refget package - GA4GH refget implementation.

For fast CLI usage, import specific modules:
    from refget.cli import app
    from refget.clients import SequenceCollectionClient

For full API with database models:
    from refget.models import SequenceCollection
    import refget  # triggers all imports
"""

# Only import lightweight modules eagerly
from .const import *
from .digest_functions import *
from ._version import __version__

# Lazy load heavy modules
def __getattr__(name):
    """Lazy import for heavy modules."""
    if name in ('SequenceCollection', 'FastaDrsObject', 'DrsObject'):
        from .models import SequenceCollection, FastaDrsObject, DrsObject
        globals()[name] = locals()[name]
        return locals()[name]

    if name in ('SequenceClient', 'SequenceCollectionClient', 'FastaDrsClient', 'PangenomeClient'):
        from .clients import SequenceClient, SequenceCollectionClient, FastaDrsClient, PangenomeClient
        globals()[name] = locals()[name]
        return locals()[name]

    if name in ('add_fasta', 'add_fasta_pep', 'add_access_method'):
        from .refget import add_fasta, add_fasta_pep, add_access_method
        globals()[name] = locals()[name]
        return locals()[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

### Step 5: Update pyproject.toml Entry Point

Ensure the CLI entry point uses the lightweight path:

```toml
[project.scripts]
refget = "refget.cli.entry:main"
```

### Step 6: Remove Print Statement

In `refget/__init__.py`, remove or make conditional:
```python
# Remove this - it prints on every import attempt
print(f"Optional dependencies not installed...")
```

Use logging instead, or silence completely for CLI.

## Expected Results

| Before | After |
|--------|-------|
| 367ms | <100ms |

Breakdown:
- typer: 45ms (unavoidable)
- version: ~1ms (direct file read)
- CLI modules: ~20ms (no heavy deps)
- Total: ~66ms

## Verification

After implementation, run:
```bash
time refget --version
time refget store --help
```

Both should complete in <150ms.

## DO NOT MAINTAIN BACKWARDS COMPATIBILITY

This is developmental software. We are optimizing for CLI performance, not for old import patterns. If existing code does `from refget import SequenceCollection`, it will still work (via `__getattr__`), but we're not preserving the exact import timing behavior.

Old patterns that may change:
- `import refget` will no longer trigger all submodule imports
- Side effects in `__init__.py` (like logging.basicConfig) may be deferred

## Summary

The fix is straightforward lazy imports. The main wins come from:
1. Not importing `sqlmodel` (245ms) for CLI commands that don't need it
2. Not importing `requests` (51ms) until a client is actually used
3. Direct version file read instead of triggering package init

After implementation, summarize:
- Before: 367ms import time
- After: Target <100ms
- LoC changes: Minimal - mostly moving imports inside functions
