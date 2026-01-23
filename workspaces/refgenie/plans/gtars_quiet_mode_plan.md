# Plan: Add Quiet Mode to gtars-refget

## Overview

The gtars-refget Rust library currently uses `println!` statements for progress/debug output. These print directly to stdout, bypassing Python's `sys.stdout`, which makes it impossible to capture or suppress output when using gtars from Python (e.g., for documentation generation or automated testing).

**Goal:** Add a configurable verbosity/quiet mode to gtars-refget so output can be suppressed when used as a library.

## Problem Analysis

The library has ~40+ `println!` statements in the core files:
- `store.rs`: Progress messages during FASTA loading, sequence counts, timing
- `collection.rs`: RGSI file operations, digest computations
- `fasta.rs`: FASTA processing messages

These are useful for CLI usage but problematic for library usage where the caller wants to control output.

## Files to Read for Context

1. `/home/nsheff/Dropbox/workspaces/refgenie/repos/gtars/gtars-refget/src/store.rs` - Main RefgetStore implementation
2. `/home/nsheff/Dropbox/workspaces/refgenie/repos/gtars/gtars-refget/src/collection.rs` - SequenceCollection with println calls
3. `/home/nsheff/Dropbox/workspaces/refgenie/repos/gtars/gtars-refget/src/fasta.rs` - FASTA parsing with println calls
4. `/home/nsheff/Dropbox/workspaces/refgenie/repos/gtars/gtars-python/src/refget/mod.rs` - Python bindings

## Implementation Steps

### Step 1: Add verbosity field to RefgetStore

In `store.rs`, add a `verbose: bool` field to `RefgetStore`:

```rust
pub struct RefgetStore {
    // ... existing fields
    verbose: bool,  // Controls whether progress messages are printed
}
```

Default to `true` for backward compatibility with CLI usage.

### Step 2: Create a macro for conditional printing

Add a macro at the top of `store.rs` (or in a shared utils module):

```rust
macro_rules! vprintln {
    ($verbose:expr, $($arg:tt)*) => {
        if $verbose {
            println!($($arg)*);
        }
    };
}
```

### Step 3: Replace println! calls with vprintln!

In `store.rs`, replace all progress-related `println!` calls:

```rust
// Before
println!("Loading rgsi index...");

// After
vprintln!(self.verbose, "Loading rgsi index...");
```

### Step 4: Add verbose parameter to constructors

Update `on_disk()` and `in_memory()` to accept an optional verbose parameter:

```rust
pub fn on_disk<P: AsRef<Path>>(path: P) -> Result<Self> {
    Self::on_disk_with_options(path, true)  // verbose=true by default
}

pub fn on_disk_quiet<P: AsRef<Path>>(path: P) -> Result<Self> {
    Self::on_disk_with_options(path, false)
}

fn on_disk_with_options<P: AsRef<Path>>(path: P, verbose: bool) -> Result<Self> {
    // ... implementation
}
```

Or use a builder pattern:

```rust
pub fn on_disk<P: AsRef<Path>>(path: P) -> Result<Self> { ... }

pub fn with_verbose(mut self, verbose: bool) -> Self {
    self.verbose = verbose;
    self
}
```

### Step 5: Handle collection.rs and fasta.rs

For standalone functions like `digest_fasta()` that aren't methods on RefgetStore:

Option A: Add verbose parameter to functions:
```rust
pub fn digest_fasta<P: AsRef<Path>>(path: P, verbose: bool) -> Result<SequenceCollection>
```

Option B: Use environment variable:
```rust
let verbose = std::env::var("GTARS_VERBOSE").map(|v| v != "0").unwrap_or(true);
```

Option C: Use a thread-local or global setting (less ideal but simpler).

**Recommendation:** Option A (explicit parameter) is cleanest. For Python bindings, default verbose=False since library usage typically wants quiet mode.

### Step 6: Update Python bindings

In `gtars-python/src/refget/mod.rs`, update the bindings:

```rust
#[pyfunction]
#[pyo3(signature = (path, verbose=false))]  // Default to quiet for Python
fn digest_fasta(path: &Bound<'_, PyAny>, verbose: Option<bool>) -> PyResult<PySequenceCollection> {
    let verbose = verbose.unwrap_or(false);
    // ...
}

#[pymethods]
impl PyRefgetStore {
    #[staticmethod]
    #[pyo3(signature = (path, verbose=false))]
    fn on_disk(path: &Bound<'_, PyAny>, verbose: Option<bool>) -> PyResult<Self> {
        let verbose = verbose.unwrap_or(false);
        // ...
    }
}
```

### Step 7: Update type stubs

In `gtars.pyi`, add verbose parameter:

```python
def digest_fasta(path: str | Path, verbose: bool = False) -> SequenceCollection: ...

class RefgetStore:
    @staticmethod
    def on_disk(path: str | Path, verbose: bool = False) -> RefgetStore: ...
    @staticmethod
    def in_memory(verbose: bool = False) -> RefgetStore: ...
```

### Step 8: Keep eprintln! for actual errors

Don't suppress `eprintln!` calls - those are for actual errors that should always be visible:

```rust
eprintln!("Failed to load sequence: {}", e);  // Keep these
```

### Step 9: Update tests

Ensure tests pass with both verbose=true and verbose=false modes.

## Summary of Changes

| File | Change |
|------|--------|
| `store.rs` | Add `verbose` field, `vprintln!` macro, update ~15 println calls |
| `collection.rs` | Add verbose parameter to `from_fasta`, `from_rgsi`, update ~10 println calls |
| `fasta.rs` | Add verbose parameter to `digest_fasta`, `load_fasta`, update ~3 println calls |
| `gtars-python/src/refget/mod.rs` | Add verbose parameter to Python bindings, default False |
| `gtars.pyi` | Update type stubs with verbose parameter |

## Expected Result

After implementation:

```python
# Quiet mode (default for Python)
from gtars.refget import RefgetStore, digest_fasta

store = RefgetStore.on_disk("/path/to/store")  # No output
collection = digest_fasta("/path/to/file.fa")  # No output

# Verbose mode (opt-in)
store = RefgetStore.on_disk("/path/to/store", verbose=True)  # Shows progress
```

## DO NOT MAINTAIN BACKWARDS COMPATIBILITY

This is developmental software. The goal is to improve the API, not preserve old behavior:

- Default Python bindings to `verbose=False` (breaking change for anyone relying on output)
- Remove any deprecated verbose-related code paths
- Don't add backwards-compatibility shims
- Delete old code, don't comment it out
