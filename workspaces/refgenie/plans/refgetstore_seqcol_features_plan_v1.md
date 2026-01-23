# Implementation plan for RefgetStore Seqcol Features

## The issue

The GA4GH seqcol spec defines rich functionality for sequence collections: comparison, attribute-based search, and retrieval by attribute digest. Currently, this functionality requires running an API server (seqcolapi).

We want to enable the Rust gtars-refget crate to provide the same functionality directly against a local or remote RefgetStore, without requiring an API server. This would allow command-line tools and Rust applications to perform seqcol operations (compare collections, find collections by attribute, retrieve coordinate systems) using only file-based storage.

### Key capabilities to add

1. **Collection comparison** - Compare two collections, returning overlap counts and order information
2. **Attribute-based search** - Find all collections with a specific attribute digest (e.g., "find all collections with this sequences digest")
3. **Attribute value retrieval** - Get the raw attribute array given its digest
4. **Ancillary attributes** - Compute and store `name_length_pairs`, `sorted_name_length_pairs`, `sorted_sequences` digests

## Files to read for context

### Specification
- `/home/nsheff/Dropbox/workspaces/refgenie/repos/ga4gh-refget/docs/seqcols/README.md` - Full seqcol spec

### Current gtars-refget implementation
- `repos/gtars/gtars-refget/src/collection.rs` - SeqColDigestLvl1, SequenceCollection, SequenceCollectionMetadata structs
- `repos/gtars/gtars-refget/src/store.rs` - RefgetStore implementation
- `repos/gtars/gtars-refget/src/digest.rs` - sha512t24u, canonicalize_json functions

### Existing plans
- `plans/attach_remote_to_refgetstore_plan.md` - Pattern for adding new RefgetStore methods

## Implementation Steps

### Phase 1: Extend RGSI format with ancillary digests

**1.1 Add ancillary digest fields to SequenceCollectionMetadata** (`collection.rs`)

```rust
pub struct SequenceCollectionMetadata {
    // ... existing fields ...

    /// Level 1 digest of name_length_pairs array (RECOMMENDED by spec)
    pub name_length_pairs_digest: Option<String>,
    /// Level 1 digest of sorted_name_length_pairs array (RECOMMENDED, transient)
    pub sorted_name_length_pairs_digest: Option<String>,
    /// Level 1 digest of sorted_sequences array (OPTIONAL)
    pub sorted_sequences_digest: Option<String>,
}
```

**1.2 Implement ancillary digest computation** (`collection.rs`)

Add methods to `SeqColDigestLvl1` or a new struct:

```rust
impl SeqColDigestLvl1 {
    /// Compute name_length_pairs digest from metadata
    /// Algorithm: {"length": L, "name": "N"} for each, canonicalize, digest each, then digest the array
    pub fn compute_name_length_pairs_digest(metadata: &[&SequenceMetadata]) -> String;

    /// Compute sorted_name_length_pairs digest (order-invariant coordinate system)
    /// Algorithm: same as above but sort the individual digests lexicographically before final digest
    pub fn compute_sorted_name_length_pairs_digest(metadata: &[&SequenceMetadata]) -> String;

    /// Compute sorted_sequences digest (order-invariant sequence set)
    /// Algorithm: sort sequence digests lexicographically, then digest the array
    pub fn compute_sorted_sequences_digest(metadata: &[&SequenceMetadata]) -> String;
}
```

**1.3 Update RGSI file format** (`collection.rs`)

Extend `write_collection_rgsi()` to include new headers:

```
##seqcol_digest=abc123
##names_digest=def456
##sequences_digest=ghi789
##lengths_digest=jkl012
##name_length_pairs_digest=mno345
##sorted_name_length_pairs_digest=pqr678
##sorted_sequences_digest=stu901
#name	description	length	alphabet	sha512t24u	md5
```

Update `read_fasta_refget_file()` in `fasta.rs` to parse new headers.

### Phase 2: Attribute index storage

**2.1 Create attribute index directory structure**

When a collection is added to a RefgetStore, write attribute index files:

```
refget_store/
  attributes/
    names/
      <names_digest>           # Contains list of collection digests
    lengths/
      <lengths_digest>
    sequences/
      <sequences_digest>
    name_length_pairs/
      <nlp_digest>
    sorted_name_length_pairs/
      <snlp_digest>
    sorted_sequences/
      <ss_digest>
```

**2.2 Define attribute index file format**

Simple newline-delimited list of collection digests:

```
collection_abc123
collection_xyz789
```

**2.3 Add index management to RefgetStore** (`store.rs`)

```rust
impl RefgetStore {
    /// Write attribute index entry when adding a collection
    fn write_attribute_index(&self, attr_name: &str, attr_digest: &str, collection_digest: &str) -> Result<()>;

    /// Read attribute index file
    fn read_attribute_index(&self, attr_name: &str, attr_digest: &str) -> Result<Vec<String>>;

    /// Remove collection from attribute indexes (for delete/update)
    fn remove_from_attribute_indexes(&self, collection_digest: &str) -> Result<()>;
}
```

**2.4 Update `add_sequence_collection()` to write indexes**

After adding a collection, call `write_attribute_index()` for each attribute:
- names_digest
- lengths_digest
- sequences_digest
- name_length_pairs_digest (if present)
- sorted_name_length_pairs_digest (if present)
- sorted_sequences_digest (if present)

### Phase 3: Attribute-based search (seqcol `/list` equivalent)

**3.1 Add search method to RefgetStore** (`store.rs`)

```rust
impl RefgetStore {
    /// Find all collections with a specific attribute digest
    ///
    /// # Arguments
    /// * `attr_name` - Attribute name ("names", "sequences", "lengths", "sorted_name_length_pairs", etc.)
    /// * `attr_digest` - The level 1 digest of the attribute
    ///
    /// # Returns
    /// Vector of collection digests that have this attribute
    pub fn find_collections_by_attribute(&self, attr_name: &str, attr_digest: &str) -> Result<Vec<String>>;

    /// Find collections matching multiple attribute constraints (AND logic)
    pub fn find_collections_by_attributes(&self, constraints: &[(&str, &str)]) -> Result<Vec<String>>;
}
```

### Phase 4: Attribute value retrieval (seqcol `/attribute` equivalent)

**4.1 Add attribute retrieval method** (`store.rs`)

```rust
/// Represents different attribute value types
pub enum AttributeValue {
    Strings(Vec<String>),    // names, sequences
    Integers(Vec<i64>),      // lengths
    NameLengthPairs(Vec<NameLengthPair>),  // name_length_pairs
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NameLengthPair {
    pub name: String,
    pub length: i64,
}

impl RefgetStore {
    /// Get attribute value by its digest
    ///
    /// Finds a collection with this attribute, extracts the value from it.
    ///
    /// # Arguments
    /// * `attr_name` - Attribute name
    /// * `attr_digest` - The level 1 digest
    ///
    /// # Returns
    /// The attribute value if found
    pub fn get_attribute(&self, attr_name: &str, attr_digest: &str) -> Result<Option<AttributeValue>>;
}
```

**4.2 Implementation strategy**

1. Read attribute index file to find a collection with this attribute
2. Load that collection's RGSI file
3. Extract the attribute value from the collection data
4. Return as appropriate `AttributeValue` variant

### Phase 5: Collection comparison (seqcol `/comparison` equivalent)

**5.1 Define comparison result struct** (`collection.rs`)

```rust
/// Result of comparing two sequence collections
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComparisonResult {
    pub digests: ComparisonDigests,
    pub attributes: AttributeComparison,
    pub array_elements: ArrayElementComparison,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComparisonDigests {
    pub a: Option<String>,
    pub b: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AttributeComparison {
    pub a_only: Vec<String>,
    pub b_only: Vec<String>,
    pub a_and_b: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArrayElementComparison {
    pub a_count: HashMap<String, usize>,
    pub b_count: HashMap<String, usize>,
    pub a_and_b_count: HashMap<String, usize>,
    pub a_and_b_same_order: HashMap<String, Option<bool>>,
}
```

**5.2 Add comparison method** (`store.rs` or `collection.rs`)

```rust
impl RefgetStore {
    /// Compare two collections by their digests
    pub fn compare(&self, digest_a: &str, digest_b: &str) -> Result<ComparisonResult>;

    /// Compare a stored collection with a provided collection object
    pub fn compare_with_collection(&self, digest: &str, collection: &SequenceCollection) -> Result<ComparisonResult>;
}

impl SequenceCollection {
    /// Compare this collection with another
    pub fn compare(&self, other: &SequenceCollection) -> ComparisonResult;
}
```

**5.3 Implement same-order detection**

Per spec, `a_and_b_same_order` is:
- `null` if fewer than 2 overlapping elements
- `null` if unbalanced duplicates present
- `true` if all matching elements are in same order
- `false` otherwise

```rust
fn compute_same_order<T: Eq + Hash>(a: &[T], b: &[T]) -> Option<bool> {
    // Implementation following spec rules
}
```

### Phase 6: Collection retrieval at different levels

**6.1 Add level-based retrieval** (`store.rs`)

```rust
/// Representation level for collection retrieval
pub enum CollectionLevel {
    /// Level 0: Just the top-level digest
    Digest,
    /// Level 1: Attribute digests
    AttributeDigests,
    /// Level 2: Full arrays (canonical representation)
    Full,
}

/// Level 1 representation (attribute digests only)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CollectionLevel1 {
    pub names: String,
    pub lengths: String,
    pub sequences: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name_length_pairs: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sorted_name_length_pairs: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sorted_sequences: Option<String>,
}

/// Level 2 representation (full arrays)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CollectionLevel2 {
    pub names: Vec<String>,
    pub lengths: Vec<i64>,
    pub sequences: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name_length_pairs: Option<Vec<NameLengthPair>>,
    // sorted_name_length_pairs is transient - no level 2
    // sorted_sequences could be included if not transient
}

impl RefgetStore {
    /// Get collection at specified representation level
    pub fn get_collection_at_level(&self, digest: &str, level: CollectionLevel) -> Result<serde_json::Value>;
}
```

### Phase 7: Python bindings

**7.1 Add bindings in `gtars-python/src/refget/mod.rs`**

```rust
#[pymethods]
impl PyRefgetStore {
    /// Find collections by attribute digest
    #[pyo3(signature = (attr_name, attr_digest))]
    fn find_by_attribute(&self, attr_name: &str, attr_digest: &str) -> PyResult<Vec<String>>;

    /// Get attribute value by digest
    #[pyo3(signature = (attr_name, attr_digest))]
    fn get_attribute(&self, attr_name: &str, attr_digest: &str) -> PyResult<Option<PyObject>>;

    /// Compare two collections
    #[pyo3(signature = (digest_a, digest_b))]
    fn compare(&self, digest_a: &str, digest_b: &str) -> PyResult<PyObject>;
}
```

**7.2 Update type stubs** (`gtars-python/py_src/gtars/refget/__init__.pyi`)

Add method signatures with documentation.

### Phase 8: CLI commands

**8.1 Add seqcol subcommands to refget CLI** (`refget/cli/seqcol.py`)

```bash
# Compare two collections
refget seqcol compare <digest1> <digest2> --store /path/to/store

# Find collections by attribute
refget seqcol find --names <digest> --store /path/to/store
refget seqcol find --sequences <digest> --sorted-name-length-pairs <digest>

# Get attribute value
refget seqcol attribute names <digest> --store /path/to/store
refget seqcol attribute lengths <digest>
```

## File changes summary

| File | Changes |
|------|---------|
| `gtars-refget/src/collection.rs` | Add ancillary digests to metadata, add comparison structs, implement comparison |
| `gtars-refget/src/store.rs` | Add attribute index methods, find_by_attribute, get_attribute, compare |
| `gtars-refget/src/fasta.rs` | Update RGSI parsing for new headers |
| `gtars-python/src/refget/mod.rs` | Add Python bindings for new methods |
| `gtars-python/py_src/gtars/refget/__init__.pyi` | Type stubs |
| `refget/cli/seqcol.py` | CLI commands |

## Backwards compatibility

This is developmental software. We are trying to eliminate old code, not keep it around.

- RGSI files without ancillary digest headers will be read correctly (fields default to None)
- Stores without `attributes/` directory will work for basic operations; attribute search will return empty results
- No migration needed for existing stores

## Testing

1. Unit tests for ancillary digest computation (verify against known values from Python implementation)
2. Unit tests for comparison logic, especially same-order edge cases
3. Integration tests for attribute index read/write
4. CLI tests for new commands

## Cleanup

Once completed, move the completed plan to `plans/completed/refgetstore_seqcol_features_plan_v1.md`.
