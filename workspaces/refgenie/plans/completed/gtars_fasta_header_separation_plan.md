# Plan: Separate FASTA ID and Description in gtars-refget

## Overview

Fix the handling of FASTA headers in gtars-refget to properly separate sequence IDs from descriptions. Currently, the system stores the entire FASTA header line (including description) as the sequence "name", which violates the FASTA standard and GA4GH seqcol spec.

Add a `strict_seqnames` flag (default: true) to control this behavior, allowing users to opt-out for edge cases.

## Problem Statement

### Current Behavior

FASTA parsing in `fasta.rs` (lines 146, 319, 507) uses:
```rust
let id = line[1..].trim().to_string();
```

This stores the entire header after `>` as the name. For example:
```
>JAHKSE010000016.1 unmasked:primary_assembly HG002.alt.pat.f1_v2
```
Becomes: `name = "JAHKSE010000016.1 unmasked:primary_assembly..."`

### Why This Matters

1. **Violates FASTA standard**: The ID is the first word; everything after the first space is description
2. **Violates seqcol spec**: GA4GH seqcol defines `names` as "human-readable labels" (chromosome names), not full metadata strings
3. **Unstable digests**: Two FASTA files with identical sequences but different descriptions produce DIFFERENT seqcol digests
4. **Poor UX**: Users expect to look up "chr1", not the full header string

### Edge Case: Duplicate IDs

Some FASTA files may have sequences with the same ID but different descriptions:
```
>seq abc
ACGT
>seq xyz
GGCC
```

In strict mode, this errors. Users with such files must use `strict_seqnames=false`.

## Design

### Behavior Modes

| Mode | `name` | `description` | Duplicate IDs |
|------|--------|---------------|---------------|
| `strict_seqnames=true` (default) | First word only | Rest of header | Error |
| `strict_seqnames=false` | Full header | None | Allowed |

### Examples

```rust
// Input: ">chr1 some description"

// strict_seqnames=true (default):
name = "chr1"
description = Some("some description")

// strict_seqnames=false:
name = "chr1 some description"
description = None
```

## Implementation Steps

### Step 1: Add `strict_seqnames` field to RefgetStore

**File:** `src/store.rs` (~line 100)

```rust
pub struct RefgetStore {
    // ... existing fields ...

    /// When true (default), use only the first word of FASTA headers as sequence names.
    /// When false, use the full header (legacy behavior).
    pub strict_seqnames: bool,
}
```

Initialize to `true` in constructors (`on_disk()`, `in_memory()`, `new()`).

### Step 2: Add `description` field to SequenceMetadata

**File:** `src/collection.rs` (~line 292)

```rust
pub struct SequenceMetadata {
    pub name: String,
    pub description: Option<String>,  // NEW
    pub length: usize,
    pub sha512t24u: String,
    pub md5: String,
    pub alphabet: AlphabetType,
    pub fai: Option<FaiMetadata>,
}
```

### Step 3: Update FASTA header parsing

**File:** `src/fasta.rs` (lines 146, 319, 507)

Replace:
```rust
let id = line[1..].trim().to_string();
```

With:
```rust
let header = line[1..].trim();
let (name, description) = if strict_seqnames {
    match header.split_once(char::is_whitespace) {
        Some((id, desc)) => (id.to_string(), Some(desc.trim().to_string())),
        None => (header.to_string(), None),
    }
} else {
    (header.to_string(), None)
};
```

**Note:** The `strict_seqnames` flag needs to be passed through to these parsing functions. Options:
- Add parameter to parsing functions
- Use a thread-local or context struct
- Refactor parsing into RefgetStore methods

Simplest: add `strict_seqnames: bool` parameter to the relevant functions.

### Step 4: Add duplicate ID detection (strict mode only)

**File:** `src/store.rs` - in `add_sequence_collection_from_fasta()`

```rust
let mut seen_names: HashSet<String> = HashSet::new();

// In the sequence processing loop:
if self.strict_seqnames && seen_names.contains(&name) {
    return Err(anyhow!(
        "Duplicate sequence ID '{}' in FASTA file. Use strict_seqnames=false for files with duplicate IDs.",
        name
    ));
}
seen_names.insert(name.clone());
```

### Step 5: Update .rgsi file format

**Files:** `src/collection.rs` (write_collection_rgsi, write_collection_farg)

Old format (5 columns):
```
#name	length	alphabet	sha512t24u	md5
```

New format (6 columns):
```
#name	description	length	alphabet	sha512t24u	md5
```

```rust
writeln!(
    file,
    "{}\t{}\t{}\t{}\t{}\t{}",
    metadata.name,
    metadata.description.as_deref().unwrap_or(""),
    metadata.length,
    metadata.alphabet,
    metadata.sha512t24u,
    metadata.md5
)?;
```

### Step 6: Update .rgsi file reading

**File:** `src/fasta.rs` - `read_fasta_refget_file()`

```rust
let parts: Vec<&str> = line.split('\t').collect();
if parts.len() < 6 {
    continue;  // Or handle legacy 5-column format
}

let seq_metadata = SequenceMetadata {
    name: parts[0].to_string(),
    description: if parts[1].is_empty() { None } else { Some(parts[1].to_string()) },
    length: parts[2].parse().unwrap_or(0),
    alphabet: parts[3].parse().unwrap_or(AlphabetType::Unknown),
    sha512t24u: parts[4].to_string(),
    md5: parts[5].to_string(),
    fai: None,
};
```

### Step 7: Update FASTA export

**File:** `src/store.rs` - `export_fasta()` (~line 1198)

```rust
let header = match &metadata.description {
    Some(desc) => format!(">{} {}", metadata.name, desc),
    None => format!(">{}", metadata.name),
};
writeln!(writer, "{}", header)?;
```

### Step 8: Add Python bindings for flag

**File:** `gtars-python/src/refget/mod.rs`

Add `strict_seqnames` parameter to constructors or as a settable property:

```rust
#[getter]
fn strict_seqnames(&self) -> bool {
    self.inner.strict_seqnames
}

#[setter]
fn set_strict_seqnames(&mut self, value: bool) {
    self.inner.strict_seqnames = value;
}
```

### Step 9: Update tests

Add test cases:

```rust
#[test]
fn test_strict_seqnames_splits_header() {
    let mut store = RefgetStore::in_memory();
    assert!(store.strict_seqnames);  // Default true

    // Parse FASTA with descriptions
    // Verify name="chr1", description=Some("some desc")
}

#[test]
fn test_strict_seqnames_rejects_duplicates() {
    let mut store = RefgetStore::in_memory();
    // FASTA with duplicate IDs should error
}

#[test]
fn test_non_strict_allows_duplicates() {
    let mut store = RefgetStore::in_memory();
    store.strict_seqnames = false;
    // FASTA with duplicate IDs should work
    // Verify name includes full header
}

#[test]
fn test_fasta_roundtrip_preserves_headers() {
    // Parse FASTA → export FASTA → verify identical
}
```

## API Usage

```python
from gtars.refget import RefgetStore

# Default: strict mode (recommended)
store = RefgetStore.in_memory()
store.add_sequence_collection_from_fasta("clean_genome.fa")  # Works

# For files with duplicate IDs:
store = RefgetStore.in_memory()
store.strict_seqnames = False
store.add_sequence_collection_from_fasta("weird_file.fa")  # Works
```

## Breaking Changes

1. **RGSI format**: 5 columns → 6 columns. Old files won't parse.
2. **Seqcol digests**: Will change for FASTAs with descriptions (in strict mode).
3. **Duplicate ID files**: Will error in strict mode (default). Must opt-out.

Users must regenerate stores from original FASTA files.

## Complexity Assessment

**Low complexity.** Changes are localized:
- ~10 lines of parsing logic
- ~5 lines for duplicate detection
- Threading the flag through (straightforward)
- File format column addition

No architectural changes required.

## Summary

| Aspect | Before | After (strict=true) | After (strict=false) |
|--------|--------|---------------------|----------------------|
| `name` | Full header | First word | Full header |
| `description` | N/A | Rest of header | None |
| Duplicate IDs | Allowed | Error | Allowed |
| Spec compliant | No | Yes | No |
