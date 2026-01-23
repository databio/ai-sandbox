# Plan: Add Timing Information to Sequence Loading Message

## Goal

Add elapsed time to the "Loaded X sequences into refget SeqColStore." message to help users understand performance.

## Difficulty Assessment

**Very easy** - This is a trivial change requiring ~5 lines of code.

## Files to Review

1. **`/home/nsheff/workspaces/intervals/repos/gtars/gtars-refget/src/store.rs`**
   - Lines 372-465: `add_sequence_collection_from_fasta()` method
   - Line 390: Where "Loading sequences..." message is printed (start timer here)
   - Line 459: Where "Loaded X sequences..." message is printed (end timer here)

## Problem Diagnosis

**Current behavior:**
```
Loading sequences into refget SeqColStore...
  [1] chrX (8 bp)
  [2] chr1 (4 bp)
  [3] chr2 (4 bp)
  ...
Loaded 420 sequences into refget SeqColStore.
```

**Missing:** No indication of how long the loading took.

**Root cause:** No timing measurement between the start (line 390) and end (line 459) of sequence loading.

## Implementation Steps

### Step 1: Start Timer After Printing "Loading sequences..."

**File:** `/home/nsheff/workspaces/intervals/repos/gtars/gtars-refget/src/store.rs`

**Location:** Line 390-391

**What to do:**
- Import `std::time::Instant` at the top of the file (or use existing import)
- After `println!("Loading sequences into refget SeqColStore...");`
- Add: `let start_time = Instant::now();`

**Change:** +1 line (plus import if needed)

### Step 2: Calculate and Display Elapsed Time

**Location:** Line 459

**What to do:**
- Replace the current println with elapsed time calculation and formatted output
- Calculate: `let elapsed = start_time.elapsed();`
- Format message to include time in appropriate units (seconds for < 60s, minutes:seconds for longer)

**Example output:**
```rust
let elapsed = start_time.elapsed();
println!("Loaded {} sequences into refget SeqColStore in {:.2}s.", seq_count, elapsed.as_secs_f64());
```

**Change:** ~3 lines

### Step 3: (Optional) More Readable Time Formatting

**What to do:**
- If elapsed time is > 60 seconds, format as "Xm Ys" instead of just seconds
- Keep it simple - just show seconds with 2 decimal places for most cases

**Example:**
```rust
let elapsed = start_time.elapsed();
let secs = elapsed.as_secs_f64();
if secs >= 60.0 {
    println!("Loaded {} sequences into refget SeqColStore in {:.0}m {:.1}s.",
             seq_count, secs / 60.0, secs % 60.0);
} else {
    println!("Loaded {} sequences into refget SeqColStore in {:.2}s.", seq_count, secs);
}
```

**Skip this if keeping it simple** - just use `.as_secs_f64()` with 2 decimal places.

## Summary of Changes

### Files Modified:

1. **`gtars-refget/src/store.rs`**
   - Add `use std::time::Instant;` import (if not already present)
   - Start timer at line 391 (+1 line)
   - Calculate elapsed time and update message at line 459 (+2-3 lines)
   - **Total:** ~4 lines

### Total Lines Changed: ~4 lines

### Before/After Output:

**Before:**
```
Loaded 420 sequences into refget SeqColStore.
```

**After:**
```
Loaded 420 sequences into refget SeqColStore in 2.34s.
```

## IMPORTANT: No Backwards Compatibility Requirements

This is developmental software. The message format is for human consumption, not machine parsing. Changing the output format is fine.
