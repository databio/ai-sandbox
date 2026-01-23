# Implementation plan for Multiple Remote Sources in RefgetStore

## The issue

Currently, `RefgetStore` can only point to a single remote source (`remote_source: Option<String>`). This limits use cases where sequences might be distributed across multiple servers, or where a user wants to set up a priority list of remotes (e.g., fast local server first, then public server as fallback).

## Feature summary

Add support for multiple remote sources with priority ordering. When fetching a sequence not found locally, the store will try each remote in order until successful.

## Files to read for context

- `gtars-refget/src/store.rs` - Main RefgetStore implementation
- `gtars-python/src/refget/mod.rs` - Python bindings

## Current state

```rust
pub struct RefgetStore {
    // ...
    remote_source: Option<String>,  // Single remote only
    // ...
}
```

The `fetch_file()` helper tries local first, then the single remote:
```rust
fn fetch_file(
    local_path: &Option<PathBuf>,
    remote_source: &Option<String>,  // Single remote
    relative_path: &str,
    persist_to_disk: bool,
) -> Result<Vec<u8>>
```

## Implementation Steps

### 1. Change struct field from single to multiple remotes

In `gtars-refget/src/store.rs`:

```rust
// Before
remote_source: Option<String>,

// After
remote_sources: Vec<String>,
```

### 2. Update `fetch_file()` to try remotes in order

```rust
fn fetch_file(
    local_path: &Option<PathBuf>,
    remote_sources: &[String],  // Now a slice
    relative_path: &str,
    persist_to_disk: bool,
) -> Result<Vec<u8>> {
    // Check local first (unchanged)
    if persist_to_disk {
        if let Some(local_path) = local_path {
            let full_local_path = local_path.join(relative_path);
            if full_local_path.exists() {
                return fs::read(&full_local_path)
                    .context(format!("Failed to read local file: {}", full_local_path.display()));
            }
        }
    }

    // Try each remote in priority order
    let mut last_error = None;
    for remote_url in remote_sources {
        let full_remote_url = if remote_url.ends_with('/') {
            format!("{}{}", remote_url, relative_path)
        } else {
            format!("{}/{}", remote_url, relative_path)
        };

        match ureq::get(&full_remote_url).call() {
            Ok(response) => {
                let mut data = Vec::new();
                response.into_reader().read_to_end(&mut data)
                    .context("Failed to read response body")?;

                // Cache locally if enabled
                if persist_to_disk {
                    if let Some(local_path) = local_path {
                        let full_local_path = local_path.join(relative_path);
                        if let Some(parent) = full_local_path.parent() {
                            create_dir_all(parent)?;
                        }
                        fs::write(&full_local_path, &data)?;
                    }
                }
                return Ok(data);
            }
            Err(e) => {
                last_error = Some(e);
                continue;  // Try next remote
            }
        }
    }

    // All remotes failed (or no remotes configured)
    if let Some(e) = last_error {
        Err(anyhow!("Failed to fetch from any remote: {}", e))
    } else {
        Err(anyhow!(
            "File not found locally and no remote sources configured: {}",
            relative_path
        ))
    }
}
```

### 3. Update all `fetch_file()` call sites

Change from `&self.remote_source` to `&self.remote_sources`:

- `load_remote()`
- `ensure_sequence_loaded()`
- `ensure_collection_loaded()`
- Any other places that call `fetch_file()`

### 4. Update `RefgetStore::new()` initialization

```rust
fn new(mode: StorageMode) -> Self {
    RefgetStore {
        // ...
        remote_sources: Vec::new(),  // Empty vec instead of None
        // ...
    }
}
```

### 5. Add methods for managing remotes

```rust
impl RefgetStore {
    /// Add a remote source (appended to end of priority list)
    pub fn add_remote(&mut self, url: String) {
        self.remote_sources.push(url);
    }

    /// Add a remote source at the beginning (highest priority)
    pub fn add_remote_priority(&mut self, url: String) {
        self.remote_sources.insert(0, url);
    }

    /// Get current remote sources in priority order
    pub fn remote_sources(&self) -> &[String] {
        &self.remote_sources
    }

    /// Clear all remote sources
    pub fn clear_remotes(&mut self) {
        self.remote_sources.clear();
    }

    /// Remove a specific remote source
    pub fn remove_remote(&mut self, url: &str) {
        self.remote_sources.retain(|r| r != url);
    }
}
```

### 6. Update `load_remote()` constructor

The current `load_remote()` takes a single URL. Options:

**Option A**: Keep signature, add single remote to list
```rust
pub fn load_remote<P: AsRef<Path>, S: AsRef<str>>(
    cache_path: P,
    remote_url: S,
) -> Result<Self> {
    // ... existing logic ...
    store.remote_sources = vec![remote_url.as_ref().to_string()];
    Ok(store)
}
```

**Option B**: Add new constructor for multiple remotes
```rust
pub fn load_remotes<P: AsRef<Path>>(
    cache_path: P,
    remote_urls: Vec<String>,
) -> Result<Self>
```

**Recommendation**: Option A (keep existing API), users can call `add_remote()` to add more.

### 7. Update `remote_source()` accessor

```rust
// Before
pub fn remote_source(&self) -> Option<&str> {
    self.remote_source.as_deref()
}

// After - return first remote (primary), or deprecate in favor of remote_sources()
pub fn remote_source(&self) -> Option<&str> {
    self.remote_sources.first().map(|s| s.as_str())
}

pub fn remote_sources(&self) -> &[String] {
    &self.remote_sources
}
```

### 8. Update StoreMetadata serialization (if remotes are persisted)

If the remote list should be persisted to rgstore.json:

```rust
#[derive(Serialize, Deserialize, Debug)]
struct StoreMetadata {
    version: u32,
    seqdata_path_template: String,
    mode: StorageMode,
    sequence_index: String,
    collection_index: Option<String>,
    remote_sources: Option<Vec<String>>,  // New field, optional for backward compat
}
```

However, remotes are typically runtime configuration, not persisted. **Recommendation**: Don't persist remotes - they're set when loading, not stored in metadata.

### 9. Update Python bindings

In `gtars-python/src/refget/mod.rs`:

```rust
#[pymethods]
impl RefgetStore {
    /// Add a remote source (lowest priority)
    pub fn add_remote(&mut self, url: String) {
        self.inner.add_remote(url);
    }

    /// Add a remote source (highest priority)
    pub fn add_remote_priority(&mut self, url: String) {
        self.inner.add_remote_priority(url);
    }

    /// Get remote sources in priority order
    pub fn remote_sources(&self) -> Vec<String> {
        self.inner.remote_sources().to_vec()
    }

    /// Clear all remote sources
    pub fn clear_remotes(&mut self) {
        self.inner.clear_remotes();
    }
}
```

### 10. Update Python type stubs

In `gtars-python/python/gtars/refget.pyi`:

```python
class RefgetStore:
    def add_remote(self, url: str) -> None: ...
    def add_remote_priority(self, url: str) -> None: ...
    def remote_sources(self) -> list[str]: ...
    def clear_remotes(self) -> None: ...
```

### 11. Add tests

```rust
#[test]
fn test_multiple_remotes_fallback() {
    // Set up store with multiple remotes where first fails
    let mut store = RefgetStore::in_memory();
    store.add_remote("http://nonexistent.example.com".to_string());
    store.add_remote("http://working.example.com".to_string());

    // Verify it falls back to second remote
}

#[test]
fn test_remote_priority_ordering() {
    let mut store = RefgetStore::in_memory();
    store.add_remote("http://low-priority.com".to_string());
    store.add_remote_priority("http://high-priority.com".to_string());

    assert_eq!(store.remote_sources()[0], "http://high-priority.com");
    assert_eq!(store.remote_sources()[1], "http://low-priority.com");
}
```

## Backwards compatibility

This is developmental software. We are trying to eliminate old code, not keep it around.

The change from `Option<String>` to `Vec<String>` is internal. The public API changes are:
- `remote_source()` returns `Option<&str>` (first in list) - **backward compatible**
- New `remote_sources()` returns `&[String]` - **additive**
- New `add_remote()`, `add_remote_priority()`, `clear_remotes()` - **additive**

## Cleanup

Once completed, move the completed plan to the `plans/completed/` subfolder.
