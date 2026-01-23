# Plan: Fix gtars export_fasta Lazy Loading Bug

## Goal

Fix a bug in the gtars library where `export_fasta()` fails with "Collection not found" when called on a store loaded from disk via `load_local()`.

## Diagnosis Summary

**Confirmed Bug**: The `export_fasta` function directly accesses `self.name_lookup` without first ensuring the collection is loaded. When stores are loaded from disk:

1. Collections are loaded as **Stubs** (lazy loading by design)
2. `name_lookup` is **NOT populated** for stub collections (by design, per comment at line 1676-1677)
3. `name_lookup` is only populated when `ensure_collection_loaded()` is called
4. `export_fasta` directly accesses `name_lookup` without calling `ensure_collection_loaded()`
5. Result: "Collection not found" error

**Evidence**:
- Line 1676-1677 explicitly states: `// Note: name_lookup is NOT populated for stubs - it will be populated when the collection is loaded via ensure_collection_loaded()`
- Test at line 3214 confirms: `assert!(!loaded_store.is_collection_loaded(&digest), "Collection should be Stub after loading from disk")`
- `export_fasta` at line 1130 assumes `name_lookup` is populated without calling `ensure_collection_loaded`

**Reproduction**:
```python
# This works (in-memory store)
store = RefgetStore.in_memory()
store.add_sequence_collection_from_fasta(fasta_path)
store.export_fasta(digest, output_path, None, None)  # OK

# This fails (disk store loaded with load_local)
subprocess.run(['refget', 'store', 'init', '--path', store_path])
subprocess.run(['refget', 'store', 'add', fasta_path, '--path', store_path])
store = RefgetStore.load_local(store_path)
store.export_fasta(digest, output_path, None, None)  # FAILS: "Collection not found"
```

## Files to Read for Context

1. `/home/nsheff/Dropbox/workspaces/refgenie/repos/gtars/gtars-refget/src/store.rs`
   - `export_fasta()` at line 1118
   - `ensure_collection_loaded()` at line 1862
   - `load_collection_stubs_from_rgci()` at line 1642
   - `load_local()` at line 1518

## Implementation Steps

### Step 1: Fix export_fasta to call ensure_collection_loaded

In `gtars-refget/src/store.rs`, modify `export_fasta()` (around line 1127):

**Before:**
```rust
pub fn export_fasta<K: AsRef<[u8]>, P: AsRef<Path>>(
    &mut self,
    collection_digest: K,
    output_path: P,
    sequence_names: Option<Vec<&str>>,
    line_width: Option<usize>,
) -> Result<()> {
    let line_width = line_width.unwrap_or(80);
    let output_path = output_path.as_ref();
    let collection_key = collection_digest.as_ref().to_key();

    // Get the name map for this collection...
    let name_to_digest: HashMap<String, [u8; 32]> = self
        .name_lookup
        .get(&collection_key)
        ...
```

**After:**
```rust
pub fn export_fasta<K: AsRef<[u8]>, P: AsRef<Path>>(
    &mut self,
    collection_digest: K,
    output_path: P,
    sequence_names: Option<Vec<&str>>,
    line_width: Option<usize>,
) -> Result<()> {
    let line_width = line_width.unwrap_or(80);
    let output_path = output_path.as_ref();
    let collection_key = collection_digest.as_ref().to_key();

    // Ensure collection is loaded (populates name_lookup for lazy-loaded stores)
    self.ensure_collection_loaded(&collection_key)?;

    // Get the name map for this collection...
    let name_to_digest: HashMap<String, [u8; 32]> = self
        .name_lookup
        .get(&collection_key)
        ...
```

### Step 2: Verify export_fasta_from_regions has the same fix

Check if `export_fasta_from_regions()` (line 938) also needs the same fix. If it accesses `name_lookup` directly, add the same `ensure_collection_loaded` call.

### Step 3: Add a test for disk-loaded stores

Add a test that specifically tests the workflow:
1. Create store on disk via CLI or `on_disk()`
2. Load it with `load_local()`
3. Call `export_fasta()`

Example test (add to the existing test section around line 2721):
```rust
#[test]
fn test_export_fasta_after_load_local() {
    let temp_dir = tempdir().expect("Failed to create temporary directory");
    let temp_path = temp_dir.path();
    let store_path = temp_path.join("store");

    // Create test FASTA
    let fasta_content = ">chr1\nACGTACGT\n>chr2\nGGGGAAAA\n";
    let fasta_path = temp_path.join("test.fa");
    fs::write(&fasta_path, fasta_content).unwrap();

    // Create and populate store on disk
    let mut store = RefgetStore::on_disk(&store_path).unwrap();
    let collection_digest = store.add_sequence_collection_from_fasta(&fasta_path).unwrap();
    drop(store);  // Close the store

    // Load the store fresh from disk
    let mut loaded_store = RefgetStore::load_local(&store_path).unwrap();

    // This should work (was failing before fix)
    let output_path = temp_path.join("exported.fa");
    loaded_store.export_fasta(&collection_digest, &output_path, None, Some(80))
        .expect("export_fasta should work on disk-loaded stores");

    // Verify output
    let exported = fs::read_to_string(&output_path).unwrap();
    assert!(exported.contains(">chr1"));
    assert!(exported.contains("ACGTACGT"));
}
```

### Step 4: Build and run tests

```bash
cd /home/nsheff/Dropbox/workspaces/refgenie/repos/gtars
cargo test -p gtars-refget
```

### Step 5: Verify the benchmark works

Rebuild the Docker image and run the export_fasta benchmark:
```bash
cd /home/nsheff/Dropbox/workspaces/refgenie/repos/refgetstore-benchmark
./build_docker.sh
./run_all_docker.sh run export
```

## Summary

- **Lines changed**: ~2 lines added to `export_fasta()`, potentially 2 more to `export_fasta_from_regions()`
- **Test added**: 1 new test case for disk-loaded store export

## Important Note

**DO NOT MAINTAIN BACKWARDS COMPATIBILITY.** This is developmental software. The fix is a straightforward addition of `ensure_collection_loaded()` call - there's no old behavior to preserve, just a bug to fix.
