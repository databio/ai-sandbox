# Plan: Fix RefgetStore Deduplication Benchmark

## Goal

Fix the deduplication benchmark to properly demonstrate RefgetStore's storage savings when storing multiple genome "flavors" (same sequences with different naming conventions).

## Problem Diagnosis

### What's Wrong

Looking at the current results (`results/deduplication.csv`) and plot (`plots/deduplication_storage.png`):

```
Genome 1: medium_genome_ensembl.fa.gz  →  1.49 MB gzip, store: 1.23 MB
Genome 2: medium_genome_ucsc.fa        →  1.49 MB gzip, store: 1.23 MB (no growth!)
Genome 3: medium_genome_ucsc.fa.gz     →  1.49 MB gzip, store: 1.23 MB (no growth!)
Genome 4-10: mini_genome_* / mini_pangenome_*  →  ~10 KB each (noise)
```

The "cumulative gzip" line shoots up steeply for genomes 1-3 (large files) then nearly flatlines for genomes 4-10 (tiny files). This creates a misleading visualization where it looks like deduplication "stops working" at genome 3.

### Root Causes

1. **Mixed file sizes**: The test data mixes ~50MB medium genomes with ~30KB mini genomes
2. **Alphabetical ordering**: Files are sorted alphabetically, putting medium_genome_* first
3. **Scale mismatch**: Mini genomes are 0.02% the size of medium genomes - they're invisible noise
4. **Wrong test scenario**: Adding mini_pangenome files tests pangenome dedup (which doesn't work - sequences differ), not naming convention dedup (which does work)

### What We Actually Want to Demonstrate

**Primary use case**: A lab has downloaded GRCh38 in multiple "flavors":
- hg38.fa (UCSC naming: chr1, chr2, chrX)
- GRCh38.fa (Ensembl naming: 1, 2, X)
- GCA_000001405.15.fa (NCBI/GenBank naming: NC_000001.11, etc.)

All three files are ~3GB each. Traditional storage: 9GB. RefgetStore: 3GB (3x savings).

**Secondary demonstration**: Pangenome haplotypes do NOT deduplicate well (sequences actually differ).

## Plan

### Step 1: Redesign Test Data Generation

**File: `data/generate_test_data.py`**

Create two separate benchmark datasets:

**Dataset A: `naming_variants/` (THE KEY DEMO)**
- Generate ONE realistic medium genome (~50MB, 5 chromosomes)
- Create 3-5 naming variants of the SAME genome:
  - `genome_ucsc.fa.gz` (chr1, chr2, chr3, chr4, chrM)
  - `genome_ensembl.fa.gz` (1, 2, 3, 4, MT)
  - `genome_ncbi.fa.gz` (NC_000001.1, NC_000002.1, ...)
  - `genome_genbank.fa.gz` (CM000663.2, CM000664.2, ...)
  - `genome_refseq.fa.gz` (NC_000001.15, ...)
- All 5 files have IDENTICAL sequences, only chromosome names differ
- Expected result: 5x storage savings (250MB gzip → 50MB store)

**Dataset B: `pangenome/` (CONTROL - shows what doesn't deduplicate)**
- Generate ONE base genome
- Create 3 haplotypes with 0.1% SNP differences
- All sequences are DIFFERENT
- Expected result: ~1x storage (no significant deduplication)

**Delete the current mixed approach**: Remove mini_genome_* and medium_genome_* from test data.

### Step 2: Update Deduplication Benchmark

**File: `benchmarks/deduplication.py`**

Changes:
1. Default to `--dataset naming_variants` (the key demo)
2. Add clear dataset descriptions in output
3. Improve CSV output with columns:
   - `dataset`: "naming_variants" or "pangenome"
   - `genome_added`: filename
   - `genome_description`: "UCSC naming", "Ensembl naming", etc.
   - `sequences_unique`: boolean (are sequences identical to existing?)
4. Print expected vs actual results interpretation

### Step 3: Update Visualization

**File: `analysis/figures.py`**

Changes for `plot_deduplication()`:
1. Add annotations explaining what each genome represents
2. Show "Naming variants only" and "Pangenome" as separate panels or plots
3. Add expected outcome text: "Naming variants: ~Nx savings expected"
4. Improve axis labels and title for clarity

### Step 4: Add Clear Dataset Descriptions

**File: `data/README.md`** (new)

Explain:
- What each dataset demonstrates
- Why naming variant deduplication matters (real-world use case)
- Why pangenome doesn't deduplicate (different sequences)
- File sizes and expected results

### Step 5: Update Main README

**File: `README.md`**

- Clarify that the benchmark demonstrates naming convention deduplication
- Add expected results table
- Remove references to mixed mini/medium genome approach

## Files to Read for Context

- `/home/nsheff/Dropbox/workspaces/refgenie/repos/refgetstore-benchmark/benchmarks/deduplication.py` - Current benchmark logic
- `/home/nsheff/Dropbox/workspaces/refgenie/repos/refgetstore-benchmark/data/generate_test_data.py` - Test data generation
- `/home/nsheff/Dropbox/workspaces/refgenie/repos/refgetstore-benchmark/analysis/figures.py` - Visualization code
- `/home/nsheff/Dropbox/workspaces/refgenie/repos/refgetstore-benchmark/results/deduplication.csv` - Current results
- `/home/nsheff/Dropbox/workspaces/refgenie/repos/refgetstore-benchmark/README.md` - Documentation

## Concrete Implementation Steps

1. **Delete existing test data**: `rm -rf data/test/*.fa*`

2. **Rewrite `data/generate_test_data.py`**:
   - Create `data/test/naming_variants/` directory
   - Generate one ~50MB genome with 5 naming variants
   - Create `data/test/pangenome/` directory
   - Generate one base genome with 3 mutated haplotypes
   - Remove all mini_genome_* and mixed medium_genome_* code

3. **Update `benchmarks/deduplication.py`**:
   - Change default dataset from "test" to "naming_variants"
   - Update dataset paths: `data/test/naming_variants/`, `data/test/pangenome/`
   - Add genome description metadata to results
   - Improve interpretation messages

4. **Update `analysis/figures.py`**:
   - Add dataset-specific annotations
   - Improve titles: "Storage Deduplication: Same Genome, Different Naming Conventions"
   - Add legend explaining what's being compared

5. **Regenerate all results**:
   ```bash
   python data/generate_test_data.py
   python -m benchmarks.deduplication --dataset naming_variants
   python -m benchmarks.deduplication --dataset pangenome
   python -m analysis.figures
   ```

6. **Update README.md** with new instructions and expected results

## Expected Outcomes

### naming_variants dataset (5 files, same 50MB genome)
- Cumulative gzip: ~7.5 MB (5 × 1.5 MB)
- RefgetStore: ~1.5 MB (only stores sequences once)
- **Savings: 5x**

### pangenome dataset (3 haplotypes with SNPs)
- Cumulative gzip: ~4.5 MB (3 × 1.5 MB)
- RefgetStore: ~4.5 MB (sequences differ, no deduplication)
- **Savings: ~1x (none)**

## Summary

Before: Confusing mixed test data with mini and medium genomes, creating misleading "plateau at genome 3" visual.

After: Two clean, focused benchmark datasets that clearly demonstrate:
1. **Naming variants**: Same sequences, different names → massive deduplication
2. **Pangenome**: Different sequences → no deduplication (control)

## Important Notes

- **DO NOT MAINTAIN BACKWARDS COMPATIBILITY** - This is developmental software. Delete old test data formats entirely.
- The old CSV format with mixed columns can be deleted and replaced with cleaner output.
- Focus on making the ONE key demo (naming variant deduplication) crystal clear.
