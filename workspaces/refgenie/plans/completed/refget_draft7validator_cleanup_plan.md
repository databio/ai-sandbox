# Refget Draft7Validator Cleanup Plan

## Goal

Resolve the broken `Draft7Validator` reference in `refget/models.py`. The file uses `Draft7Validator` without importing it, and the method that uses it (`input_validate`) is never called anywhere in the codebase.

## Diagnosis

### The Problem

In `refget/models.py`, line 384, there's a reference to `Draft7Validator`:

```python
def input_validate(cls, seqcol_obj: dict) -> bool:
    ...
    validator = Draft7Validator(schema)  # Line 384 - NameError: Draft7Validator not defined
```

However, `Draft7Validator` is **never imported** in `models.py`. This code would raise a `NameError` if ever executed.

### Why It's Dead Code

1. **Missing import**: `Draft7Validator` is imported in `utilities.py` but not in `models.py`
2. **Never called**: Searching for `.input_validate(` returns zero matches - this method is never used
3. **Duplicates existing functionality**: `utilities.py` already has working validation functions:
   - `validate_seqcol_bool()` - Returns True/False
   - `validate_seqcol()` - Returns True or raises `InvalidSeqColError`

### Decision: Remove Cruft

The `input_validate` method in `models.py` should be **removed entirely** because:

1. **It's broken** - Would fail with `NameError` if called
2. **It's unused** - No code calls this method
3. **Functionality exists elsewhere** - `utilities.validate_seqcol()` does the same thing and works correctly
4. **Bug in implementation** - It calls `seqcol_obj.level2()` but receives a `dict`, not a `SequenceCollection` object (would fail with `AttributeError` even if the import existed)

There is **no need for a validator** in this specific location. The existing validation functions in `utilities.py` are sufficient and are designed for use at API boundaries.

## Files to Read for Context

1. `refget/models.py` - Contains the broken `input_validate` method (line 372-389)
2. `refget/utilities.py` - Contains working validation functions (lines 32-56)

## Concrete Steps

### Step 1: Remove the `input_validate` method from `models.py`

Delete lines 371-389 in `refget/models.py`:

```python
    @classmethod
    def input_validate(cls, seqcol_obj: dict) -> bool:
        """
        Given a dict representation of a sequence collection, validate it against the input schema.

        Args:
            seqcol_obj (dict): Dictionary representation of a canonical sequence collection object

        Returns:
            (bool): True if the object is valid, False otherwise
        """
        with open(SEQCOL_SCHEMA_PATH, "r") as f:
            schema = json.load(f)
        validator = Draft7Validator(schema)

        if not validator.is_valid(seqcol_obj.level2()):
            errors = sorted(validator.iter_errors(seqcol_obj), key=lambda e: e.path)
            raise InvalidSeqColError("Validation failed", errors)
        return True
```

### Step 2: Remove the `InvalidSeqColError` import if no longer used

After removing `input_validate`, check if `InvalidSeqColError` is still used in `models.py`:

```bash
grep -n "InvalidSeqColError" refget/models.py
```

If only used in the now-deleted `input_validate` method, remove the import from line 44.

### Step 3: Verify no other code depends on `input_validate`

Already confirmed: `grep "\.input_validate\("` returns no matches.

## Verification Steps

1. **Run existing tests:**
   ```bash
   cd repos/refget
   pytest
   ```
   All tests should pass (they weren't using the broken method anyway).

2. **Check imports are clean:**
   ```bash
   python -c "from refget.models import SequenceCollection"
   ```
   Should succeed without errors.

## Summary

| Before | After |
|--------|-------|
| Broken `input_validate` method (18 lines) | Removed |
| Unused code with `NameError` potential | Clean codebase |
| `InvalidSeqColError` import (possibly unused) | Import removed if unused |

**Line reduction:** ~18 lines

## Important Notes

- **DO NOT MAINTAIN BACKWARDS COMPATIBILITY** - This is developmental software. The broken method was never functional and was never called.
- **DO NOT add the missing import** - The method is fundamentally broken (also calls `.level2()` on a dict) and duplicates existing functionality.
- **Validation belongs at API boundaries** - Use `refget.utilities.validate_seqcol()` or `validate_seqcol_bool()` where validation is actually needed.
