# Plan: Add attach_remote() Method to RefgetStore

## Overview

Add functionality to attach a remote URL to an existing RefgetStore, enabling lazy-loading of sequences and collections from a remote source without needing to create a new store from scratch using `load_remote()`.

This enables a workflow where users can:
1. Create or load a local store (with `on_disk()` or `load_local()`)
2. Later attach a remote URL to enable fallback fetching for missing sequences

## Use Cases

1. **Hybrid local/remote stores**: User has a partial local store and wants to fetch missing sequences on-demand from a remote
2. **Progressive caching**: Start with an empty local cache, attach a remote, and build the cache incrementally as sequences are accessed
3. **Runtime configuration**: Configure remote URL after store creation, possibly from environment variables or user config loaded at runtime

## Context Files to Read

- `gtars-refget/src/store.rs` - RefgetStore implementation, particularly:
  - Lines 81-101: RefgetStore struct definition with `remote_source` field
  - Lines 814-816: `remote_source()` getter method
  - Lines 1458-1517: `fetch_file()` helper that uses `remote_source`
  - Lines 1690-1864: `load_remote()` for pattern reference
- `gtars-python/src/refget/mod.rs` - Python bindings for RefgetStore:
  - Lines 1064-1070: `remote_url` getter binding
- `gtars-python/py_src/gtars/refget/__init__.pyi` - Type stubs for documentation

## Implementation Steps

### 1. Add Rust Method to RefgetStore (gtars-refget/src/store.rs)

Add `attach_remote()` method alongside the existing `enable_persistence()` and `disable_persistence()` methods (around line 421):

```rust
/// Attach a remote URL to this store for on-demand sequence fetching.
///
/// Once attached, the store will attempt to fetch missing sequences and
/// collections from the remote URL when accessed. Fetched data is cached
/// locally if `persist_to_disk` is enabled.
///
/// # Arguments
/// * `remote_url` - Base URL of the remote refget store
///
/// # Notes
/// - Requires `local_path` to be set (either from `on_disk()` or `enable_persistence()`)
/// - Call `disable_persistence()` after if you don't want to cache fetched data
///
/// # Example
/// ```ignore
/// let mut store = RefgetStore::on_disk("/data/cache")?;
/// store.attach_remote("https://example.com/hg38");
/// // Now sequences missing locally will be fetched from remote
/// let seq = store.get_sequence_by_id("some_digest");
/// ```
pub fn attach_remote<S: AsRef<str>>(&mut self, remote_url: S) -> Result<()> {
    // Validate that we have a local path for caching
    if self.local_path.is_none() {
        return Err(anyhow!("Cannot attach remote without a local path. Call enable_persistence() or use on_disk() first."));
    }

    self.remote_source = Some(remote_url.as_ref().to_string());
    Ok(())
}

/// Detach the remote URL from this store.
///
/// After calling this, the store will no longer attempt to fetch missing
/// sequences from remote. Existing cached data remains available.
pub fn detach_remote(&mut self) {
    self.remote_source = None;
}
```

### 2. Add Python Binding (gtars-python/src/refget/mod.rs)

Add Python method bindings in the `#[pymethods] impl PyRefgetStore` block (around line 945):

```rust
/// Attach a remote URL for on-demand sequence fetching.
///
/// Once attached, missing sequences will be fetched from the remote URL
/// and cached locally. Requires a local path to be configured.
///
/// Args:
///     remote_url: Base URL of the remote refget store.
///
/// Raises:
///     IOError: If no local path is configured for caching.
///
/// Example::
///
///     store = RefgetStore.on_disk("/data/cache")
///     store.attach_remote("https://example.com/hg38")
///     seq = store.get_sequence_by_id("some_digest")  # Fetched from remote
#[pyo3(signature = (remote_url))]
fn attach_remote(&mut self, remote_url: &str) -> PyResult<()> {
    self.inner.attach_remote(remote_url).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Error attaching remote: {}", e))
    })
}

/// Detach the remote URL from this store.
///
/// After calling this, missing sequences will no longer be fetched from remote.
/// Existing cached data remains available.
fn detach_remote(&mut self) {
    self.inner.detach_remote();
}
```

### 3. Update Type Stubs (gtars-python/py_src/gtars/refget/__init__.pyi)

Add method signatures and documentation in the `RefgetStore` class:

```python
def attach_remote(self, remote_url: str) -> None:
    """Attach a remote URL for on-demand sequence fetching.

    Once attached, missing sequences will be fetched from the remote URL
    and cached locally. Requires a local path to be configured (either
    from on_disk() or enable_persistence()).

    Args:
        remote_url: Base URL of the remote refget store (e.g.,
            "https://example.com/hg38" or "s3://bucket/hg38").

    Raises:
        IOError: If no local path is configured for caching.

    Example::

        store = RefgetStore.on_disk("/data/cache")
        store.attach_remote("https://refget-server.com/hg38")
        # First access fetches from remote and caches
        seq = store.get_substring("chr1_digest", 0, 1000)
    """
    ...

def detach_remote(self) -> None:
    """Detach the remote URL from this store.

    After calling this, the store will no longer attempt to fetch missing
    sequences from remote. Existing cached data remains available.

    Example::

        store.attach_remote("https://example.com/hg38")
        # ... use remote ...
        store.detach_remote()  # Stop remote fetching
    """
    ...
```

### 4. Add Tests (gtars-refget/src/store.rs)

Add tests in the existing test module:

```rust
#[test]
fn test_attach_remote_requires_local_path() {
    let mut store = RefgetStore::in_memory();
    let result = store.attach_remote("https://example.com");
    assert!(result.is_err());
    assert!(result.unwrap_err().to_string().contains("local path"));
}

#[test]
fn test_attach_remote_after_on_disk() {
    let temp_dir = tempfile::tempdir().unwrap();
    let mut store = RefgetStore::on_disk(temp_dir.path()).unwrap();

    assert!(store.remote_source().is_none());
    store.attach_remote("https://example.com/hg38").unwrap();
    assert_eq!(store.remote_source(), Some("https://example.com/hg38"));
}

#[test]
fn test_detach_remote() {
    let temp_dir = tempfile::tempdir().unwrap();
    let mut store = RefgetStore::on_disk(temp_dir.path()).unwrap();

    store.attach_remote("https://example.com/hg38").unwrap();
    assert!(store.remote_source().is_some());

    store.detach_remote();
    assert!(store.remote_source().is_none());
}

#[test]
fn test_attach_remote_after_enable_persistence() {
    let temp_dir = tempfile::tempdir().unwrap();
    let mut store = RefgetStore::in_memory();

    // Can't attach remote before enabling persistence
    assert!(store.attach_remote("https://example.com").is_err());

    // After enabling persistence, attach works
    store.enable_persistence(temp_dir.path()).unwrap();
    store.attach_remote("https://example.com/hg38").unwrap();
    assert_eq!(store.remote_source(), Some("https://example.com/hg38"));
}
```

### 5. Update Module Documentation (gtars-refget/src/store.rs)

Update the module-level documentation at the top of the file to mention the new method:

```rust
//! ## Runtime Configuration
//!
//! ### Persistence control
//! - `enable_persistence(path)` - Start writing to disk, flush in-memory data
//! - `disable_persistence()` - Stop writing to disk (can still read)
//!
//! ### Remote source control
//! - `attach_remote(url)` - Enable on-demand fetching from remote URL
//! - `detach_remote()` - Disable remote fetching
//!
//! ### Encoding control
//! - `set_encoding_mode(mode)` - Switch between Raw and Encoded storage
```

## Summary of Changes

| File | Change |
|------|--------|
| `gtars-refget/src/store.rs` | Add `attach_remote()` and `detach_remote()` methods, update module docs, add tests |
| `gtars-python/src/refget/mod.rs` | Add Python bindings for new methods |
| `gtars-python/py_src/gtars/refget/__init__.pyi` | Add type stubs with documentation |

## Notes

- **No backwards compatibility concerns**: This is purely additive - no existing functionality changes
- The implementation mirrors the existing `enable_persistence()` / `disable_persistence()` pattern
- Validation ensures local_path is set before attaching remote (required for caching)
- The `fetch_file()` infrastructure already handles remote fetching when `remote_source` is set
