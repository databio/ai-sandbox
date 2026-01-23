# Plan: Remove Verbose Debug Output from gtars-refget

## Problem Statement

During sequence extraction operations, gtars outputs "Raw sequence slice: [65, 84, 71, ...]" debug messages that create 2GB log files during benchmarks. This debug output must be removed or gated.

**Location:** `/home/nsheff/Dropbox/workspaces/refgenie/repos/gtars/gtars-refget/src/store.rs` line 1096

```rust
StorageMode::Raw => {
    let raw_slice: &[u8] = &sequence[start..end];
    println!("Raw sequence slice: {:?}", raw_slice);  // PROBLEM LINE
    match String::from_utf8(raw_slice.to_vec()) {
```

## Important Note

**DO NOT MAINTAIN BACKWARDS COMPATIBILITY.** This is developmental software. We are eliminating old patterns, not preserving them.

## Current State Analysis

The gtars codebase does NOT use a logging framework:
- No `log` or `tracing` crate dependencies in workspace Cargo.toml
- Uses raw `println!` statements throughout (approximately 40+ occurrences in store.rs)
- Uses `eprintln!` for error messages
- Some `println!` statements are informational (loading progress), others are debug artifacts

### Categories of println! Usage in store.rs

1. **Debug artifacts that should be removed:**
   - Line 1096: `println!("Raw sequence slice: {:?}", raw_slice);` - CRITICAL: causes 2GB logs
   - Line 2752: `println!("Do we ever get here?");` - developer question

2. **Informational progress output (useful):**
   - Line 617: `println!("Loading sequences into RefgetStore...");`
   - Line 648: `println!("  [{}] {} ({} bp)", seq_count, display_name, dr.length);`
   - Line 698: `println!("Loaded {} sequences into RefgetStore ({}) in {:.2}s.", ...);`
   - Line 2002: `println!("Writing sequences farg file: {:?}", file_path);`

3. **Warning/skip messages (useful):**
   - Line 594: `println!("Loading farg index...");`
   - Line 599: `println!("Collection already exists, skipping (use force=true to overwrite)");`

4. **Test output (acceptable in tests):**
   - Lines 2456, 2457, 2495, 2531, 2538, etc. - all in `#[cfg(test)]` blocks

## Recommended Approach

**Option A: Simple removal of debug artifacts (RECOMMENDED)**

The fastest and cleanest solution for developmental software. Simply remove the debug `println!` statements that are causing problems.

**Option B: Add proper logging framework**

A more comprehensive solution that adds the `log` crate and gates all output behind log levels. This is more work but provides a foundation for future diagnostics.

## Implementation Plan

### Phase 1: Remove Debug Artifacts (Immediate Fix)

1. **Remove the problematic debug line** in `store.rs`:
   - Delete line 1096: `println!("Raw sequence slice: {:?}", raw_slice);`

2. **Remove other debug artifacts**:
   - Delete line 2752: `println!("Do we ever get here?");`

3. **Keep informational output** (loading progress, timing) - these are useful for users and do not cause performance issues.

### Phase 2 (Optional): Add Logging Framework

If more control over output is desired in the future:

1. **Add `log` crate to Cargo.toml:**
   ```toml
   [dependencies]
   log = "0.4"
   ```

2. **Add `env_logger` for CLI:**
   ```toml
   [dependencies]
   env_logger = "0.11"
   ```

3. **Convert println! to log macros:**
   ```rust
   use log::{debug, info, warn, error};

   // Debug output (off by default)
   debug!("Raw sequence slice: {:?}", raw_slice);

   // Info output (on by default)
   info!("Loading sequences into RefgetStore...");
   info!("Loaded {} sequences in {:.2}s", count, elapsed);

   // Warnings
   warn!("Collection already exists, skipping");
   ```

4. **Update Python bindings** to initialize logging (or let Python's logging handle it via `pyo3-log`).

## Migration Strategy

This is developmental software with no backward compatibility requirements.

1. Make the changes directly to the `master` branch
2. Run `cargo test` to verify nothing breaks
3. Re-run benchmarks to confirm log file sizes are reasonable
4. No deprecation period needed

## Files to Modify

- `/home/nsheff/Dropbox/workspaces/refgenie/repos/gtars/gtars-refget/src/store.rs`
  - Delete line 1096 (Raw sequence slice debug)
  - Delete line 2752 (Do we ever get here debug)

## Testing

1. Run existing tests: `cargo test -p gtars-refget`
2. Re-run the refgetstore-benchmark suite to verify log file sizes are now reasonable
3. Verify that useful informational output (loading progress, timing) still appears

## Summary

The fix is straightforward: delete two debug `println!` statements that were left in the code. The "Raw sequence slice" line is called for every sequence extraction operation, which during benchmarks with millions of extractions produces gigabytes of output. Simply removing it solves the problem immediately.
