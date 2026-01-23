# Implementation Plan: RefgetStore File Format Update

## Overview

This plan addresses two issues:
1. **File naming inconsistency**: Current `.farg` extension is used for both sequence indexes and collection files, but "farg" implies a list of sequences (like `.fai`). Need distinct extensions.
2. **Missing collection discovery**: Users can't discover available collections without loading them all.

## File Format Changes

### File Extension Changes

| Current | New | Description |
|---------|-----|-------------|
| `index.json` | `rgstore.json` | Store manifest/config |
| `sequences.farg` | `sequences.rgsi` | Sequence index (refget sequence index) |
| `collections/{digest}.farg` | `collections/{digest}.rgsi` | Per-collection sequence list |
| *(none)* | `collections.rgci` | **NEW**: Collection index (refget collection index) |

### Extension Naming Rationale

- `.rgsi` = **r**ef**g**et **s**equence **i**ndex (list of sequences, analogous to `.fai`)
- `.rgci` = **r**ef**g**et **c**ollection **i**ndex (list of collections)
- `.json` kept for `rgstore.json` because JSON is universal and tools recognize it
- Both `.rgsi` and `.rgci` are TSV files with `#` headers (format implied by spec)

### New Directory Structure

```
refget-store/
├── rgstore.json              # Store manifest (was index.json)
├── sequences.rgsi            # Sequence index (was sequences.farg)
├── collections.rgci          # NEW: Collection index
├── sequences/                # Sequence data files
│   └── {prefix}/
│       └── {digest}.seq
└── collections/              # Per-collection sequence lists
    └── {digest}.rgsi         # (was {digest}.farg)
```

## Data Model Changes

### New: SequenceCollectionMetadata (merges SeqColDigestLvl1)

```rust
/// Metadata for a sequence collection (parallel to SequenceMetadata)
/// Merges the former SeqColDigestLvl1 fields into a single flat struct
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SequenceCollectionMetadata {
    pub digest: String,           // top-level seqcol digest
    pub n_sequences: usize,       // number of sequences
    pub names_digest: String,     // level 1 digest of names array
    pub sequences_digest: String, // level 1 digest of sequences array
    pub lengths_digest: String,   // level 1 digest of lengths array
    pub file_path: Option<PathBuf>,
}

impl SequenceCollectionMetadata {
    /// Compute metadata from sequence records
    pub fn from_sequences(sequences: &[SequenceRecord], file_path: Option<PathBuf>) -> Self {
        // Extract metadata refs
        let metadata_refs: Vec<&SequenceMetadata> = sequences.iter()
            .map(|r| r.metadata())
            .collect();

        // Compute level 1 digests (same logic as current SeqColDigestLvl1::from_metadata)
        let names_digest = compute_names_digest(&metadata_refs);
        let sequences_digest = compute_sequences_digest(&metadata_refs);
        let lengths_digest = compute_lengths_digest(&metadata_refs);

        // Compute top-level digest from level 1 digests
        let digest = compute_collection_digest(&names_digest, &sequences_digest);

        Self {
            digest,
            n_sequences: sequences.len(),
            names_digest,
            sequences_digest,
            lengths_digest,
            file_path,
        }
    }

    /// Verify that top-level digest matches computed value from level 1 digests
    pub fn verify_digest(&self) -> bool {
        let computed = compute_collection_digest(&self.names_digest, &self.sequences_digest);
        computed == self.digest
    }
}
```

### New: SequenceCollectionRecord (parallel to SequenceRecord)

```rust
/// A collection record that may or may not have its sequence list loaded
/// Parallel to SequenceRecord
#[derive(Clone, Debug)]
pub enum SequenceCollectionRecord {
    /// Collection with only metadata, sequence list not loaded
    Stub(SequenceCollectionMetadata),
    /// Collection with metadata and the actual sequence list
    Full {
        metadata: SequenceCollectionMetadata,
        sequences: Vec<SequenceRecord>,
    },
}

impl SequenceCollectionRecord {
    /// Get metadata regardless of variant
    pub fn metadata(&self) -> &SequenceCollectionMetadata {
        match self {
            SequenceCollectionRecord::Stub(meta) => meta,
            SequenceCollectionRecord::Full { metadata, .. } => metadata,
        }
    }

    /// Get sequences if loaded
    pub fn sequences(&self) -> Option<&[SequenceRecord]> {
        match self {
            SequenceCollectionRecord::Stub(_) => None,
            SequenceCollectionRecord::Full { sequences, .. } => Some(sequences),
        }
    }

    /// Check if sequences are loaded
    pub fn has_sequences(&self) -> bool {
        matches!(self, SequenceCollectionRecord::Full { .. })
    }

    /// Load sequences into a Stub record, converting to Full
    pub fn with_sequences(self, sequences: Vec<SequenceRecord>) -> Self {
        let metadata = match self {
            SequenceCollectionRecord::Stub(m) => m,
            SequenceCollectionRecord::Full { metadata, .. } => metadata,
        };
        SequenceCollectionRecord::Full { metadata, sequences }
    }
}
```

### Parallel Structure Summary

| Sequences | Collections |
|-----------|-------------|
| `SequenceMetadata` | `SequenceCollectionMetadata` |
| `SequenceRecord::Stub(SequenceMetadata)` | `SequenceCollectionRecord::Stub(SequenceCollectionMetadata)` |
| `SequenceRecord::Full { metadata, sequence: Vec<u8> }` | `SequenceCollectionRecord::Full { metadata, sequences: Vec<SequenceRecord> }` |

## File Format Specifications

### rgstore.json (renamed from index.json)

```json
{
  "version": 1,
  "seqdata_path_template": "sequences/%s2/%s.seq",
  "collections_path_template": "collections/%s.rgsi",
  "sequence_index": "sequences.rgsi",
  "collection_index": "collections.rgci",
  "mode": "Encoded",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Changes:**
- Renamed file from `index.json` to `rgstore.json`
- `collections_path_template`: Changed from `.farg` to `.rgsi`
- `sequence_index`: Changed from `sequences.farg` to `sequences.rgsi`
- `collection_index`: **NEW** field pointing to `collections.rgci`

### sequences.rgsi (renamed from sequences.farg)

No format change, just renamed:

```
#name	length	alphabet	sha512t24u	md5
chr1	248956422	dna2bit	AbCdEf123...	a1b2c3d4...
chr2	242193529	dna2bit	XyZabc456...	f7e8d9c0...
```

### collections/{digest}.rgsi (renamed from {digest}.farg)

No format change, just renamed:

```
##seqcol_digest=uC_UorBNf3YUu1YIDainBhI94CedlNeH
##names_digest=zxcvbnmasdfghjkl
##sequences_digest=qwertyuiopasdfgh
##lengths_digest=poiuytrewqlkjhgf
#name	length	alphabet	sha512t24u	md5
chr1	248956422	dna2bit	AbCdEf123...	a1b2c3d4...
chr2	242193529	dna2bit	XyZabc456...	f7e8d9c0...
```

### collections.rgci (NEW)

Master index of all collections in the store.

```
#digest	n_sequences	names_digest	sequences_digest	lengths_digest
0aHV7I-94paL9Z1H4LNlqsW3WxJhlou5	847	aS554WVCyQGCNgb5zVH6fAKUoFQp-EJd	d1F0MA_qgQ5zNoc7Ii8zY7uE6MS0Veuy	xojAZd8qioB7vLh2LXNhbFIPu8RQUndm
ET-m1LqV9Pp5GtNK7-gzcCBTOOYprPQN	823	bT665XWDzRHDOhc6aVI7gBLVpGRq-FKe	e2G1NB_rhR6aPpdL8-h0cDUwPZNu0Fvz	ypkBAe9rUjpC8wMi3LNicGJQv9SeeDUo
```

**Columns:**
1. `digest` - Collection's SHA-512/24u digest (required)
2. `n_sequences` - Number of sequences in collection (required)
3. `names_digest` - Level 1 digest of names array
4. `sequences_digest` - Level 1 digest of sequences array
5. `lengths_digest` - Level 1 digest of lengths array

## Loading Behavior

### Current Behavior (Problem)

When loading a RefgetStore:
1. Read `index.json` - get store config
2. Read `sequences.farg` - load all sequence metadata as stubs
3. Collections loaded **on-demand only** → can't discover what's available

### New Behavior (Solution)

When loading a RefgetStore:
1. Read `rgstore.json` - get store config
2. Read `sequences.rgsi` - load all sequence metadata as `SequenceRecord::Stub`
3. Read `collections.rgci` - load all collection metadata as `SequenceCollectionRecord::Stub`
4. Individual collection files (`collections/{digest}.rgsi`) loaded on-demand → upgrades Stub to Full

**Two-level lazy loading:**

| Level | Transition | Trigger | Data loaded |
|-------|------------|---------|-------------|
| 1 | `SequenceCollectionRecord::Stub` → `Full` | Accessing collection's sequences | Sequence metadata from `collections/{digest}.rgsi` |
| 2 | `SequenceRecord::Stub` → `Full` | Accessing actual sequence data | Sequence bytes from `sequences/{prefix}/{digest}.seq` |

When a collection is loaded (Stub → Full), its `sequences` field contains `SequenceRecord::Stub` entries (metadata only). The actual sequence bytes remain lazy-loaded separately via the existing `ensure_sequence_loaded()` mechanism when `get_sequence_by_id()` or `get_sequence_by_collection_and_name()` is called.

This matches the existing pattern in the codebase where collection loading and sequence data loading are independent operations.

**What's loaded eagerly:**
- Store config (`rgstore.json`)
- Sequence index (`sequences.rgsi`)
- Collection index (`collections.rgci`)

**What's lazy-loaded:**
- Per-collection sequence lists (`collections/{digest}.rgsi`) - upgrades `SequenceCollectionRecord::Stub` → `Full`
- Actual sequence data (`.seq` files) - upgrades `SequenceRecord::Stub` → `Full`

### Index File Consistency

The `collections.rgci` file MUST be kept in sync with the `collections/*.rgsi` files:
- When a collection is added to a disk-backed store, BOTH the per-collection `.rgsi` file AND `collections.rgci` are updated immediately
- When loading a store, `collections.rgci` is the source of truth for available collections
- If `collections.rgci` doesn't exist or is empty, the store has no collections (consistent with `sequences.rgsi` behavior)

## Implementation Steps

### Phase 1: Data Model (collection.rs)

#### 1.1 Add SequenceCollectionMetadata struct

```rust
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SequenceCollectionMetadata {
    pub digest: String,
    pub n_sequences: usize,
    pub names_digest: String,
    pub sequences_digest: String,
    pub lengths_digest: String,
    pub file_path: Option<PathBuf>,
}
```

#### 1.2 Add SequenceCollectionRecord enum

```rust
#[derive(Clone, Debug)]
pub enum SequenceCollectionRecord {
    Stub(SequenceCollectionMetadata),
    Full {
        metadata: SequenceCollectionMetadata,
        sequences: Vec<SequenceRecord>,
    },
}
```

#### 1.3 Add helper methods to SequenceCollectionRecord

- `metadata(&self) -> &SequenceCollectionMetadata`
- `sequences(&self) -> Option<&[SequenceRecord]>`
- `has_sequences(&self) -> bool`
- `with_sequences(self, sequences: Vec<SequenceRecord>) -> Self`

#### 1.4 Deprecate SeqColDigestLvl1

- Keep for now with `#[deprecated]` attribute
- Add `From<&SequenceCollectionMetadata>` impl for compatibility
- Migrate all usages to SequenceCollectionMetadata

#### 1.5 Add conversion from SequenceCollection to SequenceCollectionRecord

```rust
impl SequenceCollection {
    /// Convert to a Full record for storage in RefgetStore
    pub fn to_record(&self) -> SequenceCollectionRecord {
        let metadata = SequenceCollectionMetadata::from_sequences(&self.sequences, None);
        SequenceCollectionRecord::Full {
            metadata,
            sequences: self.sequences.clone(),
        }
    }
}

impl From<SequenceCollection> for SequenceCollectionRecord {
    fn from(collection: SequenceCollection) -> Self {
        collection.to_record()
    }
}
```

This allows existing code using `SequenceCollection` to easily convert to the new record type.

### Phase 2: Store Changes (store.rs)

#### 2.1 Update StoreMetadata struct

```rust
#[derive(Debug, Serialize, Deserialize)]
struct StoreMetadata {
    version: u32,
    seqdata_path_template: String,
    collections_path_template: String,  // Now uses .rgsi
    sequence_index: String,             // Now "sequences.rgsi"
    collection_index: String,           // NEW: "collections.rgci"
    mode: StorageMode,
    created_at: String,
}
```

#### 2.2 Update RefgetStore struct

```rust
pub struct RefgetStore {
    // ... existing fields ...

    // Change from:
    // collections: HashMap<[u8; 32], SequenceCollection>,

    // To:
    collections: HashMap<[u8; 32], SequenceCollectionRecord>,
}
```

#### 2.3 Add write_collections_rgci() method

```rust
fn write_collections_rgci<P: AsRef<Path>>(&self, file_path: P) -> Result<()> {
    let file_path = file_path.as_ref();
    let mut file = File::create(file_path)?;

    writeln!(file, "#digest\tn_sequences\tnames_digest\tsequences_digest\tlengths_digest")?;

    for record in self.collections.values() {
        let meta = record.metadata();
        writeln!(
            file,
            "{}\t{}\t{}\t{}\t{}",
            meta.digest,
            meta.n_sequences,
            meta.names_digest,
            meta.sequences_digest,
            meta.lengths_digest,
        )?;
    }
    Ok(())
}
```

#### 2.4 Update add_sequence_collection() for index sync

When adding a collection to a disk-backed store, update BOTH files:

```rust
pub fn add_sequence_collection(&mut self, collection: SequenceCollection) -> Result<String> {
    let record = collection.to_record();
    let digest = record.metadata().digest.clone();
    let key = digest_to_key(&digest);

    // Insert into in-memory store
    self.collections.insert(key, record);

    // For disk-backed stores, write both files
    if let Some(ref local_path) = self.local_path {
        // Write per-collection .rgsi file
        let collection_path = local_path.join(format!("collections/{}.rgsi", digest));
        self.write_collection_rgsi(&key, &collection_path)?;

        // Update collections.rgci (rewrite entire file to stay in sync)
        let index_path = local_path.join("collections.rgci");
        self.write_collections_rgci(&index_path)?;
    }

    Ok(digest)
}
```

#### 2.5 Update write_index_files()

```rust
fn write_index_files(&self) -> Result<()> {
    let local_path = self.local_path.as_ref().context("local_path not set")?;

    // Write sequence index (renamed)
    let sequence_index_path = local_path.join("sequences.rgsi");
    self.write_sequences_rgsi(&sequence_index_path)?;

    // Write collection index (NEW)
    let collection_index_path = local_path.join("collections.rgci");
    self.write_collections_rgci(&collection_index_path)?;

    // Write store manifest (renamed)
    let metadata = StoreMetadata {
        version: 1,
        seqdata_path_template: template.clone(),
        collections_path_template: "collections/%s.rgsi".to_string(),
        sequence_index: "sequences.rgsi".to_string(),
        collection_index: "collections.rgci".to_string(),
        mode: self.mode,
        created_at: Utc::now().to_rfc3339(),
    };

    let json = serde_json::to_string_pretty(&metadata)?;
    fs::write(local_path.join("rgstore.json"), json)?;

    Ok(())
}
```

#### 2.6 Update load_local() and load_remote()

```rust
// After loading store config...

// Load sequence stubs from sequences.rgsi (existing behavior, renamed file)
let seq_index_data = Self::fetch_file(&local_path, &remote_source, "sequences.rgsi", true)?;
// ... parse and populate sequence_store with SequenceRecord::Stub ...

// Load collection stubs from collections.rgci (NEW)
let coll_index_data = Self::fetch_file(&local_path, &remote_source, "collections.rgci", true)?;
let index_str = String::from_utf8(coll_index_data)?;
for line in index_str.lines() {
    if line.starts_with('#') { continue; }
    let parts: Vec<&str> = line.split('\t').collect();
    if parts.len() >= 5 {
        let metadata = SequenceCollectionMetadata {
            digest: parts[0].to_string(),
            n_sequences: parts[1].parse().unwrap_or(0),
            names_digest: parts[2].to_string(),
            sequences_digest: parts[3].to_string(),
            lengths_digest: parts[4].to_string(),
            file_path: None,  // Set when loaded
        };
        let key = digest_to_key(&metadata.digest);
        store.collections.insert(key, SequenceCollectionRecord::Stub(metadata));
    }
}
```

#### 2.7 Update stats() method

```rust
pub fn stats(&self) -> (usize, usize, usize, &'static str) {
    let n_sequences = self.sequence_store.len();
    let n_collections = self.collections.len();
    let n_collections_loaded = self.collections.values()
        .filter(|c| c.has_sequences())
        .count();
    let mode_str = match self.mode {
        StorageMode::Raw => "Raw",
        StorageMode::Encoded => "Encoded",
    };
    (n_sequences, n_collections, n_collections_loaded, mode_str)
}
```

#### 2.8 Add collection access methods

```rust
/// List all collection digests (both stubs and loaded)
pub fn list_collections(&self) -> Vec<String> {
    self.collections.values()
        .map(|r| r.metadata().digest.clone())
        .collect()
}

/// Get collection metadata without loading sequences
pub fn get_collection_metadata<K: AsRef<[u8]>>(&self, digest: K) -> Option<&SequenceCollectionMetadata> {
    let key = digest_to_key(digest.as_ref());
    self.collections.get(&key).map(|r| r.metadata())
}

/// Load a collection's sequences from its .rgsi file (Stub → Full)
fn load_collection_sequences(&self, metadata: &SequenceCollectionMetadata) -> Result<SequenceCollectionRecord> {
    let collection_path = format!("collections/{}.rgsi", metadata.digest);

    // Fetch from local or remote
    let data = Self::fetch_file(
        self.local_path.as_ref(),
        self.remote_source.as_ref(),
        &collection_path,
        true,  // cache locally if remote
    )?;

    // Parse .rgsi file into SequenceRecord::Stub entries
    let content = String::from_utf8(data)?;
    let mut sequences = Vec::new();

    for line in content.lines() {
        if line.starts_with('#') { continue; }
        let parts: Vec<&str> = line.split('\t').collect();
        if parts.len() >= 5 {
            let seq_metadata = SequenceMetadata {
                name: parts[0].to_string(),
                length: parts[1].parse().unwrap_or(0),
                alphabet: AlphabetType::from_str(parts[2]).unwrap_or(AlphabetType::Dna2Bit),
                sha512t24u: parts[3].to_string(),
                md5: parts[4].to_string(),
                fai: None,
            };
            sequences.push(SequenceRecord::Stub(seq_metadata));
        }
    }

    Ok(SequenceCollectionRecord::Full {
        metadata: metadata.clone(),
        sequences,
    })
}

/// Get collection with sequences (loads if needed)
pub fn get_collection<K: AsRef<[u8]>>(&mut self, digest: K) -> Option<&SequenceCollectionRecord> {
    let key = digest_to_key(digest.as_ref());

    // If stub, load the full collection
    if let Some(SequenceCollectionRecord::Stub(meta)) = self.collections.get(&key) {
        // Load from .rgsi file
        if let Ok(loaded) = self.load_collection_sequences(&meta.clone()) {
            self.collections.insert(key, loaded);
        }
    }

    self.collections.get(&key)
}
```

#### 2.9 Rename existing methods

- `write_sequences_farg()` → `write_sequences_rgsi()`
- `write_collection_farg()` → `write_collection_rgsi()` (in collection.rs)

### Phase 3: Python Bindings (gtars-python)

#### 3.1 Update stats() return value

```rust
fn stats(&self) -> HashMap<String, String> {
    let (n_sequences, n_collections, n_collections_loaded, mode_str) = self.inner.stats();
    let mut stats = HashMap::new();
    stats.insert("n_sequences".to_string(), n_sequences.to_string());
    stats.insert("n_collections".to_string(), n_collections.to_string());
    stats.insert("n_collections_loaded".to_string(), n_collections_loaded.to_string());
    stats.insert("storage_mode".to_string(), mode_str.to_string());
    stats
}
```

#### 3.2 Add list_collections() method

```rust
fn list_collections(&self) -> Vec<String> {
    self.inner.list_collections()
}
```

#### 3.3 Update __init__.pyi type stubs

```python
class RefgetStore:
    def stats(self) -> dict[str, str]:
        """Returns store statistics.

        Returns:
            dict with keys: n_sequences, n_collections, n_collections_loaded, storage_mode
        """
        ...

    def list_collections(self) -> list[str]:
        """List all collection digests (loaded and not yet loaded)."""
        ...
```

### Phase 4: Testing

1. **Write/read round-trip test** - Create store, write, reload, verify all data
2. **Extension rename test** - Verify new extensions are used in output
3. **Collection index test** - Verify collections.rgci is created and parsed correctly
4. **Stub/Full test** - Verify collections start as Stub, upgrade to Full on access
5. **stats() test** - Verify n_collections vs n_collections_loaded
6. **list_collections() test** - Verify returns all collection digests
7. **Remote loading test** - Verify collection stubs loaded from remote store

### Phase 5: Documentation Updates

#### 5.1 Code Files to Modify

| File | Changes |
|------|---------|
| `gtars/gtars-refget/src/collection.rs` | Add SequenceCollectionMetadata, SequenceCollectionRecord |
| `gtars/gtars-refget/src/store.rs` | Update StoreMetadata, RefgetStore, file operations |
| `gtars/gtars-python/src/refget/mod.rs` | Python binding changes |
| `gtars/gtars-python/py_src/gtars/refget/__init__.pyi` | Type stub updates |

#### 5.2 User-Facing Documentation

| File | Updates Needed |
|------|----------------|
| `bedbase/docs/gtars/refget-store-format.md` | Update to reflect new extensions, collections.rgci, two-level lazy loading |
| `refgenie-docs/docs/refget/notebooks/refgetstore.ipynb` | Update examples with new API (list_collections, stats keys) |
| `refgenie-docs/docs/refget/reference_docs.md` | Verify mkdocstrings picks up new methods |

#### 5.3 Documentation Checklist

Before marking complete, verify:

- [ ] `refget-store-format.md` matches implementation:
  - [ ] File extensions (.rgsi, .rgci, rgstore.json)
  - [ ] Directory structure diagram
  - [ ] collections.rgci format and columns
  - [ ] Two-level lazy loading explanation
  - [ ] Loading behavior section
  - [ ] Code examples use correct API
- [ ] Python docstrings present for all new/changed methods
- [ ] Type stubs (.pyi) match actual signatures
- [ ] Notebook runs without errors with updated API
- [ ] mkdocs builds without warnings

## Migration

**No backward compatibility required.** This is development - existing stores should be regenerated.

Changes from current format:
- File extensions: `.farg` → `.rgsi`
- Config file: `index.json` → `rgstore.json`
- New file: `collections.rgci`
