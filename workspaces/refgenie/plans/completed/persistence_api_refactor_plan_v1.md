# Implementation plan for RefgetStore Persistence API Refactor

## The issue

The current `RefgetStore` API for controlling persistence is confusing and inconsistent:

1. **Inconsistent naming**: The internal field `cache_to_disk` doesn't clearly convey its purpose
2. **Asymmetric API**: `load_remote()` takes a `cache_to_disk` parameter, but `load_local()` doesn't
3. **No runtime control**: Users cannot toggle persistence after store creation
4. **Confusing method name**: `set_mode()` controls encoding, not the "mode" of the store

### Current state

| Method | Persistence | User control |
|--------|-------------|--------------|
| `in_memory()` | No | Fixed at creation |
| `on_disk(path)` | Yes | Fixed at creation |
| `load_local(path)` | Yes (always) | None |
| `load_remote(path, url, cache_to_disk)` | User's choice | Parameter only |

### Desired state

| Method | Default Persistence | Runtime control |
|--------|---------------------|-----------------|
| `in_memory()` | No | `enable_persistence(path)` |
| `on_disk(path)` | Yes | `disable_persistence()` |
| `load_local(path)` | Yes | `disable_persistence()` |
| `load_remote(path, url)` | Yes | `disable_persistence()` |

Plus rename `set_mode()` → `set_encoding_mode()` for clarity.

## Files to read for context

- `gtars-refget/src/store.rs` - Main Rust implementation (RefgetStore)
- `gtars-python/src/refget/mod.rs` - Python bindings (PyRefgetStore)
- `gtars-python/tests/test_refget.py` - Python tests

## Implementation Steps

### Step 1: Rename internal field in Rust store

In `gtars-refget/src/store.rs`:

1. Rename field `cache_to_disk` → `persist_to_disk` in `RefgetStore` struct (line ~74)
2. Update all references to this field throughout the file (approximately 15 occurrences)

### Step 2: Rename `set_mode()` to `set_encoding_mode()` in Rust

In `gtars-refget/src/store.rs`:

1. Rename `pub fn set_mode()` → `pub fn set_encoding_mode()` (line ~290)
2. Update calls in `enable_encoding()` and `disable_encoding()` to use new name

### Step 3: Implement `enable_persistence()` in Rust

In `gtars-refget/src/store.rs`, add new method to `impl RefgetStore`:

```rust
/// Enable disk persistence for this store.
///
/// Sets up the store to write sequences to disk. Any in-memory Full sequences
/// are flushed to disk and converted to Stubs.
///
/// # Arguments
/// * `path` - Directory for storing sequences and metadata
///
/// # Returns
/// Result indicating success or error
pub fn enable_persistence<P: AsRef<Path>>(&mut self, path: P) -> Result<()> {
    let path = path.as_ref();

    // Set up persistence configuration
    self.local_path = Some(path.to_path_buf());
    self.persist_to_disk = true;
    self.seqdata_path_template
        .get_or_insert_with(|| DEFAULT_SEQDATA_PATH_TEMPLATE.to_string());

    // Create directory structure
    create_dir_all(path.join("sequences"))?;
    create_dir_all(path.join("collections"))?;

    // Flush any in-memory Full sequences to disk
    let keys: Vec<[u8; 32]> = self.sequence_store.keys().cloned().collect();
    for key in keys {
        if let Some(SequenceRecord::Full { metadata, sequence }) = self.sequence_store.get(&key) {
            // Write to disk
            self.write_sequence_to_disk_single(metadata, sequence)?;
            // Convert to stub
            let stub = SequenceRecord::Stub(metadata.clone());
            self.sequence_store.insert(key, stub);
        }
    }

    // Write all collections to disk
    for collection in self.collections.values() {
        self.write_collection_to_disk_single(collection)?;
    }

    // Write index files
    self.write_index_files()?;

    Ok(())
}
```

### Step 4: Implement `disable_persistence()` in Rust

In `gtars-refget/src/store.rs`, add new method:

```rust
/// Disable disk persistence for this store.
///
/// New sequences will be kept in memory only. Existing Stub sequences
/// can still be loaded from disk if local_path is set.
pub fn disable_persistence(&mut self) {
    self.persist_to_disk = false;
}
```

### Step 5: Update `load_remote()` in Rust

In `gtars-refget/src/store.rs`:

1. Remove the `cache_to_disk` parameter from `load_remote()` signature
2. Default to `persist_to_disk = true` (users can call `disable_persistence()` after)
3. Update the function body to remove references to the parameter

Change from:
```rust
pub fn load_remote<P: AsRef<Path>, S: AsRef<str>>(
    cache_path: P,
    remote_url: S,
    cache_to_disk: bool,
) -> Result<Self>
```

To:
```rust
pub fn load_remote<P: AsRef<Path>, S: AsRef<str>>(
    cache_path: P,
    remote_url: S,
) -> Result<Self>
```

And set `store.persist_to_disk = true;` internally.

### Step 6: Add module-level documentation in Rust

At the top of `gtars-refget/src/store.rs`, add comprehensive documentation:

```rust
//! # RefgetStore
//!
//! A store for managing reference genome sequences with support for both
//! in-memory and disk-backed storage.
//!
//! ## Store Creation Patterns
//!
//! ### New stores (empty)
//! - `in_memory()` - All data in RAM, fast but lost on drop
//! - `on_disk(path)` - Sequences written to disk immediately, only metadata in RAM
//!
//! ### Loading existing stores
//! - `load_local(path)` - Load from local directory (lazy-loads sequences)
//! - `load_remote(path, url)` - Load from URL, caches to local directory
//!
//! ## Runtime Configuration
//!
//! ### Persistence control
//! - `enable_persistence(path)` - Start writing to disk, flush in-memory data
//! - `disable_persistence()` - Stop writing to disk (can still read)
//!
//! ### Encoding control
//! - `set_encoding_mode(mode)` - Switch between Raw and Encoded storage
//! - `enable_encoding()` - Use 2-bit encoding (space efficient)
//! - `disable_encoding()` - Use raw bytes
```

### Step 7: Update Python bindings

In `gtars-python/src/refget/mod.rs`:

1. Rename `set_mode()` → `set_encoding_mode()` (line ~699)
2. Add `enable_persistence()` method:
```rust
#[pyo3(signature = (path))]
fn enable_persistence(&mut self, path: &Bound<'_, PyAny>) -> PyResult<()> {
    let path = path.to_string();
    self.inner.enable_persistence(path).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Error enabling persistence: {}", e))
    })
}
```

3. Add `disable_persistence()` method:
```rust
fn disable_persistence(&mut self) {
    self.inner.disable_persistence();
}
```

4. Update `load_remote()` to remove `cache_to_disk` parameter (lines ~1004-1011)

### Step 8: Update Python type stubs

In `gtars-python/py_src/gtars/refget/__init__.pyi`:

1. Add `enable_persistence()` and `disable_persistence()` method signatures
2. Rename `set_mode()` → `set_encoding_mode()`
3. Update `load_remote()` signature to remove `cache_to_disk` parameter

### Step 9: Update Python tests

In `gtars-python/tests/test_refget.py`:

1. Update any tests that use `set_mode()` to use `set_encoding_mode()`
2. Update any tests that use `load_remote(..., cache_to_disk=...)` to use the new pattern:
   ```python
   store = RefgetStore.load_remote(path, url)
   store.disable_persistence()  # if memory-only desired
   ```
3. Add new tests for `enable_persistence()` and `disable_persistence()`

### Step 10: Run tests and fix any issues

1. Run Rust tests: `cargo test -p gtars-refget`
2. Run Python tests: `cd gtars-python && pytest tests/test_refget.py -v`
3. Fix any compilation errors or test failures

## Backwards compatibility

This is developmental software. We are trying to eliminate old code, not keep it around.

Breaking changes:
- `set_mode()` renamed to `set_encoding_mode()` (Rust and Python)
- `load_remote()` no longer accepts `cache_to_disk` parameter (Rust and Python)
- Internal field `cache_to_disk` renamed to `persist_to_disk`

Users must update their code:
- `store.set_mode(...)` → `store.set_encoding_mode(...)`
- `RefgetStore.load_remote(path, url, cache_to_disk=False)` → `store = RefgetStore.load_remote(path, url); store.disable_persistence()`
