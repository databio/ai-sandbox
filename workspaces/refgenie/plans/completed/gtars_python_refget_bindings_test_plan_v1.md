# Implementation Plan: Meaningful Tests for gtars Refget Module

This plan covers test coverage for both:
- **Part I:** Python bindings (`gtars-python/src/refget/mod.rs`) tested via pytest
- **Part II:** Rust library (`gtars-refget/src/collection.rs`) tested via `#[cfg(test)]`

---

# Part I: Python Binding Tests (pytest)

## The Issue

The file `gtars-python/src/refget/mod.rs` contains Python bindings for the gtars refget module, but several important functions and methods lack test coverage. The existing `test_refget.py` covers basic functionality but misses:

1. **`compute_fai()`** - FASTA index computation function (completely untested)
2. **`FaiRecord` and `FaiMetadata`** - FAI data structures (untested)
3. **`SequenceCollectionMetadata`** - Collection metadata class (untested)
4. **Collection inspection methods** - `list_collections()`, `get_collection_metadata()`, `is_collection_loaded()`
5. **Sequence enumeration methods** - `sequence_metadata()`, `sequence_records()`
6. **Export methods** - `export_fasta()`, `export_fasta_by_digests()`
7. **`SequenceCollection.write_fasta()`** - Writing collections to FASTA
8. **Python protocol methods** - `__iter__`, `__len__`, `__getitem__` on collections/store
9. **`quiet` mode** - Store quiet mode for suppressing output

## Files to Read for Context

- `gtars-python/src/refget/mod.rs` - The bindings being tested (already read)
- `gtars-python/tests/test_refget.py` - Existing tests (already read)
- `tests/data/fasta/base.fa` - Test FASTA file (already read)

## Implementation Steps

### Step 1: Add tests for `compute_fai()` function

This is a completely untested function. Test that it:
- Returns a list of `FaiRecord` objects for a FASTA file
- Each record has `name`, `length`, and `fai` attributes
- FAI metadata includes `offset`, `line_bases`, `line_bytes`
- Returns `fai=None` for gzipped files (verify with a gzipped test file if available)

```python
def test_compute_fai():
    """Test compute_fai() returns correct FAI records"""
    from gtars.refget import compute_fai

    fasta_path = "../tests/data/fasta/base.fa"
    fai_records = compute_fai(fasta_path)

    # Should have 3 records for base.fa
    assert len(fai_records) == 3

    # Check first record structure
    rec = fai_records[0]
    assert rec.name == "chrX"
    assert rec.length == 8
    assert rec.fai is not None
    assert rec.fai.offset > 0  # Byte offset after header
    assert rec.fai.line_bases == 8  # All bases on one line
    assert rec.fai.line_bytes == 9  # 8 bases + newline
```

### Step 2: Add tests for SequenceCollection Pythonic interface

Test `__len__`, `__getitem__`, and `__iter__`:

```python
def test_sequence_collection_pythonic_interface():
    """Test SequenceCollection supports len(), indexing, and iteration"""
    from gtars.refget import digest_fasta

    result = digest_fasta("../tests/data/fasta/base.fa")

    # Test __len__
    assert len(result) == 3

    # Test __getitem__ with positive index
    assert result[0].metadata.name == "chrX"
    assert result[1].metadata.name == "chr1"
    assert result[2].metadata.name == "chr2"

    # Test __getitem__ with negative index
    assert result[-1].metadata.name == "chr2"
    assert result[-3].metadata.name == "chrX"

    # Test index out of range
    with pytest.raises(IndexError):
        _ = result[10]

    # Test iteration
    names = [seq.metadata.name for seq in result]
    assert names == ["chrX", "chr1", "chr2"]
```

### Step 3: Add tests for RefgetStore Pythonic interface

Test `__len__` and `__iter__`:

```python
def test_refget_store_pythonic_interface():
    """Test RefgetStore supports len() and iteration"""
    store = RefgetStore.in_memory()
    store.add_sequence_collection_from_fasta("../tests/data/fasta/base.fa")

    # Test __len__
    assert len(store) == 3

    # Test iteration yields SequenceMetadata
    count = 0
    for seq_meta in store:
        assert hasattr(seq_meta, 'name')
        assert hasattr(seq_meta, 'length')
        assert hasattr(seq_meta, 'sha512t24u')
        count += 1
    assert count == 3
```

### Step 4: Add tests for collection inspection methods

Test `list_collections()`, `get_collection_metadata()`, `is_collection_loaded()`:

```python
def test_collection_inspection_methods():
    """Test collection listing and metadata retrieval"""
    store = RefgetStore.in_memory()
    fasta_path = "../tests/data/fasta/base.fa"
    store.add_sequence_collection_from_fasta(fasta_path)

    # Get expected digest
    result = digest_fasta(fasta_path)
    expected_digest = result.digest

    # Test list_collections
    collections = store.list_collections()
    assert len(collections) == 1
    assert expected_digest in collections

    # Test get_collection_metadata
    meta = store.get_collection_metadata(expected_digest)
    assert meta is not None
    assert meta.digest == expected_digest
    assert meta.n_sequences == 3
    assert meta.names_digest == result.lvl1.names_digest
    assert meta.sequences_digest == result.lvl1.sequences_digest
    assert meta.lengths_digest == result.lvl1.lengths_digest

    # Test str/repr
    assert expected_digest in str(meta)
    assert "n_sequences=3" in repr(meta)

    # Test is_collection_loaded (in-memory store should be loaded)
    assert store.is_collection_loaded(expected_digest)

    # Test non-existent collection
    assert store.get_collection_metadata("nonexistent") is None
```

### Step 5: Add tests for sequence enumeration methods

Test `sequence_metadata()` and `sequence_records()`:

```python
def test_sequence_enumeration_methods():
    """Test sequence_metadata() and sequence_records() methods"""
    store = RefgetStore.in_memory()
    store.add_sequence_collection_from_fasta("../tests/data/fasta/base.fa")

    # Test sequence_metadata - returns metadata only
    metadata_list = store.sequence_metadata()
    assert len(metadata_list) == 3
    for meta in metadata_list:
        assert hasattr(meta, 'name')
        assert hasattr(meta, 'length')
        assert hasattr(meta, 'sha512t24u')
        assert hasattr(meta, 'md5')

    # Test sequence_records - returns full records
    records_list = store.sequence_records()
    assert len(records_list) == 3
    for rec in records_list:
        assert hasattr(rec, 'metadata')
        assert hasattr(rec, 'sequence')
        # In-memory store should have sequence data
        assert rec.sequence is not None or rec.decode() is not None
```

### Step 6: Add tests for export_fasta() and export_fasta_by_digests()

```python
def test_export_fasta():
    """Test export_fasta() exports full collection or subset"""
    store = RefgetStore.in_memory()
    fasta_path = "../tests/data/fasta/base.fa"
    store.add_sequence_collection_from_fasta(fasta_path)

    result = digest_fasta(fasta_path)
    collection_digest = result.digest

    with tempfile.TemporaryDirectory() as tmpdir:
        # Export all sequences
        output_path = os.path.join(tmpdir, "all.fa")
        store.export_fasta(collection_digest, output_path, None, None)

        with open(output_path) as f:
            content = f.read()
        assert ">chrX" in content
        assert ">chr1" in content
        assert ">chr2" in content

        # Export subset
        subset_path = os.path.join(tmpdir, "subset.fa")
        store.export_fasta(collection_digest, subset_path, ["chr1", "chr2"], 60)

        with open(subset_path) as f:
            subset_content = f.read()
        assert ">chrX" not in subset_content
        assert ">chr1" in subset_content
        assert ">chr2" in subset_content

def test_export_fasta_by_digests():
    """Test export_fasta_by_digests() exports specific sequences by digest"""
    store = RefgetStore.in_memory()
    store.add_sequence_collection_from_fasta("../tests/data/fasta/base.fa")

    # Get digests for chr1 and chr2
    sha_chr1 = sha512t24u_digest(b"GGAA")  # chr1 sequence
    sha_chr2 = sha512t24u_digest(b"GCGC")  # chr2 sequence

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "by_digest.fa")
        store.export_fasta_by_digests([sha_chr1, sha_chr2], output_path, None)

        with open(output_path) as f:
            content = f.read()

        # Should contain chr1 and chr2 but NOT chrX
        assert "GGAA" in content
        assert "GCGC" in content
        # chrX sequence should not be present
        assert "TTGGGGAA" not in content
```

### Step 7: Add tests for SequenceCollection.write_fasta()

```python
def test_sequence_collection_write_fasta():
    """Test SequenceCollection.write_fasta() method"""
    from gtars.refget import load_fasta

    # load_fasta returns collection with data
    collection = load_fasta("../tests/data/fasta/base.fa")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "written.fa")
        collection.write_fasta(output_path)

        with open(output_path) as f:
            content = f.read()

        assert ">chrX" in content
        assert "TTGGGGAA" in content
        assert ">chr1" in content
        assert "GGAA" in content

        # Test with custom line width
        output_path2 = os.path.join(tmpdir, "written2.fa")
        collection.write_fasta(output_path2, line_width=4)

        with open(output_path2) as f:
            content2 = f.read()
        # With line_width=4, TTGGGGAA should be split
        assert "TTGG\n" in content2 or "GGAA\n" in content2
```

### Step 8: Add tests for quiet mode

```python
def test_quiet_mode():
    """Test store quiet mode suppresses output"""
    store = RefgetStore.in_memory()

    # Test getter
    assert store.quiet == False

    # Test setter
    store.set_quiet(True)
    assert store.quiet == True

    store.set_quiet(False)
    assert store.quiet == False
```

### Step 9: Add tests for collections() method

```python
def test_collections_method():
    """Test store.collections() returns SequenceCollection objects"""
    store = RefgetStore.in_memory()
    fasta_path = "../tests/data/fasta/base.fa"
    store.add_sequence_collection_from_fasta(fasta_path)

    collections = store.collections()
    assert len(collections) == 1

    coll = collections[0]
    assert hasattr(coll, 'digest')
    assert hasattr(coll, 'sequences')
    assert hasattr(coll, 'lvl1')
    assert len(coll.sequences) == 3
```

### Step 10: Add test for str/repr methods on various types

```python
def test_string_representations():
    """Test __str__ and __repr__ for all types"""
    from gtars.refget import (
        digest_fasta, compute_fai, RefgetStore,
        AlphabetType, RetrievedSequence
    )

    fasta_path = "../tests/data/fasta/base.fa"

    # SequenceCollection
    coll = digest_fasta(fasta_path)
    assert "3 sequences" in str(coll)
    assert "SequenceCollection" in repr(coll)

    # SequenceRecord
    rec = coll.sequences[0]
    assert "chrX" in str(rec)
    assert "SequenceRecord" in repr(rec)

    # SequenceMetadata
    meta = rec.metadata
    assert "chrX" in str(meta)
    assert "SequenceMetadata" in repr(meta)

    # SeqColDigestLvl1
    lvl1 = coll.lvl1
    assert "SeqColDigestLvl1" in str(lvl1)
    assert "SeqColDigestLvl1" in repr(lvl1)

    # FaiRecord
    fai_records = compute_fai(fasta_path)
    fai = fai_records[0]
    assert "chrX" in str(fai)
    assert "FaiRecord" in repr(fai)

    # FaiMetadata
    if fai.fai:
        assert "FaiMetadata" in str(fai.fai)
        assert "FaiMetadata" in repr(fai.fai)

    # AlphabetType
    assert str(meta.alphabet) in ["dna2bit", "dna3bit", "dnaio", "protein", "ASCII", "Unknown"]

    # RetrievedSequence
    rs = RetrievedSequence(sequence="ATGC", chrom_name="chr1", start=0, end=4)
    assert "chr1" in str(rs)
    assert "RetrievedSequence" in repr(rs)

    # RefgetStore
    store = RefgetStore.in_memory()
    assert "RefgetStore" in repr(store)
    assert "memory-only" in repr(store)
```

---

# Part II: Rust Tests for collection.rs

## The Issue

The file `gtars-refget/src/collection.rs` has existing tests (lines 702-932) but they only cover:
- `decode()` method (8 tests for various alphabets and data states)
- `SequenceCollection` iterator

**Untested functionality:**

1. **`SequenceCollectionMetadata`** - `from_sequences()`, `from_collection()`, `to_lvl1()`
2. **`SequenceCollectionRecord`** - `metadata()`, `sequences()`, `has_sequences()`, `with_sequences()`, `to_collection()`, `write_collection_rgsi()`
3. **`SeqColDigestLvl1`** - `to_digest()`, `from_metadata()`
4. **`SequenceRecord`** - `metadata()`, `sequence()`, `has_data()`, `with_data()`, `to_file()`
5. **`SequenceMetadata`** - `disk_size()`
6. **`SequenceCollection`** - `from_fasta()`, `from_rgsi()`, `from_records()`, `from_path_with_cache()`, `write_collection_rgsi()`, `write_rgsi()`, `to_record()`, `write_fasta()`
7. **`Display` implementations** - for SequenceCollection, SequenceRecord
8. **`From<SequenceCollection>` trait** - conversion to SequenceCollectionRecord

## Implementation Steps

### Step 11: Add tests for SeqColDigestLvl1

```rust
#[test]
fn test_seqcol_digest_lvl1_from_metadata() {
    // Test computing lvl1 digests from sequence metadata
    let seqcol = digest_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let metadata_refs: Vec<&SequenceMetadata> = seqcol.sequences.iter()
        .map(|r| r.metadata())
        .collect();

    let lvl1 = SeqColDigestLvl1::from_metadata(&metadata_refs);

    // Verify digests are non-empty and valid base64url
    assert!(!lvl1.names_digest.is_empty());
    assert!(!lvl1.sequences_digest.is_empty());
    assert!(!lvl1.lengths_digest.is_empty());

    // Verify they match what the collection has
    assert_eq!(lvl1.names_digest, seqcol.lvl1.names_digest);
    assert_eq!(lvl1.sequences_digest, seqcol.lvl1.sequences_digest);
    assert_eq!(lvl1.lengths_digest, seqcol.lvl1.lengths_digest);
}

#[test]
fn test_seqcol_digest_lvl1_to_digest() {
    // Test that to_digest() produces consistent collection digest
    let seqcol = digest_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let computed_digest = seqcol.lvl1.to_digest();
    assert_eq!(computed_digest, seqcol.digest);
}
```

### Step 12: Add tests for SequenceCollectionMetadata

```rust
#[test]
fn test_sequence_collection_metadata_from_sequences() {
    let seqcol = load_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let meta = SequenceCollectionMetadata::from_sequences(
        &seqcol.sequences,
        Some(PathBuf::from("../tests/data/fasta/base.fa"))
    );

    assert_eq!(meta.digest, seqcol.digest);
    assert_eq!(meta.n_sequences, 3);
    assert_eq!(meta.names_digest, seqcol.lvl1.names_digest);
    assert!(meta.file_path.is_some());
}

#[test]
fn test_sequence_collection_metadata_from_collection() {
    let seqcol = digest_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let meta = SequenceCollectionMetadata::from_collection(&seqcol);

    assert_eq!(meta.digest, seqcol.digest);
    assert_eq!(meta.n_sequences, seqcol.sequences.len());
    assert_eq!(meta.names_digest, seqcol.lvl1.names_digest);
}

#[test]
fn test_sequence_collection_metadata_to_lvl1() {
    let seqcol = digest_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let meta = SequenceCollectionMetadata::from_collection(&seqcol);
    let lvl1 = meta.to_lvl1();

    assert_eq!(lvl1.names_digest, seqcol.lvl1.names_digest);
    assert_eq!(lvl1.sequences_digest, seqcol.lvl1.sequences_digest);
    assert_eq!(lvl1.lengths_digest, seqcol.lvl1.lengths_digest);
}
```

### Step 13: Add tests for SequenceCollectionRecord

```rust
#[test]
fn test_sequence_collection_record_stub() {
    let seqcol = digest_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let meta = SequenceCollectionMetadata::from_collection(&seqcol);
    let record = SequenceCollectionRecord::Stub(meta.clone());

    assert_eq!(record.metadata().digest, seqcol.digest);
    assert!(record.sequences().is_none());
    assert!(!record.has_sequences());
}

#[test]
fn test_sequence_collection_record_full() {
    let seqcol = load_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let record: SequenceCollectionRecord = seqcol.clone().into();

    assert!(record.has_sequences());
    assert!(record.sequences().is_some());
    assert_eq!(record.sequences().unwrap().len(), 3);
}

#[test]
fn test_sequence_collection_record_with_sequences() {
    let seqcol = load_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let meta = SequenceCollectionMetadata::from_collection(&seqcol);
    let stub = SequenceCollectionRecord::Stub(meta);

    // Convert stub to full by adding sequences
    let full = stub.with_sequences(seqcol.sequences.clone());

    assert!(full.has_sequences());
    assert_eq!(full.sequences().unwrap().len(), 3);
}

#[test]
fn test_sequence_collection_record_to_collection() {
    let seqcol = load_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let record: SequenceCollectionRecord = seqcol.clone().into();
    let converted = record.to_collection();

    assert_eq!(converted.digest, seqcol.digest);
    assert_eq!(converted.sequences.len(), seqcol.sequences.len());
}
```

### Step 14: Add tests for SequenceRecord methods

```rust
#[test]
fn test_sequence_record_metadata() {
    let seqcol = digest_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let record = &seqcol.sequences[0];
    let meta = record.metadata();

    assert_eq!(meta.name, "chrX");
    assert_eq!(meta.length, 8);
    assert!(!meta.sha512t24u.is_empty());
    assert!(!meta.md5.is_empty());
}

#[test]
fn test_sequence_record_sequence() {
    // Stub should return None
    let seqcol = digest_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");
    assert!(seqcol.sequences[0].sequence().is_none());

    // Full should return Some
    let seqcol_with_data = load_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");
    assert!(seqcol_with_data.sequences[0].sequence().is_some());
}

#[test]
fn test_sequence_record_with_data() {
    let seqcol = digest_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let stub = seqcol.sequences[0].clone();
    assert!(!stub.has_data());

    let full = stub.with_data(b"TTGGGGAA".to_vec());
    assert!(full.has_data());
    assert_eq!(full.sequence().unwrap(), b"TTGGGGAA");
}

#[test]
fn test_sequence_record_to_file() {
    use std::fs;
    use tempfile::tempdir;

    let seqcol = load_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let dir = tempdir().expect("Failed to create temp dir");
    let file_path = dir.path().join("test_seq.txt");

    seqcol.sequences[0].to_file(&file_path).expect("Failed to write file");

    let content = fs::read(&file_path).expect("Failed to read file");
    assert!(!content.is_empty());
}
```

### Step 15: Add tests for SequenceMetadata.disk_size()

```rust
#[test]
fn test_sequence_metadata_disk_size() {
    use crate::store::StorageMode;
    use crate::alphabet::AlphabetType;

    let metadata = SequenceMetadata {
        name: "test".to_string(),
        description: None,
        length: 1000,
        sha512t24u: "test".to_string(),
        md5: "test".to_string(),
        alphabet: AlphabetType::Dna2bit,
        fai: None,
    };

    // Raw mode: 1 byte per base
    assert_eq!(metadata.disk_size(&StorageMode::Raw), 1000);

    // Encoded mode for Dna2bit: 2 bits per base = 250 bytes for 1000 bases
    assert_eq!(metadata.disk_size(&StorageMode::Encoded), 250);
}

#[test]
fn test_sequence_metadata_disk_size_protein() {
    use crate::store::StorageMode;
    use crate::alphabet::AlphabetType;

    let metadata = SequenceMetadata {
        name: "protein_test".to_string(),
        description: None,
        length: 100,
        sha512t24u: "test".to_string(),
        md5: "test".to_string(),
        alphabet: AlphabetType::Protein,  // 5 bits per symbol
        fai: None,
    };

    // Raw mode: 1 byte per symbol
    assert_eq!(metadata.disk_size(&StorageMode::Raw), 100);

    // Encoded mode for Protein: 5 bits per symbol = 500 bits = 63 bytes (ceil(500/8))
    assert_eq!(metadata.disk_size(&StorageMode::Encoded), 63);
}
```

### Step 16: Add tests for SequenceCollection I/O methods

```rust
#[test]
fn test_sequence_collection_from_fasta() {
    let seqcol = SequenceCollection::from_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load FASTA");

    assert_eq!(seqcol.sequences.len(), 3);
    assert!(!seqcol.digest.is_empty());
    assert!(seqcol.file_path.is_some());
}

#[test]
fn test_sequence_collection_from_records() {
    let seqcol = load_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let records = seqcol.sequences.clone();
    let reconstructed = SequenceCollection::from_records(records);

    assert_eq!(reconstructed.digest, seqcol.digest);
    assert_eq!(reconstructed.sequences.len(), 3);
}

#[test]
fn test_sequence_collection_write_and_read_rgsi() {
    use tempfile::tempdir;

    let seqcol = digest_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let dir = tempdir().expect("Failed to create temp dir");
    let rgsi_path = dir.path().join("test.rgsi");

    seqcol.write_collection_rgsi(&rgsi_path).expect("Failed to write RGSI");

    // Read it back
    let loaded = SequenceCollection::from_rgsi(&rgsi_path)
        .expect("Failed to read RGSI");

    assert_eq!(loaded.digest, seqcol.digest);
    assert_eq!(loaded.sequences.len(), seqcol.sequences.len());
}

#[test]
fn test_sequence_collection_write_fasta() {
    use tempfile::tempdir;
    use std::fs;

    let seqcol = load_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let dir = tempdir().expect("Failed to create temp dir");
    let fasta_path = dir.path().join("output.fa");

    seqcol.write_fasta(&fasta_path, None).expect("Failed to write FASTA");

    let content = fs::read_to_string(&fasta_path).expect("Failed to read file");
    assert!(content.contains(">chrX"));
    assert!(content.contains("TTGGGGAA"));
}

#[test]
fn test_sequence_collection_write_fasta_with_line_width() {
    use tempfile::tempdir;
    use std::fs;

    let seqcol = load_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let dir = tempdir().expect("Failed to create temp dir");
    let fasta_path = dir.path().join("output.fa");

    // Write with 4 chars per line
    seqcol.write_fasta(&fasta_path, Some(4)).expect("Failed to write FASTA");

    let content = fs::read_to_string(&fasta_path).expect("Failed to read file");
    // TTGGGGAA (8 chars) should be split into 2 lines
    assert!(content.contains("TTGG\n") || content.contains("GGAA\n"));
}
```

### Step 17: Add tests for Display implementations

```rust
#[test]
fn test_sequence_collection_display() {
    let seqcol = digest_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let display = format!("{}", seqcol);
    assert!(display.contains("3 sequences"));
    assert!(display.contains(&seqcol.digest));
}

#[test]
fn test_sequence_record_display() {
    let seqcol = digest_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let display = format!("{}", seqcol.sequences[0]);
    assert!(display.contains("chrX"));
    assert!(display.contains("length: 8"));
}
```

### Step 18: Add test for SequenceCollectionRecord.write_collection_rgsi()

```rust
#[test]
fn test_sequence_collection_record_write_rgsi() {
    use tempfile::tempdir;
    use std::fs;

    let seqcol = load_fasta("../tests/data/fasta/base.fa")
        .expect("Failed to load test FASTA file");

    let record: SequenceCollectionRecord = seqcol.clone().into();

    let dir = tempdir().expect("Failed to create temp dir");
    let rgsi_path = dir.path().join("test.rgsi");

    record.write_collection_rgsi(&rgsi_path).expect("Failed to write RGSI");

    let content = fs::read_to_string(&rgsi_path).expect("Failed to read file");
    assert!(content.contains("##seqcol_digest="));
    assert!(content.contains("##names_digest="));
    assert!(content.contains("chrX"));
    assert!(content.contains("chr1"));
    assert!(content.contains("chr2"));
}
```

## Backwards Compatibility

This is developmental software. We are trying to eliminate old code, not keep it around. These tests should use the current API without concern for backwards compatibility.

## Cleanup

Once completed, move this plan to `plans/completed/gtars_python_refget_bindings_test_plan_v1.md`.
