# Plan: Restructure RefgetStore API with Idiomatic Rust Constructors

## Goal
Restructure the RefgetStore API to use clear, idiomatic Rust constructors that separate storage location from data sources, eliminating boolean flags and making intent explicit.

## Overview
Replace the current mixed API (`new()`, `load_local()`, `load_remote()`) with a cleaner design:
- **Storage location constructors**: `on_disk()` and `in_memory()`
- **Population methods**: `add_sequence_collection_from_fasta()`, `add_fasta_folder()`, optional `add_remote()`
- **Keep convenience methods** for common patterns: `load_local()`, `load_remote()`
- **No builder pattern**: Simple, direct API

This separates orthogonal concerns (where to store vs where data comes from) without combinatorial explosion of constructors.

## Context Files to Review

### Rust Core
- `/home/nsheff/workspaces/intervals/repos/gtars/gtars-refget/src/store.rs` - Main store implementation
  - Current constructors: `new()` (line 198), `load_local()` (line 997), `load_remote()` (line 1097)
  - `add_sequence_collection_from_fasta()` method (line 293)
  - `write_store_to_dir()` method (line 1336)

### Python Bindings
- `/home/nsheff/workspaces/intervals/repos/gtars/gtars-python/src/refget/mod.rs` - Python bindings
  - Python constructor bindings (line 652)
  - Classmethod bindings for `load_local()`, `load_remote()`

### Tests
- `/home/nsheff/workspaces/intervals/repos/gtars/gtars-refget/src/store.rs` - Rust test module
- `/home/nsheff/workspaces/intervals/repos/gtars/gtars-python/tests/test_refget.py` - Python tests

### Documentation
- `/home/nsheff/workspaces/refgenie/repos/bedbase/docs/gtars/python/refget-store.md` - User tutorial

## Implementation Steps

### Step 1: Add New Constructors to Rust Core

**File**: `/home/nsheff/workspaces/intervals/repos/gtars/gtars-refget/src/store.rs`

#### 1.1: Add `on_disk()` Constructor
Add after `new()` method (around line 213):

```rust
/// Create a disk-backed RefgetStore
///
/// Sequences are written to disk and loaded on-demand (lazy loading).
/// Only metadata is kept in memory, making this suitable for large datasets.
///
/// # Arguments
/// * `cache_path` - Directory for storing sequences and metadata
/// * `mode` - Storage mode (Raw or Encoded)
///
/// # Returns
/// Empty store configured for disk-backed storage. Populate with `add_sequence_collection_from_fasta()`.
///
/// # Example
/// ```
/// let store = RefgetStore::on_disk("/data/refget_store", StorageMode::Encoded)?;
/// store.add_sequence_collection_from_fasta("genome.fa")?;
/// ```
pub fn on_disk<P: AsRef<Path>>(
    cache_path: P,
    mode: StorageMode,
) -> Result<Self> {
    let cache_path = cache_path.as_ref();
    create_dir_all(cache_path)?;

    // Create store with disk-backing configuration
    let mut store = RefgetStore::new(mode);
    store.local_path = Some(cache_path.to_path_buf());
    store.seqdata_path_template = Some("sequences/%s2/%s.seq".to_string());
    store.cache_to_disk = true;  // Always true for on_disk()

    // Create base directory structure
    create_dir_all(cache_path.join("sequences"))?;
    create_dir_all(cache_path.join("collections"))?;

    Ok(store)
}
```

#### 1.2: Add `in_memory()` Constructor
Add after `on_disk()`:

```rust
/// Create an in-memory RefgetStore
///
/// All sequences kept in RAM for fast access. Suitable for small datasets
/// or when working with a subset of sequences.
///
/// # Arguments
/// * `mode` - Storage mode (Raw or Encoded)
///
/// # Returns
/// Empty store configured for in-memory storage.
///
/// # Example
/// ```
/// let store = RefgetStore::in_memory(StorageMode::Encoded);
/// store.add_sequence_collection_from_fasta("genome.fa")?;
/// ```
pub fn in_memory(mode: StorageMode) -> Self {
    RefgetStore::new(mode)
}
```

### Step 2: Modify `add_sequence_collection_from_fasta()` to Respect Storage Location

**File**: `/home/nsheff/workspaces/intervals/repos/gtars/gtars-refget/src/store.rs:293-381`

Add disk-caching logic at the end of the method (around line 370):

```rust
// After processing all sequences...

// Check if store is disk-backed
if self.cache_to_disk && self.local_path.is_some() {
    println!("Writing sequences to disk (disk-backed store)...");

    // Write each sequence to disk and replace with stub
    for (sha512_key, record) in self.sequence_store.iter() {
        if let SequenceRecord::Full { metadata, sequence } = record {
            // Write to disk
            self.write_sequence_to_disk_single(metadata, sequence)?;

            // Replace with stub in memory
            let stub = SequenceRecord::Stub(metadata.clone());
            self.sequence_store.insert(*sha512_key, stub);
        }
    }
}

Ok(())
```

### Step 3: Extract Helper for Writing Single Sequence

**File**: `/home/nsheff/workspaces/intervals/repos/gtars/gtars-refget/src/store.rs`

Add before `write_store_to_dir()` method:

```rust
/// Write a single sequence to disk using the store's path template
fn write_sequence_to_disk_single(
    &self,
    metadata: &SequenceMetadata,
    sequence: &[u8],
) -> Result<()> {
    let template = self.seqdata_path_template.as_ref()
        .context("seqdata_path_template not set (store not disk-backed)")?;
    let local_path = self.local_path.as_ref()
        .context("local_path not set (store not disk-backed)")?;

    // Build file path from template
    let digest_str = &metadata.sha512t24u;
    let seq_file_path = expand_template(template, digest_str, local_path);

    // Create parent directories
    if let Some(parent) = seq_file_path.parent() {
        create_dir_all(parent)?;
    }

    // Write sequence data
    let mut file = File::create(&seq_file_path)
        .context(format!("Failed to create sequence file: {:?}", seq_file_path))?;
    file.write_all(sequence)?;

    Ok(())
}
```

### Step 4: Add Convenience Method for Batch Loading

**File**: `/home/nsheff/workspaces/intervals/repos/gtars/gtars-refget/src/store.rs`

Add after `add_sequence_collection_from_fasta()`:

```rust
/// Add all FASTA files from a directory
///
/// Convenience method to batch-load all `.fa`, `.fasta`, `.fa.gz`, and `.fasta.gz` files.
///
/// # Arguments
/// * `folder_path` - Directory containing FASTA files
///
/// # Returns
/// Number of files successfully added
pub fn add_fasta_folder<P: AsRef<Path>>(&mut self, folder_path: P) -> Result<usize> {
    let folder = folder_path.as_ref();

    if !folder.is_dir() {
        return Err(anyhow!("Path is not a directory: {:?}", folder));
    }

    // Find all FASTA files
    let mut fasta_files = Vec::new();
    for entry in fs::read_dir(folder)? {
        let entry = entry?;
        let path = entry.path();

        if path.is_file() {
            if let Some(ext) = path.extension() {
                let ext_str = ext.to_string_lossy();
                if ext_str == "fa" || ext_str == "fasta" {
                    fasta_files.push(path);
                }
            } else if let Some(name) = path.file_name() {
                let name_str = name.to_string_lossy();
                if name_str.ends_with(".fa.gz") || name_str.ends_with(".fasta.gz") {
                    fasta_files.push(path);
                }
            }
        }
    }

    fasta_files.sort();
    let total = fasta_files.len();

    println!("Found {} FASTA files in {:?}", total, folder);

    for (i, fasta_path) in fasta_files.iter().enumerate() {
        println!("  [{}/{}] Loading {:?}...", i + 1, total, fasta_path.file_name().unwrap());
        self.add_sequence_collection_from_fasta(fasta_path)?;
    }

    Ok(total)
}
```

### Step 5: Update Python Bindings

**File**: `/home/nsheff/workspaces/intervals/repos/gtars/gtars-python/src/refget/mod.rs`

#### 5.1: Add `on_disk()` Classmethod
Add after `__new__`:

```rust
#[classmethod]
fn on_disk(
    _cls: &PyType,
    cache_path: String,
    mode: StorageMode,
) -> PyResult<Self> {
    let store = RefgetStore::on_disk(cache_path, mode)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    Ok(PyRefgetStore { inner: store })
}
```

#### 5.2: Add `in_memory()` Classmethod
```rust
#[classmethod]
fn in_memory(
    _cls: &PyType,
    mode: StorageMode,
) -> PyResult<Self> {
    let store = RefgetStore::in_memory(mode);
    Ok(PyRefgetStore { inner: store })
}
```

#### 5.3: Add `add_fasta_folder()` Method
```rust
fn add_fasta_folder(&mut self, folder_path: String) -> PyResult<usize> {
    self.inner
        .add_fasta_folder(folder_path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
}
```

### Step 6: Deprecate Old Constructor

**File**: `/home/nsheff/workspaces/intervals/repos/gtars/gtars-refget/src/store.rs`

Mark `new()` as deprecated:

```rust
#[deprecated(
    since = "0.2.0",
    note = "Use `in_memory()` or `on_disk()` instead for clearer intent"
)]
pub fn new(mode: StorageMode) -> Self {
    // ... existing implementation ...
}
```

Keep `load_local()` and `load_remote()` as convenience methods (they're fine as-is).

### Step 7: Add Comprehensive Tests

**File**: `/home/nsheff/workspaces/intervals/repos/gtars/gtars-refget/src/store.rs` (test module)

```rust
#[test]
fn test_on_disk_constructor() {
    let temp_dir = tempdir().unwrap();
    let cache_path = temp_dir.path().join("store");

    let mut store = RefgetStore::on_disk(&cache_path, StorageMode::Encoded).unwrap();

    // Verify configuration
    assert_eq!(store.cache_to_disk, true);
    assert!(store.local_path.is_some());
    assert!(cache_path.join("sequences").exists());
    assert!(cache_path.join("collections").exists());
}

#[test]
fn test_in_memory_constructor() {
    let store = RefgetStore::in_memory(StorageMode::Encoded);

    assert_eq!(store.cache_to_disk, false);
    assert!(store.local_path.is_none());
}

#[test]
fn test_on_disk_with_fasta() {
    let temp_dir = tempdir().unwrap();
    let cache_path = temp_dir.path().join("store");
    let test_fa = "../tests/data/fasta/base.fa";

    let mut store = RefgetStore::on_disk(&cache_path, StorageMode::Encoded).unwrap();
    store.add_sequence_collection_from_fasta(test_fa).unwrap();

    // Verify sequences are Stubs (not in memory)
    for record in store.sequence_store.values() {
        assert!(matches!(record, SequenceRecord::Stub(_)));
    }

    // Verify sequence files exist on disk
    let seq_files: Vec<_> = fs::read_dir(cache_path.join("sequences"))
        .unwrap()
        .filter_map(|e| e.ok())
        .collect();
    assert!(seq_files.len() > 0, "Sequence files should exist on disk");
}

#[test]
fn test_in_memory_with_fasta() {
    let test_fa = "../tests/data/fasta/base.fa";

    let mut store = RefgetStore::in_memory(StorageMode::Encoded);
    store.add_sequence_collection_from_fasta(test_fa).unwrap();

    // Verify sequences are Full (in memory)
    for record in store.sequence_store.values() {
        assert!(matches!(record, SequenceRecord::Full { .. }));
    }
}

#[test]
fn test_add_fasta_folder() {
    let temp_dir = tempdir().unwrap();
    let fasta_dir = temp_dir.path().join("fastas");
    create_dir_all(&fasta_dir).unwrap();

    // Copy test files
    let test_files = ["base.fa", "different_names.fa"];
    for file in &test_files {
        let src = format!("../tests/data/fasta/{}", file);
        let dst = fasta_dir.join(file);
        fs::copy(src, dst).unwrap();
    }

    let mut store = RefgetStore::in_memory(StorageMode::Encoded);
    let count = store.add_fasta_folder(&fasta_dir).unwrap();

    assert_eq!(count, test_files.len());
    assert!(store.sequence_store.len() > 0);
}

#[test]
fn test_multiple_fastas_on_disk() {
    let temp_dir = tempdir().unwrap();
    let cache_path = temp_dir.path().join("store");
    let test_fa = "../tests/data/fasta/base.fa";

    let mut store = RefgetStore::on_disk(&cache_path, StorageMode::Encoded).unwrap();

    // Add same file twice (just for testing)
    store.add_sequence_collection_from_fasta(test_fa).unwrap();
    store.add_sequence_collection_from_fasta(test_fa).unwrap();

    // All sequences should still be Stubs
    for record in store.sequence_store.values() {
        assert!(matches!(record, SequenceRecord::Stub(_)));
    }
}
```

### Step 8: Add Python Tests

**File**: `/home/nsheff/workspaces/intervals/repos/gtars/gtars-python/tests/test_refget.py`

```python
def test_on_disk_constructor():
    """Test on_disk() constructor"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = os.path.join(tmpdir, "store")

        store = RefgetStore.on_disk(cache_path, StorageMode.Encoded)

        # Verify directories created
        assert os.path.exists(os.path.join(cache_path, "sequences"))
        assert os.path.exists(os.path.join(cache_path, "collections"))

def test_in_memory_constructor():
    """Test in_memory() constructor"""
    store = RefgetStore.in_memory(StorageMode.Encoded)

    # Should work and be in-memory
    fasta_path = "../../gtars/tests/data/fasta/base.fa"
    store.add_sequence_collection_from_fasta(fasta_path)

    sha512 = "iYtREV555dUFKg2_agSJW6suquUyPpMw"
    seq = store.get_sequence_by_id(sha512)
    assert seq is not None

def test_on_disk_with_fasta():
    """Test disk-backed store with FASTA loading"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = os.path.join(tmpdir, "store")
        fasta_path = "../../gtars/tests/data/fasta/base.fa"

        store = RefgetStore.on_disk(cache_path, StorageMode.Encoded)
        store.add_sequence_collection_from_fasta(fasta_path)

        # Verify sequence files exist
        seq_dir = os.path.join(cache_path, "sequences")
        seq_files = os.listdir(seq_dir)
        assert len(seq_files) > 0

        # Verify can retrieve
        sha512 = "iYtREV555dUFKg2_agSJW6suquUyPpMw"
        seq = store.get_sequence_by_id(sha512)
        assert seq is not None

def test_add_fasta_folder():
    """Test batch loading from folder"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test folder with FASTA files
        fasta_dir = os.path.join(tmpdir, "fastas")
        os.makedirs(fasta_dir)

        # Copy test files
        import shutil
        test_files = ["base.fa", "different_names.fa"]
        for fname in test_files:
            src = f"../../gtars/tests/data/fasta/{fname}"
            dst = os.path.join(fasta_dir, fname)
            shutil.copy(src, dst)

        store = RefgetStore.in_memory(StorageMode.Encoded)
        count = store.add_fasta_folder(fasta_dir)

        assert count == len(test_files)
        assert len(list(store.sequence_metadata())) > 0

def test_disk_and_memory_combinations():
    """Test all four combinations of storage + source"""
    with tempfile.TemporaryDirectory() as tmpdir:
        fasta_path = "../../gtars/tests/data/fasta/base.fa"
        cache_path = os.path.join(tmpdir, "store")

        # 1. Disk + Local FASTA
        store1 = RefgetStore.on_disk(cache_path + "1", StorageMode.Encoded)
        store1.add_sequence_collection_from_fasta(fasta_path)
        assert len(list(store1.sequence_metadata())) > 0

        # 2. Memory + Local FASTA
        store2 = RefgetStore.in_memory(StorageMode.Encoded)
        store2.add_sequence_collection_from_fasta(fasta_path)
        assert len(list(store2.sequence_metadata())) > 0

        # 3. Disk + Folder
        fasta_dir = os.path.join(tmpdir, "fastas")
        os.makedirs(fasta_dir)
        import shutil
        shutil.copy(fasta_path, os.path.join(fasta_dir, "test.fa"))

        store3 = RefgetStore.on_disk(cache_path + "3", StorageMode.Encoded)
        count = store3.add_fasta_folder(fasta_dir)
        assert count == 1

        # 4. Memory + Folder
        store4 = RefgetStore.in_memory(StorageMode.Encoded)
        count = store4.add_fasta_folder(fasta_dir)
        assert count == 1
```

### Step 9: Update Documentation

**File**: `/home/nsheff/workspaces/refgenie/repos/bedbase/docs/gtars/python/refget-store.md`

Replace the current "Creating and Populating a Store" and "Incremental Batch Loading" sections with:

```markdown
## Creating a Store

### Disk-Backed Store (Recommended for Large Datasets)

Sequences written to disk, loaded on-demand. Only metadata in RAM.

```python
from gtars.refget import RefgetStore, StorageMode

# Create disk-backed store
store = RefgetStore.on_disk("/data/refget_store", StorageMode.Encoded)

# Add FASTA files
store.add_sequence_collection_from_fasta("genome.fa.gz")
store.add_sequence_collection_from_fasta("genome2.fa.gz")

# Or add entire folder
store.add_fasta_folder("/data/genomes/")

# Sequences on disk, only metadata in RAM
print(f"Store contains {len(store.collections())} collections")
```

### In-Memory Store (Fast Access for Small Datasets)

All sequences kept in RAM.

```python
# Create in-memory store
store = RefgetStore.in_memory(StorageMode.Encoded)

# Add FASTA files
store.add_sequence_collection_from_fasta("small_genome.fa")

# Everything in RAM for fast access
```

## Batch Loading Example

Complete example loading a folder of gzipped FASTAs:

```python
from pathlib import Path
from gtars.refget import RefgetStore, StorageMode
import os

# Configuration
fa_root = Path(os.path.expandvars("$BRICKYARD/datasets_downloaded/pangenome_fasta/2023_hprc_draft"))
output_dir = Path(os.path.expandvars("$BRICKYARD/datasets_downloaded/pangenome_fasta/refget_store"))

# Create disk-backed store
print(f"Creating disk-backed store at {output_dir}...")
store = RefgetStore.on_disk(str(output_dir), StorageMode.Encoded)

# Add entire folder
count = store.add_fasta_folder(str(fa_root))

print(f"✓ Added {count} FASTA files")
print(f"✓ Store contains {len(store.collections())} collections")
print(f"✓ Only metadata in RAM, sequences on disk")
```

## When to Use Each Constructor

| Constructor | Use When | Memory Usage | Access Speed |
|------------|----------|--------------|--------------|
| `on_disk()` | Large datasets, batch processing | Low (metadata only) | Moderate (lazy loading) |
| `in_memory()` | Small datasets, frequent access | High (all sequences) | Fast (no I/O) |
| `load_local()` | Loading existing store | Low (lazy loading) | Moderate |
| `load_remote()` | Fetching from remote server | Configurable | Varies |
```

### Step 10: Update API Reference / Docstrings

Add module-level documentation to store.rs:

```rust
//! # RefgetStore Constructors
//!
//! ## Storage Location
//! Choose where sequences are stored:
//! - [`on_disk()`]: Disk-backed with lazy loading (memory-efficient)
//! - [`in_memory()`]: All sequences in RAM (fast access)
//!
//! ## Loading Existing Stores (Convenience)
//! - [`load_local()`]: Load from local directory
//! - [`load_remote()`]: Fetch from remote URL with optional caching
//!
//! ## Adding Data
//! - [`add_sequence_collection_from_fasta()`]: Add single FASTA file
//! - [`add_fasta_folder()`]: Add all FASTAs from directory
//!
//! ## Example
//! ```rust
//! // Disk-backed for large dataset
//! let mut store = RefgetStore::on_disk("/data/store", StorageMode::Encoded)?;
//! store.add_fasta_folder("/data/genomes")?;
//!
//! // In-memory for small dataset
//! let mut store = RefgetStore::in_memory(StorageMode::Encoded);
//! store.add_sequence_collection_from_fasta("genome.fa")?;
//! ```
```

## Summary of Changes

### Before (Lines of Code)
- `new()`: ~15 lines
- `load_local()`: ~89 lines
- `load_remote()`: ~109 lines
- Total constructors: ~213 lines
- `add_sequence_collection_from_fasta()`: ~88 lines (no disk-backing logic)

### After (Estimated Lines of Code)
- `on_disk()`: ~20 lines
- `in_memory()`: ~5 lines
- `load_local()`: ~89 lines (unchanged)
- `load_remote()`: ~109 lines (unchanged)
- `write_sequence_to_disk_single()`: ~25 lines (new helper)
- Modified `add_sequence_collection_from_fasta()`: ~110 lines (+22 for disk-backing)
- `add_fasta_folder()`: ~40 lines (new convenience)
- Total new code: ~398 lines
- New tests: ~150 lines (Rust) + ~100 lines (Python)

### Key Improvements
1. **Clearer Intent**: `on_disk()` vs `in_memory()` vs `new()` with boolean
2. **Composable**: 2 constructors × multiple data sources = all combinations
3. **Consistent**: Storage location separate from data source
4. **Convenient**: `add_fasta_folder()` for batch loading
5. **Idiomatic**: Follows Rust naming conventions
6. **No Breaking Changes for Core Functionality**: `load_local()` and `load_remote()` stay

## IMPORTANT: No Backwards Compatibility Required

This is developmental software. We are:
- **DEPRECATING** `new()` constructor (mark with `#[deprecated]`)
- **KEEPING** convenience methods `load_local()` and `load_remote()` (they're still useful)
- **ENCOURAGING** migration to `on_disk()` / `in_memory()` for new code
- **NOT MAINTAINING** old patterns - the goal is to clean up the API

Users should migrate to the new API:
- `new()` → `in_memory()`
- `new()` + manual path setting → `on_disk()`

## Testing Strategy

1. **Unit Tests**: Each constructor independently
2. **Integration Tests**: All combinations (disk+fasta, memory+fasta, disk+folder, memory+folder)
3. **Regression Tests**: Verify `load_local()` and `load_remote()` still work
4. **Migration Tests**: Verify deprecated `new()` still works but shows warning

## Documentation Updates

1. Update tutorial with new constructors first
2. Add migration guide for existing users
3. Update API reference
4. Add examples to method docstrings
5. Create comparison table (disk vs memory)
