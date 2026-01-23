# Plan: Migrate FAI Computation from Python to gtars

## Status: In Progress

**Completed:** gtars Rust implementation and Python bindings
**Remaining:** Update refget Python package to use gtars instead of its own implementation

## Overview

Move FASTA index (FAI) computation from Python (`FastaDrsObject._compute_fai_index()`) to Rust (gtars). This improves performance and consolidates FASTA parsing logic.

## Architecture Note: FAI is File-Specific

FAI data is specific to a **FASTA file**, not a **sequence collection**. Two FASTA files with identical sequences but different line wrapping have:
- Same seqcol digest
- Different FAI offsets and line_bases/line_bytes

This is handled correctly:
- **RefgetStore / `.rgsi` files**: Do NOT store FAI data (content-addressed)
- **FastaDrsObject**: DOES store FAI data (file-specific metadata)

The gtars implementation computes FAI transiently during FASTA parsing. It flows to `FastaDrsObject` in refget, where it belongs.

---

## What's Already Implemented in gtars

### Rust Structs (gtars-refget/src/collection.rs)

```rust
/// FASTA index (FAI) metadata for a sequence.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct FaiMetadata {
    pub offset: u64,       // byte offset to first base of sequence data
    pub line_bases: u32,   // number of bases per line
    pub line_bytes: u32,   // number of bytes per line (including newline chars)
}

pub struct SequenceMetadata {
    pub name: String,
    pub length: usize,
    pub sha512t24u: String,
    pub md5: String,
    pub alphabet: AlphabetType,
    pub fai: Option<FaiMetadata>,  // Present when parsed from FASTA
}
```

### Python Bindings (gtars-python/src/refget/mod.rs)

```python
from gtars.refget import compute_fai, FaiMetadata, FaiRecord

# Dedicated FAI computation function
fai_records = compute_fai("genome.fa")
for record in fai_records:
    record.name         # str: sequence name
    record.length       # int: sequence length
    record.fai.offset      # int: byte offset
    record.fai.line_bases  # int: bases per line
    record.fai.line_bytes  # int: bytes per line

# Or via digest_fasta (FAI included in metadata)
from gtars.refget import digest_fasta
seq_col = digest_fasta("genome.fa")
for seq in seq_col.sequences:
    seq.metadata.fai.offset      # Available if parsed from FASTA
    seq.metadata.fai.line_bases
    seq.metadata.fai.line_bytes
```

### FAI Not Persisted to RefgetStore

When writing `.rgsi` files, FAI data is intentionally excluded (collection.rs:676):
```rust
fai: None,  // FARG files don't store FAI data
```

This is correct - FAI belongs with file metadata, not content-addressed storage.

---

## What Remains: Update refget Python Package

### Current State (to be replaced)

**File:** `repos/refget/refget/models.py`

The `FastaDrsObject` class has its own Python FAI computation:

```python
@classmethod
def _compute_fai_index(cls, fasta_file: str) -> dict:
    # ~35 lines of Python reading file line-by-line
    # Returns {"offsets": [...], "line_bases": N, "extra_line_bytes": N}
```

This is called from `FastaDrsObject.from_fasta_file()` at line 233.

### Implementation Steps

#### Step 1: Update `FastaDrsObject.from_fasta_file()` to use gtars

**File:** `repos/refget/refget/models.py`

Replace the call to `_compute_fai_index()` with gtars `compute_fai()`:

```python
@classmethod
def from_fasta_file(cls, fasta_file: str, digest: str = None) -> "FastaDrsObject":
    from gtars.refget import compute_fai

    file_size = os.path.getsize(fasta_file)

    # Get FAI data from gtars (Rust, fast)
    fai_records = compute_fai(fasta_file)

    # Collect per-sequence offsets
    offsets = []
    line_bases_set = set()
    line_bytes_set = set()

    for record in fai_records:
        if record.fai:  # None for gzipped files
            offsets.append(record.fai.offset)
            line_bases_set.add(record.fai.line_bases)
            line_bytes_set.add(record.fai.line_bytes)

    # Validate consistency (required for valid FAI index)
    if len(line_bases_set) > 1:
        raise ValueError(
            f"Inconsistent line_bases across sequences: {line_bases_set}. "
            "FASTA file cannot be FAI-indexed."
        )
    if len(line_bytes_set) > 1:
        raise ValueError(
            f"Inconsistent line_bytes across sequences: {line_bytes_set}. "
            "FASTA file cannot be FAI-indexed."
        )

    line_bases = line_bases_set.pop() if line_bases_set else None
    line_bytes = line_bytes_set.pop() if line_bytes_set else None
    extra_line_bytes = (line_bytes - line_bases) if line_bytes and line_bases else None

    # ... rest of method (checksums, etc.) stays the same ...

    return FastaDrsObject(
        id=digest,
        name=os.path.basename(fasta_file),
        # ... other fields ...
        line_bases=line_bases,
        extra_line_bytes=extra_line_bytes,
        offsets=offsets if offsets else None,
    )
```

#### Step 2: Delete `_compute_fai_index()` method

Remove the entire `_compute_fai_index()` method (~lines 169-199 in models.py). No backwards compatibility needed.

#### Step 3: Update imports

Add gtars import at top of models.py if not present:
```python
from gtars.refget import compute_fai
```

#### Step 4: Test

Run existing tests to ensure FAI data is correctly computed:
```bash
cd repos/refget
pytest -v -k fai
```

---

## Summary

| Component | Status | Notes |
|-----------|--------|-------|
| gtars `FaiMetadata` struct | ✅ Done | collection.rs:308-312 |
| gtars FAI computation | ✅ Done | fasta.rs (multiple locations) |
| gtars Python bindings | ✅ Done | `compute_fai()`, `FaiMetadata`, `FaiRecord` |
| refget uses gtars FAI | ❌ Pending | Still uses `_compute_fai_index()` |
| Delete Python FAI code | ❌ Pending | After migration |

**Estimated effort:** ~30 minutes. Simple replacement of one method call and deletion of unused code.
