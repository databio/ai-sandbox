# Plan: Clean Up `refget store add` CLI Messaging

## Goal

Simplify and clarify the console output when adding a FASTA file to a RefgetStore. The current output is confusing with duplicate messages, debug-level information, and unclear progress indication.

## Current State (Problem)

When running `refget store add <file> -p <store>`, the user sees:

```
Processing FASTA file: /path/to/file.fa.gz
lvl1 digest: 7sLU_buKTJK1jP-y_BwN2nt5ee0aI4f4
Loading rgsi index...
from path with cache: reading from file: "/path/to/file.fa.gz"
RGSI file path: "/path/to/file.rgsi"
Computing digests...: "/path/to/file.rgsi"
Processing FASTA file: /path/to/file.fa.gz
lvl1 digest: 7sLU_buKTJK1jP-y_BwN2nt5ee0aI4f4
Writing collection rgsi file: "/path/to/file.rgsi"
RGSI file written to "/path/to/file.rgsi"
Writing sequences rgsi file: "/home/user/store/sequences.rgsi"
Loading sequences into RefgetStore...
  [1] chr1 (183079594 bp)
  [2] chr2 (120021262 bp)
  [3] chr3 (118557555 bp)
  ...
Loaded 610 sequences into RefgetStore (Encoded) in 10.67s.
{
  "digest": "7sLU_buKTJK1jP-y_BwN2nt5ee0aI4f4",
  "fasta": "/path/to/file.fa.gz",
  "sequences": 610
}
```

## Issues

1. **Duplicate "Processing FASTA file"** - The file is processed twice: once by CLI's `fasta_to_digest()` call and again by `add_sequence_collection_from_fasta()`
2. **Debug-level messages** - "from path with cache", "RGSI file path", "lvl1 digest" are implementation details
3. **Redundant write confirmation** - "Writing collection rgsi file" + "RGSI file written" say the same thing
4. **Confusing terminology** - "Processing" vs "Computing digests" vs "Loading" unclear to users
5. **Redundant summary** - Both "Loaded X sequences... in Ys" and JSON blob; don't need both

## Target State

Clean, concise output:

```
Importing: /path/to/file.fa.gz
Added abc123xyz (610 seqs) in 23.4s [12.1s digest + 11.3s encode]
{
  "digest": "abc123xyz",
  "fasta": "/path/to/file.fa.gz",
  "sequences": 610
}
```

## Files to Read for Context

1. `repos/gtars/gtars-refget/src/fasta.rs` - Lines 70-100 (digest_fasta function)
2. `repos/gtars/gtars-refget/src/collection.rs` - Lines 460-545 (from_fasta, from_path_with_cache)
3. `repos/gtars/gtars-refget/src/store.rs` - Lines 588-705 (add_sequence_collection_from_fasta_internal)
4. `repos/refget/refget/cli/store.py` - Lines 171-240 (add command)
5. `repos/refget/refget/processing/fasta.py` - Lines 13-46 (fasta_to_seqcol_dict, fasta_to_digest)

## Implementation Steps

### Step 1: Remove CLI Double-Processing

**File:** `repos/refget/refget/cli/store.py`

The CLI calls `fasta_to_digest()` at line 219 to get the digest upfront, then calls `add_sequence_collection_from_fasta()` at line 222 which computes it again.

**Change:** Remove the separate `fasta_to_digest()` call. Instead:
- Call `add_sequence_collection_from_fasta()` first
- Extract the digest from the store after adding

This eliminates one full pass through the FASTA file.

### Step 2: Remove Debug/Implementation-Detail Messages in collection.rs

**File:** `repos/gtars/gtars-refget/src/collection.rs`

Remove these println! statements:
- Line 232: `println!("lvl1 digest: {}", digest)` - internal implementation detail
- Lines 468-469: `println!("From_rgsi...")`, `println!("RGSI file path...")` - debug info
- Lines 512-516: `println!("from path with cache...")`, `println!("RGSI file path...")` - debug info
- Line 519: `println!("Reading from existing rgsi file...")` - debug info
- Line 526: `println!("Computing digests...")` - redundant with Processing message
- Lines 535, 537-540: RGSI write confirmations - verbose
- Line 563: `println!("Writing collection rgsi file...")` - verbose

### Step 3: Clean Up Store Messages and Fix Timing in store.rs

**File:** `repos/gtars/gtars-refget/src/store.rs`

**Problem:** The current timer (line 618) only times the second pass (loading sequences). The first pass (computing digests via `SequenceCollection::from_fasta()`) is not timed.

**Fix:** Use two timers to show both phases:

```rust
fn add_sequence_collection_from_fasta_internal(...) {
    // Phase 1: Digest computation
    let digest_start = Instant::now();
    let seqcol = SequenceCollection::from_fasta(&file_path)?;
    let digest_elapsed = digest_start.elapsed();

    // ... setup ...

    // Phase 2: Load/encode sequences
    let encode_start = Instant::now();
    while let Some(record) = fasta_reader.next() {
        // ...
    }
    let encode_elapsed = encode_start.elapsed();

    // Final summary with both times
    if !self.quiet {
        println!(
            "Added {} ({} seqs) in {:.1}s [{:.1}s digest + {:.1}s encode]",
            seqcol.digest,
            seq_count,
            digest_elapsed.as_secs_f64() + encode_elapsed.as_secs_f64(),
            digest_elapsed.as_secs_f64(),
            encode_elapsed.as_secs_f64()
        );
    }
}
```

**Output example:**
```
Added abc123xyz (610 seqs) in 23.4s [12.1s digest + 11.3s encode]
```

**Other changes:**
- Remove line 594: `println!("Loading rgsi index...")` - confusing terminology
- Remove line 1440: `println!("Writing sequences rgsi file...")` - too verbose

### Step 4: Clean Up fasta.rs Messages

**File:** `repos/gtars/gtars-refget/src/fasta.rs`

- Line 77: Keep `println!("Processing FASTA file: {}")` but rename to `Importing: {}`
- Line 435: Remove `println!("Loading FASTA file with data: {}")` - redundant

### Step 5: Update CLI to Print Single Clear Header

**File:** `repos/refget/refget/cli/store.py`

Print one clear message at the start:
```python
print(f"Importing: {fasta.resolve()}", file=sys.stderr)
```

Then let gtars handle progress messages.

### Step 6: Add Quiet Mode

**Architecture Decision:** Where should quiet mode live?

**Option A: Library-level flag** (Recommended for now)
- Add `quiet: bool` field to `RefgetStore` struct in `store.rs`
- Add `set_quiet(&mut self, quiet: bool)` method
- Wrap all remaining println! statements with `if !self.quiet { ... }`
- Expose via Python bindings: `store.quiet = True` or `store.set_quiet(True)`
- CLI adds `--quiet/-q` flag that sets `store.quiet = True` before operations

**Option B: Silent library** (Cleaner but more work)
- Remove ALL println! from gtars-refget library
- Libraries shouldn't print by default - callers decide what to show
- Return progress info via callbacks or structured return values
- CLI handles all user-facing output based on return data

**Recommendation:** Start with Option A (simpler). The quiet flag gives immediate control. Later, if needed, refactor to Option B for a cleaner library API.

**Implementation for Option A:**

1. **File:** `repos/gtars/gtars-refget/src/store.rs`
   - Add field to RefgetStore struct: `quiet: bool`
   - Initialize to `false` in `new()`, `on_disk()`, `in_memory()`
   - Add method: `pub fn set_quiet(&mut self, quiet: bool) { self.quiet = quiet; }`
   - Wrap println! statements: `if !self.quiet { println!(...); }`

2. **File:** `repos/gtars/gtars-python/src/refget/store.rs`
   - Add Python binding: `fn set_quiet(&mut self, quiet: bool)`
   - Optionally add property: `#[getter] fn quiet(&self) -> bool`

3. **File:** `repos/refget/refget/cli/store.py`
   - Add to `add` command:
     ```python
     quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress progress output")
     ```
   - Before operations: `if quiet: store.set_quiet(True)`

## Verification

After changes, the output should look like:

```
Importing: /path/to/file.fa.gz
Added abc123xyz (610 seqs) in 23.4s [12.1s digest + 11.3s encode]
{
  "digest": "abc123xyz",
  "fasta": "/path/to/file.fa.gz",
  "sequences": 610
}
```

The timing breakdown shows:
- **digest** - First pass: computing SHA512 digests for each sequence
- **encode** - Second pass: bit-packing sequences and writing to store

With `--quiet` flag:
```
{
  "digest": "abc123xyz",
  "fasta": "/path/to/file.fa.gz",
  "sequences": 610
}
```

## Summary of Changes

| Component | Before | After |
|-----------|--------|-------|
| collection.rs | 12 debug println! statements | 0 (all removed) |
| store.rs | 4 verbose println! statements | 1 clean summary + quiet flag |
| fasta.rs | 2 println! statements | 1 progress indicator |
| CLI store.py | Double FASTA processing | Single processing + `--quiet` flag |
| RefgetStore struct | No verbosity control | `quiet: bool` field + `set_quiet()` method |
| Python bindings | No verbosity control | `store.set_quiet(True)` method |

## DO NOT Maintain Backwards Compatibility

This is developmental software. Old messaging behavior is not an API contract. Remove all the verbose/debug messages without deprecation warnings or configuration options to preserve old behavior.
