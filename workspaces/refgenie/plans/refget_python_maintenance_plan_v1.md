# Refget Python Package Maintenance Plan

## Goal

Simplify and modernize the `repos/refget/` Python package without removing features. This is developmental software with no need to maintain backwards compatibility. The goal is to reduce technical debt, eliminate redundant code paths, consolidate duplicate patterns, and improve maintainability.

## Context Files to Read Before Implementation

1. `refget/__init__.py` - Entry point with lazy loading
2. `refget/refget.py` - Legacy CLI with argparse (531 lines)
3. `refget/agents.py` - Database agents (938 lines)
4. `refget/clients.py` - API clients (780 lines)
5. `refget/models.py` - SQLModel definitions (638 lines)
6. `refget/utilities.py` - Helper functions (351 lines)
7. `refget/cli/store.py` - Store CLI commands (796 lines)
8. `refget/cli/seqcol.py` - Seqcol CLI commands (671 lines)
9. `refget/cli/fasta.py` - FASTA CLI commands (527 lines)
10. `refget/cli/admin.py` - Admin CLI commands (554 lines)

## Items to Remove Completely

### 1. Delete `build/` directory (~3,500 lines)
The `build/lib/refget/` directory contains stale copies of source files. This is a build artifact that should be gitignored and deleted.

```bash
rm -rf build/
```

### 2. Delete `deprecated/` directory (~245 lines)
Contains dead code that is no longer used:
- `deprecated/agent_updates.py` (66 lines)
- `deprecated/seqcol.py` (178 lines)

```bash
rm -rf deprecated/
```

### 3. Delete `refget/refget.py` legacy CLI (~531 lines)
This file contains an obsolete argparse-based CLI that duplicates the modern Typer CLI. Functions that are still needed (`add_fasta`, `add_fasta_pep`, etc.) should be extracted to a new module, and the CLI should be removed.

### 4. Remove commented-out code in `models.py`
Lines 632-638 contain commented-out `SortedNameLengthPairsAttr` class. Delete these lines.

### 5. Remove dead import in `models.py`
Line 384: `Draft7Validator` is imported but never used (the validation code is incomplete). Remove.

## Specific Simplifications

### Step 1: Extract data loading functions from `refget/refget.py` (Priority: High)

**Current State:** `refget/refget.py` mixes CLI code with useful data loading functions.

**Action:** Create `refget/loaders.py` with these functions extracted from `refget/refget.py`:
- `add_fasta()`
- `add_fasta_pep()`
- `add_access_method()`
- `register_fasta()`
- `register_fasta_pep()`
- `_upload_to_s3()`
- `_check_boto3()`
- `load_pep()`

Then delete `refget/refget.py` entirely (the argparse CLI is obsolete).

Update `refget/__init__.py` to import from the new location.

### Step 2: Consolidate duplicate helper functions (Priority: High)

**Duplications found:**
1. `_check_boto3()` exists in both `refget/refget.py:238` and `refget/cli/admin.py:57`
2. `_load_pep()` / `load_pep()` exists in both `refget/refget.py:109` and `refget/cli/admin.py:66`

**Action:** After Step 1, `cli/admin.py` should import from `refget/loaders.py` instead of duplicating.

### Step 3: Simplify `_ensure_collection_loaded` pattern (Priority: Medium)

**Current State:** `refget/cli/store.py:110-136` has a complex workaround to force lazy-load collections.

**Analysis:** The function uses a loop over `sequence_records()` just to trigger loading, which is inefficient and non-obvious.

**Action:** Either:
1. Add a proper `ensure_loaded(digest)` method to gtars RefgetStore
2. Or simplify by calling `store.get_collection_metadata(digest)` which should trigger loading

### Step 4: Remove redundant comparison function (Priority: Low)

**Current State:** `agents.py` has multiple comparison methods:
- `compare_digests()` (line 837)
- `calc_similarities()` (line 842)
- `calc_similarities_seqcol_dicts()` (line 866)
- `compare_1_digest()` (line 884)

**Action:** Review if all are needed. `compare_digests` and `compare_1_digest` have significant overlap.

### Step 5: Consolidate FAI/chrom-sizes generation (Priority: Medium)

**Current State:** FAI and chrom.sizes generation exists in multiple places:
- `cli/fasta.py` - FASTA file utilities
- `cli/store.py` - Store-based generation
- `clients.py` - Client-side generation (lines 212-278)

**Action:** Consider extracting common FAI/chrom-sizes formatting to `utilities.py` to reduce duplication.

### Step 6: Simplify pangenome code (Priority: Low)

**Current State:** `utilities.py:312-351` contains commented-out `build_pangenome_model` function. The pangenome feature appears incomplete.

**Action:** Either:
1. Delete the commented code entirely
2. Or implement the feature properly

Current line is just `raise NotImplementedError` which wastes space.

### Step 7: Clean up agent list patterns (Priority: Low)

**Current State:** Multiple agents have nearly identical `list_by_offset()` methods:
- `SequenceAgent.list()` (lines 150-161)
- `SequenceCollectionAgent.list_by_offset()` (lines 470-481)
- `PangenomeAgent.list_by_offset()` (lines 626-637)
- `FastaDrsAgent.list_by_offset()` (lines 722-734)

**Action:** Extract a generic `paginated_list()` helper that these can call.

### Step 8: Consolidate stats dictionary handling (Priority: Low)

**Current State:** `cli/store.py:694-716` has complex logic to convert stats object to dict.

**Action:** The stats object should have a `to_dict()` method or consistent structure.

## Implementation Order

1. **Delete build/ and deprecated/ directories** - No code changes needed
2. **Extract loaders from refget.py** - Creates new file, then delete old
3. **Consolidate duplicate helpers** - Import from new location
4. **Remove commented-out code** - Simple deletions
5. **Consolidate FAI/chrom-sizes** - Optional refactor
6. **Clean up agents** - Optional refactor

## Verification Steps

1. **Run existing tests:**
   ```bash
   cd repos/refget
   pytest
   ```
   All tests should pass.

2. **Test CLI commands:**
   ```bash
   refget --help
   refget fasta --help
   refget store --help
   refget seqcol --help
   refget admin --help
   ```

3. **Test critical functions:**
   ```python
   from refget import add_fasta, SequenceCollectionClient
   from refget.processing import RefgetStore, fasta_to_seqcol_dict
   ```

4. **Compare line counts before/after:**
   ```bash
   find . -path './.venv' -prune -o -name '*.py' -type f -print | xargs wc -l | sort -n
   ```

## Expected Impact

| Item | Lines Removed |
|------|---------------|
| build/ directory | ~3,500 |
| deprecated/ directory | ~245 |
| refget/refget.py (after extraction) | ~400 |
| Commented code in models.py | ~10 |
| Duplicate helpers | ~30 |
| **Total** | **~4,185 lines** |

## Important Notes

- **DO NOT MAINTAIN BACKWARDS COMPATIBILITY** - This is developmental software. Old patterns should be replaced, not preserved.
- **DO NOT add new features** - This is maintenance only.
- **DO preserve all existing functionality** - Just reorganize it.

## Summary

After this cleanup:
1. Code will be more discoverable (loaders in one place)
2. Build artifacts won't pollute the source tree
3. Deprecated code won't confuse developers
4. Duplicate helpers will be consolidated
5. Total line count will decrease by ~25-30%

## Baseline File Sizes (Lines of Code)

```
     0 ./seqcolapi/__init__.py
     0 ./tests/api/__init__.py
     0 ./tests/__init__.py
     0 ./tests/local/__init__.py
     1 ./build/lib/refget/_version.py
     1 ./refget/_version.py
     1 ./seqcolapi/_version.py
     1 ./tests/local/conftest.py
     1 ./tests/test_cli/__init__.py
     1 ./tests/test_cli_integration/__init__.py
     4 ./refget/processing/store.py
     7 ./data_loaders/using_looper/add_single_ref_via_looper.py
     8 ./refget/processing/digest.py
     9 ./refget/cli/__init__.py
     9 ./seqcolapi/__main__.py
    10 ./build/lib/refget/exceptions.py
    10 ./refget/exceptions.py
    11 ./scripts/refget_refgenie.py
    15 ./seqcolapi/const.py
    16 ./tests/drc_manual_test.py
    23 ./build/lib/refget/__init__.py
    25 ./data_loaders/compute_pangenome_digests.py
    28 ./data_loaders/load_brickyard_fasta_pep.py
    28 ./data_loaders/load_ref_fasta_pep.py
    31 ./build/lib/refget/refget_store.py
    36 ./refget/processing/__init__.py
    37 ./data_loaders/load_pangenome_pep.py
    43 ./data_loaders/load_demo_sequences.py
    43 ./refget/digest_functions.py
    43 ./tests/local/test_refget_clients.py
    45 ./tests/api/conftest.py
    48 ./data_loaders/demo_build_store.py
    48 ./tests/local/test_digest_functions.py
    55 ./array_overlap.py
    55 ./refget/cli/main.py
    56 ./setup.py
    57 ./tests/test_cli/test_admin_commands.py
    60 ./build/lib/refget/digest_functions.py
    60 ./data_loaders/load_pangenome_reference.py
    62 ./tests/local/test_local_models_gtars.py
    63 ./frontend/node_modules/flatted/python/test.py
    66 ./deprecated/agent_updates.py
    68 ./data_loaders/load_demo_seqcols.py
    69 ./refget/__init__.py
    81 ./create_compliance_answers.py
    85 ./refget/processing/bridge.py
    92 ./tests/test_cli/test_help.py
   103 ./build/lib/refget/refget.py
   134 ./tests/integration/test_cli_admin_integration.py
   138 ./refget/cli/output.py
   141 ./refget/processing/fasta.py
   143 ./seqcolapi/examples.py
   144 ./build/lib/refget/const.py
   149 ./frontend/node_modules/flatted/python/flatted.py
   149 ./tests/integration/test_seqcolapi_client.py
   162 ./refget/const.py
   164 ./data_loaders/demo_remote_store.py
   164 ./tests/integration/conftest.py
   171 ./build/lib/refget/examples.py
   171 ./refget/examples.py
   178 ./deprecated/seqcol.py
   182 ./tests/local/test_local_models.py
   192 ./tests/integration/test_cli_seqcol_integration.py
   193 ./interactive_tests.py
   204 ./seqcolapi/main.py
   216 ./tests/test_cli/test_seqcol_commands.py
   217 ./tests/test_cli/test_config_commands.py
   245 ./tests/conftest.py
   275 ./build/lib/refget/clients.py
   299 ./tests/api/test_compliance.py
   302 ./refget/cli/config_manager.py
   349 ./refget/cli/config.py
   351 ./refget/utilities.py
   362 ./tests/test_cli/test_fasta_commands.py
   382 ./build/lib/refget/utilities.py
   386 ./tests/test_cli_integration/test_workflows.py
   435 ./tests/test_cli/test_store_commands.py
   474 ./build/lib/refget/models.py
   475 ./build/lib/refget/refget_router.py
   527 ./refget/cli/fasta.py
   531 ./refget/refget.py
   549 ./refget/refget_router.py
   554 ./refget/cli/admin.py
   638 ./refget/models.py
   671 ./refget/cli/seqcol.py
   759 ./build/lib/refget/agents.py
   780 ./refget/clients.py
   796 ./refget/cli/store.py
   938 ./refget/agents.py
 15905 total
```
