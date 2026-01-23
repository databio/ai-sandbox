# Implementation Plan: Refget CLI Consolidation

## The Issue

The refget package has accumulated technical debt in its CLI architecture:

1. **Legacy argparse CLI** (`refget/refget.py`, 531 lines) contains an obsolete CLI alongside wrapper functions that the modern Typer CLI imports
2. **Unnecessary indirection** - The Typer CLI (`cli/admin.py`) imports wrapper functions from `refget.py` instead of using agents directly
3. **Duplicate helpers** - `_check_boto3()` and `load_pep()` exist in both files
4. **Unnecessary public API exports** - `__init__.py` exports `add_fasta`, `add_fasta_pep`, `add_access_method` which are server-side operations that should go through agents

The proper architecture is: **CLI → Agents → Database**

The wrapper functions in `refget.py` are an unnecessary middle layer that should be eliminated.

## Files to Read for Context

1. `refget/refget.py` - Legacy file to delete (531 lines)
2. `refget/cli/admin.py` - Typer CLI to refactor (554 lines)
3. `refget/agents.py` - Database agents (the proper interface)
4. `refget/__init__.py` - Public API exports to clean up
5. `refget/models.py` - AccessMethod, AccessURL models needed for register command
6. `data_loaders/load_demo_seqcols.py` - Example script using legacy functions

## Implementation Steps

### Step 1: Move S3 upload utilities to cli/admin.py

Move these functions from `refget/refget.py` to `refget/cli/admin.py`:

- `_upload_to_s3()` (lines 248-316) - S3 upload logic
- `_check_boto3()` (lines 238-245) - Already duplicated, keep CLI version

The `_upload_to_s3` function is ~70 lines of real S3 logic that the CLI needs.

### Step 2: Refactor `load` command to use agents directly

Current (`cli/admin.py` line 180):
```python
from refget.refget import add_fasta
digest = add_fasta(str(input_file), name=name, dbagent=dbagent)
```

New:
```python
if name:
    seqcol = dbagent.seqcol.add_from_fasta_file_with_name(str(input_file), name, update=True)
else:
    seqcol = dbagent.seqcol.add_from_fasta_file(str(input_file), update=True)
digest = seqcol.digest
```

Also update batch loading (line 197):
```python
# Old: from refget.refget import add_fasta_pep
# New: use dbagent.seqcol.add_from_fasta_pep() or loop with add_from_fasta_file
```

### Step 3: Refactor `register` command to use agents directly

Current (`cli/admin.py` line 284):
```python
from refget.refget import register_fasta
url = register_fasta(digest=digest, fasta_path=str(fasta), ...)
```

New:
```python
from refget.models import AccessMethod, AccessURL

# Upload to S3 (using moved function)
url = _upload_to_s3(str(fasta), bucket, prefix, region=region)

# Register via agent
dbagent.fasta_drs.add_access_method(
    digest=digest,
    access_method=AccessMethod(
        type="s3" if cloud in ("aws", "backblaze") else "https",
        cloud=cloud,
        region=region,
        access_url=AccessURL(url=url),
    ),
)
```

### Step 4: Refactor `ingest` command to use agents directly

Current (`cli/admin.py` lines 410, 432):
```python
from refget.refget import add_fasta
digest = add_fasta(str(fasta), name=name, dbagent=dbagent, storage=storage)
```

New: Combine the load and register logic directly:
```python
# Load metadata
if name:
    seqcol = dbagent.seqcol.add_from_fasta_file_with_name(str(fasta), name, update=True)
else:
    seqcol = dbagent.seqcol.add_from_fasta_file(str(fasta), update=True)
digest = seqcol.digest

# Upload and register
url = _upload_to_s3(str(fasta), bucket, prefix, region=region)
dbagent.fasta_drs.add_access_method(
    digest=digest,
    access_method=AccessMethod(
        type="s3" if cloud in ("aws", "backblaze") else "https",
        cloud=cloud,
        region=region,
        access_url=AccessURL(url=url),
    ),
)
```

### Step 5: Add PEP batch loading helper to cli/admin.py

Move `load_pep()` logic (already exists as `_load_pep` in cli/admin.py, so just keep that).

For batch operations, create a local helper or use agent's `add_from_fasta_pep()` method directly.

### Step 6: Remove exports from `__init__.py`

Delete lines 44-51:
```python
if name in ("add_fasta", "add_fasta_pep", "add_access_method"):
    from .refget import add_fasta, add_fasta_pep, add_access_method
    globals().update({
        "add_fasta": add_fasta,
        "add_fasta_pep": add_fasta_pep,
        "add_access_method": add_access_method,
    })
    return globals()[name]
```

### Step 7: Delete `refget/refget.py`

After all imports are removed, delete the entire file (~531 lines).

### Step 8: Update data_loaders scripts

Update these scripts to use agents directly:
- `data_loaders/load_demo_seqcols.py`
- `data_loaders/load_brickyard_fasta_pep.py`
- `data_loaders/load_pangenome_pep.py`
- `data_loaders/load_ref_fasta_pep.py`

Or delete them if they're no longer needed.

## Verification

1. Run tests:
   ```bash
   cd repos/refget
   pytest
   ```

2. Test CLI commands:
   ```bash
   refget admin --help
   refget admin load --help
   refget admin register --help
   refget admin ingest --help
   refget admin status
   refget admin info
   ```

3. Test imports still work:
   ```python
   from refget import SequenceCollectionClient, SequenceCollection
   from refget.agents import RefgetDBAgent
   ```

4. Verify removed exports raise proper errors:
   ```python
   from refget import add_fasta  # Should raise AttributeError
   ```

## Expected Impact

| Item | Lines |
|------|-------|
| Delete `refget/refget.py` | -531 |
| Move `_upload_to_s3` to cli/admin.py | +70 |
| Remove `__init__.py` exports | -8 |
| Simplify cli/admin.py imports | -20 |
| **Net reduction** | **~490 lines** |

More importantly: cleaner architecture with CLI → Agents → Database.

## Backwards Compatibility

**DO NOT MAINTAIN BACKWARDS COMPATIBILITY.** This is developmental software.

- Remove the public API exports (`add_fasta`, `add_fasta_pep`, `add_access_method`)
- Delete the legacy argparse CLI entirely
- Users should use the Typer CLI or agents directly

## Cleanup

Once completed, move this plan to `plans/completed/refget_cli_consolidation_plan_v1.md`.
