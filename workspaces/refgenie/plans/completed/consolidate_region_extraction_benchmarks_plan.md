# Plan: Consolidate Region Extraction Benchmarks

## Goal

Simplify the region extraction benchmarking by consolidating `random_access.py` and `bed_extraction.py` into a single unified module. Currently these are two separate files that essentially test the same capability (extracting subsequences given coordinates), with `region_extraction.py` serving as a thin orchestrator. This creates unnecessary code duplication and complexity.

## Analysis

### What These Tests Actually Do

**Both tests measure the exact same fundamental operation:**
- Given a list of `(chromosome, start, end)` tuples
- Extract the subsequence from each region
- Time how long it takes

**The only differences:**
1. **Region source**: random_access generates regions randomly; bed_extraction loads from BED files
2. **Execution**: random_access supports parallel execution; bed_extraction runs sequentially
3. **Extra tool**: bed_extraction includes bedtools (which requires a BED file anyway)

### Code Duplication Found

The following patterns are duplicated or near-duplicated between the files:

| Pattern | random_access.py | bed_extraction.py |
|---------|-----------------|-------------------|
| RefgetStore benchmarking | `benchmark_refgetstore_single()` | `extract_with_refgetstore()` |
| pyfaidx benchmarking | `benchmark_pyfaidx_single()` | `extract_with_pyfaidx()` |
| seqrepo benchmarking | `benchmark_seqrepo_single()` | `extract_with_seqrepo()` |
| samtools benchmarking | `benchmark_samtools_batch()` | `extract_with_samtools_batch()` |
| Store setup | Uses `create_refgetstore_variants()` | Uses `create_refgetstore_variants()` |
| bgzip setup | Uses `create_bgzipped_fasta()` | Uses `create_bgzipped_fasta()` |
| seqrepo setup | Uses `create_seqrepo()` | Uses `create_seqrepo()` |

### Current File State

```
benchmarks/random_access.py     309 lines
benchmarks/bed_extraction.py    395 lines
benchmarks/region_extraction.py 230 lines
                          Total: 934 lines
```

### Recommendation

**YES, these should be combined.** The only meaningful difference is the source of regions (random vs BED file). This is a configuration choice, not a fundamental difference in what's being tested.

## Files to Read

Before implementation:
- `benchmarks/random_access.py` - Current random access benchmark
- `benchmarks/bed_extraction.py` - Current BED extraction benchmark
- `benchmarks/region_extraction.py` - Current orchestrator
- `benchmarks/utils.py` - Shared utilities

## Concrete Steps

### Step 1: Create Unified `region_extraction.py`

Replace all three files with a single `region_extraction.py` that:

1. **Unifies extraction functions** - Single set of functions:
   - `extract_with_refgetstore(store, collection_digest, regions)`
   - `extract_with_pyfaidx(fasta, regions)`
   - `extract_with_seqrepo(seqrepo, regions)`
   - `extract_with_samtools(fasta_path, regions)`
   - `extract_with_bedtools(fasta_path, bed_path)` (BED-file-only, optional)

2. **Support multiple region sources** via CLI:
   ```
   python -m benchmarks.region_extraction --random --count 10000 --region-size 1000
   python -m benchmarks.region_extraction --bed bed_files/synthetic/
   python -m benchmarks.region_extraction --bed bed_files/synthetic/ --random --count 5000
   ```

3. **Single benchmark loop** that:
   - Accepts a list of regions (from any source)
   - Times extraction for each tool
   - Reports results consistently

4. **Keep parallel execution optional** (from random_access.py)

### Step 2: Delete Redundant Files

Remove:
- `benchmarks/random_access.py` (functionality merged)
- `benchmarks/bed_extraction.py` (functionality merged)
- Old `benchmarks/region_extraction.py` (replaced with new unified version)

### Step 3: Update Imports and References

- Update `benchmarks/__init__.py` if needed
- Update any scripts that call these benchmarks (e.g., in shell scripts, Docker files)
- Update README.md documentation

## Expected Result

### Line Count Reduction

Before:
```
benchmarks/random_access.py     309 lines
benchmarks/bed_extraction.py    395 lines
benchmarks/region_extraction.py 230 lines
                          Total: 934 lines
```

After:
```
benchmarks/region_extraction.py ~400 lines (unified)
                          Total: ~400 lines
```

**Expected reduction: ~530 lines (~57%)**

### Simplified Mental Model

Before: "Do I use random_access, bed_extraction, or region_extraction?"

After: "Use region_extraction with `--random` for synthetic tests or `--bed` for BED file tests"

### Unified Output Format

Currently the two tests produce different output formats:
- random_access: `ms_per_access`
- bed_extraction: `regions_per_second`

The unified version should output both metrics for all tests.

## Backwards Compatibility

**DO NOT MAINTAIN BACKWARDS COMPATIBILITY.**

This is developmental software. The CLI interface will change:
- Old: `python -m benchmarks.random_access`
- New: `python -m benchmarks.region_extraction --random`

Users should update their scripts to use the new interface.

## Verification

1. Run `python -m benchmarks.region_extraction --help` to verify CLI
2. Run with `--random` flag and verify results match old random_access.py output
3. Run with `--bed` flag and verify results match old bed_extraction.py output
4. Compare line counts before/after
5. Verify all tools are benchmarked correctly

## Summary Template

After implementation, document:
- Before/after line counts
- Old CLI → New CLI mapping
- Any features added/removed
- Test results verification
