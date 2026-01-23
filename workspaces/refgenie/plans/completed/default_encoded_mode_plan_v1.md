# Implementation plan for Default StorageMode.Encoded with Dynamic Mode Switching

## The issue

Currently, `RefgetStore` constructors (`on_disk()`, `in_memory()`) **require** users to specify `StorageMode` (Raw or Encoded). This is verbose and error-prone because:

1. **Most users want Encoded** - it's space-efficient (2-bit encoding for DNA sequences)
2. **Forcing explicit mode** adds boilerplate to every store creation
3. **No way to change mode** after creation - switching between Raw/Encoded requires rebuilding the store

**Feature request:**
1. Default to `StorageMode::Encoded` (user doesn't need to specify)
2. Add a setter method to change the mode dynamically
3. When mode changes, automatically re-encode/decode existing sequences in the store

## Files to read for context

1. **`/home/nsheff/workspaces/intervals/repos/gtars/gtars-refget/src/store.rs`**
   - Lines 35-39: `StorageMode` enum definition (Raw, Encoded)
   - Lines 54-75: `RefgetStore` struct (has `mode: StorageMode` field)
   - Lines 235-261: `on_disk()` constructor - currently requires mode
   - Lines 276-278: `in_memory()` constructor - currently requires mode
   - Lines 423-470: `add_sequence_collection_from_fasta()` - uses `self.mode` to decide Raw vs Encoded

2. **`/home/nsheff/workspaces/intervals/repos/gtars/gtars-refget/src/encoder.rs`**
   - Line 97: `encode_sequence()` - encodes raw bytes to 2-bit packed
   - Line 134: `decode_substring_from_bytes()` - decodes 2-bit back to string
   - Line 163: `decode_string_from_bytes()` - full sequence decoding

3. **`/home/nsheff/workspaces/intervals/repos/gtars/gtars-refget/src/collection.rs`**
   - Line 241: `SequenceRecord::decode()` - decodes sequence data to String

4. **`/home/nsheff/workspaces/intervals/repos/gtars/gtars-python/src/refget/mod.rs`**
   - Python bindings for `on_disk()` and `in_memory()` - need to make mode optional

## Implementation Steps

### Step 1: Make StorageMode Optional in Constructors (Rust)

**File:** `gtars-refget/src/store.rs`

**Location:** Lines 235 and 276

**Changes:**

1. **`on_disk()` - change signature:**
```rust
// From:
pub fn on_disk<P: AsRef<Path>>(cache_path: P, mode: StorageMode) -> Result<Self>

// To:
pub fn on_disk<P: AsRef<Path>>(cache_path: P, mode: Option<StorageMode>) -> Result<Self> {
    let mode = mode.unwrap_or(StorageMode::Encoded);
    // ... rest of function
}
```

2. **`in_memory()` - change signature:**
```rust
// From:
pub fn in_memory(mode: StorageMode) -> Self

// To:
pub fn in_memory(mode: Option<StorageMode>) -> Self {
    Self::new(mode.unwrap_or(StorageMode::Encoded))
}
```

**Lines changed:** ~4

### Step 2: Add set_mode() Method with Re-encoding

**File:** `gtars-refget/src/store.rs`

**Location:** Add after `in_memory()` around line 280

**What to do:**
- Add `set_mode()` method that changes storage mode
- If switching Raw→Encoded: encode all Full sequences
- If switching Encoded→Raw: decode all Full sequences
- Stub sequences (on-disk) don't need conversion - they're loaded on-demand

**Code:**
```rust
/// Change the storage mode, re-encoding/decoding existing sequences as needed.
///
/// When switching from Raw to Encoded:
/// - All Full sequences in memory are encoded (2-bit packed)
///
/// When switching from Encoded to Raw:
/// - All Full sequences in memory are decoded back to raw bytes
///
/// Note: Stub sequences (lazy-loaded from disk) are not affected.
/// They will be loaded in the NEW mode when accessed.
pub fn set_mode(&mut self, new_mode: StorageMode) {
    if self.mode == new_mode {
        return;  // No change needed
    }

    // Re-encode/decode all Full sequences in memory
    for record in self.sequence_store.values_mut() {
        match record {
            SequenceRecord::Full { metadata, sequence } => {
                match (self.mode, new_mode) {
                    (StorageMode::Raw, StorageMode::Encoded) => {
                        // Encode: raw bytes -> 2-bit packed
                        let alphabet = lookup_alphabet(metadata.alphabet);
                        *sequence = encode_sequence(sequence, &alphabet);
                    }
                    (StorageMode::Encoded, StorageMode::Raw) => {
                        // Decode: 2-bit packed -> raw bytes
                        let decoded = decode_string_from_bytes(
                            sequence,
                            metadata.alphabet,
                            metadata.length
                        );
                        *sequence = decoded.into_bytes();
                    }
                    _ => {}  // Same mode, no conversion needed
                }
            }
            SequenceRecord::Stub(_) => {
                // Stubs don't hold sequence data, nothing to convert
            }
        }
    }

    self.mode = new_mode;
}
```

**Lines added:** ~40

### Step 3: Add Convenience Methods for Mode Switching

**File:** `gtars-refget/src/store.rs`

**Location:** After `set_mode()`

**What to do:**
- Add `enable_encoding()` - switch to Encoded mode
- Add `disable_encoding()` - switch to Raw mode

**Code:**
```rust
/// Enable 2-bit encoding for space efficiency.
/// Re-encodes any existing Raw sequences in memory.
pub fn enable_encoding(&mut self) {
    self.set_mode(StorageMode::Encoded);
}

/// Disable encoding, use raw byte storage.
/// Decodes any existing Encoded sequences in memory.
pub fn disable_encoding(&mut self) {
    self.set_mode(StorageMode::Raw);
}
```

**Lines added:** ~10

### Step 4: Update Python Bindings

**File:** `gtars-python/src/refget/mod.rs`

**Location:** Lines 656 and 680 (on_disk, in_memory classmethods)

**Changes:**

1. **Update `on_disk()` to make mode optional:**
```rust
#[classmethod]
#[pyo3(signature = (cache_path, mode=None))]
fn on_disk(_cls: &Bound<'_, PyType>, cache_path: &Bound<'_, PyAny>, mode: Option<PyStorageMode>) -> PyResult<Self> {
    let cache_path = cache_path.to_string();
    let mode_rust = mode.map(|m| m.into());
    let store = RefgetStore::on_disk(cache_path, mode_rust).map_err(...)?;
    Ok(Self { inner: store })
}
```

2. **Update `in_memory()` to make mode optional:**
```rust
#[classmethod]
#[pyo3(signature = (mode=None))]
fn in_memory(_cls: &Bound<'_, PyType>, mode: Option<PyStorageMode>) -> Self {
    let mode_rust = mode.map(|m| m.into());
    Self { inner: RefgetStore::in_memory(mode_rust) }
}
```

3. **Add `set_mode()` Python binding:**
```rust
fn set_mode(&mut self, mode: PyStorageMode) {
    self.inner.set_mode(mode.into());
}

fn enable_encoding(&mut self) {
    self.inner.enable_encoding();
}

fn disable_encoding(&mut self) {
    self.inner.disable_encoding();
}
```

**Lines changed:** ~20

### Step 5: Update Tests

**File:** `gtars-refget/src/store.rs` (test module)

**What to do:**

1. **Test default mode is Encoded:**
```rust
#[test]
fn test_default_mode_is_encoded() {
    let store = RefgetStore::in_memory(None);
    assert_eq!(store.mode, StorageMode::Encoded);
}
```

2. **Test mode switching with re-encoding:**
```rust
#[test]
fn test_set_mode_raw_to_encoded() {
    let mut store = RefgetStore::in_memory(Some(StorageMode::Raw));
    store.add_sequence_collection_from_fasta("../tests/data/fasta/base.fa").unwrap();

    // Sequences should be stored as Raw
    let seq = store.get_sequence("...digest...").unwrap();

    // Switch to Encoded
    store.set_mode(StorageMode::Encoded);

    // Same sequence should still be retrievable
    let seq2 = store.get_sequence("...digest...").unwrap();
    assert_eq!(seq, seq2);
}

#[test]
fn test_set_mode_encoded_to_raw() {
    let mut store = RefgetStore::in_memory(Some(StorageMode::Encoded));
    store.add_sequence_collection_from_fasta("../tests/data/fasta/base.fa").unwrap();

    store.disable_encoding();  // Switch to Raw

    // Should still work
    let seq = store.get_sequence("...digest...").unwrap();
    assert!(!seq.is_empty());
}
```

3. **Update existing tests that use constructors:**
   - Tests can now use simpler syntax: `RefgetStore::in_memory(None)`
   - Or explicitly: `RefgetStore::in_memory(Some(StorageMode::Encoded))`

**Lines added:** ~40 test code

### Step 6: Update Documentation

**File:** `repos/bedbase/docs/gtars/python/refget-store.md`

**What to do:**

Update examples to show new default behavior:

```markdown
## Creating a Store

```python
from gtars.refget import RefgetStore

# Simple - defaults to Encoded mode (space-efficient)
store = RefgetStore.in_memory()

# Or on-disk - also defaults to Encoded
store = RefgetStore.on_disk("/data/store")

# Explicitly specify Raw mode if needed
from gtars.refget import StorageMode
store = RefgetStore.in_memory(StorageMode.Raw)
```

## Changing Storage Mode

```python
# Start with default Encoded mode
store = RefgetStore.in_memory()
store.add_sequence_collection_from_fasta("genome.fa")

# Switch to Raw mode (decodes all sequences in memory)
store.disable_encoding()

# Switch back to Encoded (re-encodes all sequences)
store.enable_encoding()

# Or use set_mode() directly
store.set_mode(StorageMode.Raw)
```
```

**Lines changed:** ~25 docs

## Summary of Changes

### Files Modified:

1. **`gtars-refget/src/store.rs`**
   - Make mode optional in `on_disk()` (+2 lines)
   - Make mode optional in `in_memory()` (+2 lines)
   - Add `set_mode()` method (+40 lines)
   - Add `enable_encoding()` / `disable_encoding()` (+10 lines)
   - **Rust total:** ~54 lines

2. **`gtars-python/src/refget/mod.rs`**
   - Update `on_disk()` signature (+3 lines)
   - Update `in_memory()` signature (+3 lines)
   - Add `set_mode()`, `enable_encoding()`, `disable_encoding()` (+10 lines)
   - **Python bindings total:** ~16 lines

3. **Tests:** ~40 lines
4. **Docs:** ~25 lines

### Total: ~135 lines

### Before/After:

**Before:**
```python
# Verbose - must specify mode every time
store = RefgetStore.in_memory(StorageMode.Encoded)
store = RefgetStore.on_disk("/path", StorageMode.Encoded)
# No way to change mode after creation
```

**After:**
```python
# Simple - Encoded by default
store = RefgetStore.in_memory()
store = RefgetStore.on_disk("/path")

# Change mode dynamically
store.disable_encoding()  # Switch to Raw
store.enable_encoding()   # Back to Encoded
```

## Backwards compatibility

This is developmental software. We are trying to eliminate old code, not keep it around.

**Breaking changes:**
- Constructor signatures change (mode becomes optional)
- Existing code using `StorageMode.Encoded` explicitly will still work
- Existing code using `StorageMode.Raw` explicitly will still work
- Only change: mode is no longer required, defaults to Encoded

**This is not a breaking change for users** - existing code continues to work. Adding optional parameter with sensible default is backwards-compatible.
