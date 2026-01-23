# Implementation plan for CLI Code Review Fixes

## The issue

The refget Typer CLI migration introduced several code quality issues identified during code review:

1. **Import ordering violation** in `store.py` - imports placed after function/enum definitions
2. **Inconsistent error output** in `fasta.py` - `digest()` outputs JSON error to stdout while all other commands use `print_error()` to stderr
3. **Loop bug** in `seqcol.py` - `validate()` function only shows first error due to early exit
4. **Unused import** in test file - `DIFFERENT_ORDER_FASTA` imported but never used
5. **Minor: Fragile file extension handling** in `fasta.py` - case-sensitive extension matching

## Files to read for context

- `refget/cli/store.py` - Import ordering issue
- `refget/cli/fasta.py` - Error output inconsistency and extension handling
- `refget/cli/seqcol.py` - Loop bug in validate()
- `refget/cli/output.py` - Error output utilities (reference)
- `tests/test_cli/test_fasta_commands.py` - Unused import

## Implementation Steps

### Step 1: Fix import ordering in store.py

**File:** `refget/cli/store.py`

Move the imports at lines 47-56 to the top of the file, after the standard library imports and before the `StorageModeChoice` enum definition.

Current structure (wrong):
```python
import os
import tempfile
...

class StorageModeChoice(str, Enum):
    ...

@contextmanager
def _temp_file_path(...):
    ...

from refget.cli.config_manager import get_store_path  # Line 47
from refget.cli.output import (...)  # Lines 48-56
```

Target structure (correct):
```python
import os
import tempfile
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Iterator, List, Optional

import typer

from refget.cli.config_manager import get_store_path
from refget.cli.output import (
    EXIT_FILE_NOT_FOUND,
    EXIT_FAILURE,
    EXIT_SUCCESS,
    check_dependency,
    not_implemented,
    print_error,
    print_json,
)


class StorageModeChoice(str, Enum):
    ...
```

### Step 2: Fix inconsistent error output in fasta.py digest()

**File:** `refget/cli/fasta.py`, lines 160-163

Change from outputting JSON error to stdout:
```python
if not file.exists():
    print(json.dumps({"error": f"File not found: {file}"}))
    raise typer.Exit(EXIT_FILE_NOT_FOUND)
```

To using the standard error output pattern:
```python
if not file.exists():
    print_error(f"File not found: {file}", EXIT_FILE_NOT_FOUND)
```

This matches the pattern used everywhere else in the CLI and sends errors to stderr where they belong.

### Step 3: Fix loop bug in seqcol.py validate()

**File:** `refget/cli/seqcol.py`, lines 555-558

Current (buggy - only shows first error):
```python
if errors:
    for error in errors:
        print_error(error, EXIT_FAILURE)  # Exits immediately
    return  # Never reached
```

Fixed (shows all errors, then exits):
```python
if errors:
    for error in errors:
        print_error(error)  # No exit code - just prints
    raise typer.Exit(EXIT_FAILURE)
```

### Step 4: Remove unused import in test file

**File:** `tests/test_cli/test_fasta_commands.py`, lines 16-23

Remove `DIFFERENT_ORDER_FASTA` from the import statement:

```python
from conftest import (
    BASE_FASTA,
    DIFFERENT_NAMES_FASTA,
    # DIFFERENT_ORDER_FASTA removed - unused
    TEST_FASTA_DIGESTS,
    assert_json_output,
    assert_valid_digest,
)
```

### Step 5: (Optional) Improve file extension handling in fasta.py

**File:** `refget/cli/fasta.py`, lines 111-117

Current (case-sensitive, fragile):
```python
seqcol_path = out_dir / f"{base_name.replace('.fa', '.seqcol.json').replace('.fasta', '.seqcol.json')}"
if base_name.endswith(".gz"):
    seqcol_path = out_dir / f"{base_name[:-3].replace('.fa', '.seqcol.json')..."
```

Improved (use Path.stem properly):
```python
# Strip .gz suffix if present
name_without_gz = base_name[:-3] if base_name.lower().endswith(".gz") else base_name

# Extract stem (filename without final extension)
if name_without_gz.lower().endswith(".fasta"):
    stem = name_without_gz[:-6]
elif name_without_gz.lower().endswith(".fa"):
    stem = name_without_gz[:-3]
else:
    stem = Path(name_without_gz).stem

seqcol_path = out_dir / f"{stem}.seqcol.json"
chrom_sizes_path = out_dir / f"{stem}.chrom.sizes"
```

This handles case variations like `.FA.GZ` correctly.

### Step 6: Run tests to verify fixes

```bash
cd /home/nsheff/Dropbox/workspaces/refgenie/repos/refget
pytest tests/test_cli/ -v
```

All existing tests should pass. The changes are behavioral improvements that shouldn't break any tests.

## Backwards compatibility

This is developmental software. We are trying to eliminate old code, not keep it around.

The only user-visible change is that `refget fasta digest` will now output errors to stderr instead of stdout. This is actually the correct Unix behavior and scripts that were parsing JSON errors from stdout were relying on incorrect behavior.

## Cleanup

Once completed, move the completed plan to the `/home/nsheff/Dropbox/workspaces/refgenie/plans/completed/` subfolder.
