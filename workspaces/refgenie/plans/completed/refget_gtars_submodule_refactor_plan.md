# Refget gtars Submodule Refactor Plan

## Goal

Refactor the `refget` Python package to separate gtars-dependent functionality into a dedicated submodule. This provides automatic protection against unguarded gtars imports - any code added to the submodule inherits the gtars requirement automatically.

## Problem

Currently, gtars-dependent code is scattered across multiple files with inconsistent protection:
- Some files use `GTARS_INSTALLED` checks
- Some use try/except guards
- Some have unguarded imports that will crash if gtars isn't installed
- It's easy to accidentally add unprotected gtars imports

The refget package has two distinct use cases:
1. **Client functionality** - querying remote servers, comparing collections - NO gtars needed
2. **Heavy lifting** - FASTA processing, digest computation, RefgetStore - gtars required

## Proposed Submodule Name: `processing`

After considering options:
- `gtars_required` - too implementation-specific
- `fasta` - too narrow (also includes RefgetStore, digests)
- `local` - unclear
- `compute` - good but generic
- **`processing`** - captures FASTA processing, digest computation, local store operations

The name `processing` clearly indicates "this is where the heavy computation happens" vs the client-side operations.

## Files to Read for Context

1. `/home/nsheff/Dropbox/workspaces/refgenie/repos/refget/refget/__init__.py` - current public API
2. `/home/nsheff/Dropbox/workspaces/refgenie/repos/refget/refget/const.py` - GTARS_INSTALLED flag
3. `/home/nsheff/Dropbox/workspaces/refgenie/repos/refget/refget/refget_store.py` - current gtars wrapper
4. `/home/nsheff/Dropbox/workspaces/refgenie/repos/refget/refget/digest_functions.py` - hybrid gtars/python digests
5. `/home/nsheff/Dropbox/workspaces/refgenie/repos/refget/refget/models.py` - FastaDrsObject.from_fasta_file(), from_PySequenceCollection()

## Current gtars Usage Analysis

| File | gtars Usage | Should Move to `processing/`? |
|------|-------------|-------------------------------|
| `refget_store.py` | RefgetStore, StorageMode, RetrievedSequence | YES - entire file |
| `digest_functions.py` | sha512t24u_digest, md5_digest, digest_fasta | PARTIAL - gtars versions only |
| `models.py` | FastaDrsObject.from_fasta_file(), from_PySequenceCollection() | PARTIAL - these methods only |
| `utilities.py` | fasta_to_digest(), fasta_to_seqcol_dict() | YES - these already use gtars! |
| `clients.py` | download_to_store (uses RefgetStore) | NO - keep in clients, it already guards |

**Key Discovery:** `fasta_to_digest()` and `fasta_to_seqcol_dict()` in utilities.py are NOT pure Python - they already call `fasta_to_seq_digests` which is `gtars.digest_fasta`. There is no Python FASTA parsing code to preserve.

## What Stays vs What Moves

**Stays in root (pure Python, no gtars needed):**
- `utilities.py`: `canonical_str()`, `compare_seqcols()`, `seqcol_digest()`, `validate_seqcol()`, etc.
- `digest_functions.py`: `py_sha512t24u_digest()`, `py_md5_digest()` (fallbacks for client-side verification)
- `clients.py`: All client classes (HTTP requests only)
- `models.py`: Data structures (except factory methods that process FASTA)

**Moves to `processing/`:**
- `fasta_to_digest()`, `fasta_to_seqcol_dict()` from utilities.py
- `fasta_to_seq_digests` alias from digest_functions.py
- RefgetStore wrapper from refget_store.py
- `FastaDrsObject.from_fasta_file()` logic from models.py
- `SequenceCollection.from_PySequenceCollection()` logic from models.py

## Implementation Steps

### Step 1: Create the `processing` submodule structure

```
refget/
  processing/
    __init__.py      # Gate + public exports
    store.py         # RefgetStore wrapper (moved from refget_store.py)
    digest.py        # gtars digest functions
    fasta.py         # FastaDrsObject.from_fasta_file() and related
    bridge.py        # from_PySequenceCollection() and gtars↔python conversions
```

### Step 2: Create `refget/processing/__init__.py` with the gate

```python
"""
Processing submodule - requires gtars for FASTA processing, digest computation,
and local RefgetStore operations.

This submodule will raise ImportError immediately if gtars is not installed.
"""
from ..const import GTARS_INSTALLED

if not GTARS_INSTALLED:
    raise ImportError(
        "The refget.processing module requires gtars. "
        "Install with: pip install gtars"
    )

# Only reached if gtars is available
from .store import RefgetStore, StorageMode, RetrievedSequence
from .digest import sha512t24u_digest, md5_digest, digest_fasta
from .fasta import fasta_to_digest, fasta_to_seqcol_dict, create_fasta_drs_object
from .bridge import seqcol_from_gtars
```

### Step 3: Create `refget/processing/store.py`

Move contents from `refget_store.py` but without the GTARS_INSTALLED guard (the `__init__.py` handles it):

```python
"""RefgetStore wrapper - gtars is guaranteed available in this submodule."""
from gtars.refget import RefgetStore, StorageMode, RetrievedSequence

__all__ = ["RefgetStore", "StorageMode", "RetrievedSequence"]
```

### Step 4: Create `refget/processing/digest.py`

```python
"""Digest functions using gtars (fast Rust implementation)."""
from gtars.refget import (
    sha512t24u_digest,
    md5_digest,
    digest_fasta,
)

__all__ = ["sha512t24u_digest", "md5_digest", "digest_fasta"]
```

### Step 5: Create `refget/processing/fasta.py`

Move FASTA processing functions here:

```python
"""FASTA processing functions using gtars."""
import os
import hashlib
from datetime import datetime, timezone
from gtars.refget import digest_fasta

from .digest import sha512t24u_digest


def fasta_to_seqcol_dict(fasta_file_path: str) -> dict:
    """
    Convert a FASTA file into a Sequence Collection dict.
    Moved from utilities.py - this already used gtars.
    """
    from ..utilities import canonical_str  # Pure Python, stays in utilities

    fasta_seq_digests = digest_fasta(fasta_file_path)
    seqcol_dict = {
        "lengths": [],
        "names": [],
        "sequences": [],
        "sorted_name_length_pairs": [],
        "sorted_sequences": [],
    }
    for s in fasta_seq_digests.sequences:
        seq_name = s.metadata.name
        seq_length = s.metadata.length
        seq_digest = "SQ." + s.metadata.sha512t24u
        nlp = {"length": seq_length, "name": seq_name}
        snlp_digest = sha512t24u_digest(canonical_str(nlp))
        seqcol_dict["lengths"].append(seq_length)
        seqcol_dict["names"].append(seq_name)
        seqcol_dict["sorted_name_length_pairs"].append(snlp_digest)
        seqcol_dict["sequences"].append(seq_digest)
        seqcol_dict["sorted_sequences"].append(seq_digest)
    seqcol_dict["sorted_name_length_pairs"].sort()
    return seqcol_dict


def fasta_to_digest(fasta_file_path: str, inherent_attrs: list = None) -> str:
    """
    Given a FASTA file path, return its seqcol digest.
    Moved from utilities.py - this already used gtars.
    """
    from ..utilities import seqcol_digest  # Pure Python, stays in utilities
    from ..const import DEFAULT_INHERENT_ATTRS

    if inherent_attrs is None:
        inherent_attrs = DEFAULT_INHERENT_ATTRS
    seqcol_obj = fasta_to_seqcol_dict(fasta_file_path)
    return seqcol_digest(seqcol_obj, inherent_attrs)


def create_fasta_drs_object(fasta_file: str, digest: str = None):
    """
    Create a FastaDrsObject from a FASTA file.
    Moved from FastaDrsObject.from_fasta_file()
    """
    # ... implementation moved from FastaDrsObject.from_fasta_file()


__all__ = ["fasta_to_seqcol_dict", "fasta_to_digest", "create_fasta_drs_object"]
```

### Step 6: Create `refget/processing/bridge.py`

Move `SequenceCollection.from_PySequenceCollection()` logic here:

```python
"""Bridge functions between gtars types and refget Python types."""
from gtars.refget import SequenceCollection as GtarsSequenceCollection

def seqcol_from_gtars(gtars_seq_col: GtarsSequenceCollection):
    """Convert a gtars SequenceCollection to a refget SequenceCollection."""
    # ... implementation moved from SequenceCollection.from_PySequenceCollection()
```

### Step 7: Update `refget/utilities.py`

Remove `fasta_to_digest()` and `fasta_to_seqcol_dict()` - they moved to `processing/fasta.py`.

Delete these functions entirely (lines ~94-150). Also remove the import of `fasta_to_seq_digests` from the imports at the top.

The remaining functions stay (all pure Python):
- `canonical_str()`, `print_csc()`
- `validate_seqcol()`, `validate_seqcol_bool()`
- `seqcol_digest()`, `seqcol_dict_to_level1_dict()`, `level1_dict_to_seqcol_digest()`
- `compare_seqcols()`, `calc_jaccard_similarities()`
- `build_name_length_pairs()`, `build_sorted_name_length_pairs()`
- etc.

### Step 8: Update `refget/digest_functions.py`

Keep only the pure Python implementations as fallbacks:

```python
"""Digest functions with Python fallbacks."""
import hashlib
import base64
from typing import Callable, Union

from .const import GTARS_INSTALLED

def py_sha512t24u_digest(seq: str | bytes, offset: int = 24) -> str:
    """GA4GH digest function in pure Python (slower fallback)."""
    if isinstance(seq, str):
        seq = seq.encode("utf-8")
    digest = hashlib.sha512(seq).digest()
    tdigest_b64us = base64.urlsafe_b64encode(digest[:offset])
    return tdigest_b64us.decode("ascii")

def py_md5_digest(seq) -> str:
    """MD5 digest function in pure Python."""
    return hashlib.md5(seq.encode()).hexdigest()

# Default exports - use gtars if available, else Python fallback
if GTARS_INSTALLED:
    from .processing.digest import sha512t24u_digest, md5_digest
else:
    sha512t24u_digest = py_sha512t24u_digest
    md5_digest = py_md5_digest

DigestFunction = Callable[[Union[str, bytes]], str]
```

### Step 9: Update `refget/models.py`

Remove gtars-specific methods, delegate to processing submodule:

```python
# In FastaDrsObject class:
@classmethod
def from_fasta_file(cls, fasta_file: str, digest: str = None) -> "FastaDrsObject":
    """Create from FASTA file. Requires gtars."""
    from .processing.fasta import create_fasta_drs_object
    return create_fasta_drs_object(fasta_file, digest)

# In SequenceCollection class:
@classmethod
def from_PySequenceCollection(cls, gtars_seq_col) -> "SequenceCollection":
    """Create from gtars SequenceCollection. Requires gtars."""
    from .processing.bridge import seqcol_from_gtars
    return seqcol_from_gtars(gtars_seq_col)
```

### Step 10: Update `refget/__init__.py`

```python
# Core (no gtars required)
from .clients import SequenceClient, SequenceCollectionClient, PangenomeClient
from .models import SequenceCollection, FastaDrsObject
from .digest_functions import sha512t24u_digest, md5_digest  # Uses gtars if available

# Processing submodule (requires gtars) - users import explicitly:
# from refget.processing import RefgetStore, StorageMode
```

### Step 11: Delete `refget/refget_store.py`

The old file is replaced by `refget/processing/store.py`.

### Step 12: Update imports throughout codebase

Search for and update:
- `from .refget_store import` → `from .processing import`
- `from refget.refget_store import` → `from refget.processing import`
- `from .utilities import fasta_to_digest` → `from .processing import fasta_to_digest`
- `from .utilities import fasta_to_seqcol_dict` → `from .processing import fasta_to_seqcol_dict`

Files that need updating (based on grep):
- `refget/agents.py` - imports `fasta_to_seqcol_dict` from utilities
- `refget/models.py` - imports `fasta_to_seqcol_dict` from utilities
- `refget/refget.py` - imports `fasta_to_digest` from utilities

### Step 13: Run tests and verify

```bash
cd /home/nsheff/Dropbox/workspaces/refgenie/repos/refget
python -m pytest tests/local/ -v
```

## Summary of Changes

**Before:**
- gtars usage scattered across 4+ files
- Inconsistent protection (GTARS_INSTALLED, try/except, unguarded)
- Easy to accidentally add unprotected gtars imports
- ~50 lines of gtars-related boilerplate/guards

**After:**
- All gtars code in `refget/processing/` submodule
- Single gate at submodule import
- New gtars code automatically protected
- Cleaner separation of concerns
- ~30 lines of gtars-related code (gate + re-exports)

## Important Note

**DO NOT MAINTAIN BACKWARDS COMPATIBILITY.** This is developmental software. The goal is to simplify and clean up, not preserve old patterns. Specifically:

- Delete `refget_store.py` entirely (replaced by `processing/store.py`)
- Remove all scattered `GTARS_INSTALLED` guards from individual files
- Remove dummy/stub classes that exist only for graceful degradation
- Users who need gtars functionality must import from `refget.processing`
