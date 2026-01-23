# Integrating seqcol and refgenie for FASTA file handling

**Date:** 2025-12-03
**Status:** Option 4 now implementable (FAI index support added to refget)
**Authors:** Conversation participants

---

## Executive summary

This guide addresses a fundamental architectural question: how should refgenie and refget/seqcol share responsibility for FASTA file handling without duplicating data or functionality?

Refgenie manages genomic assets including a "fasta" asset class that bundles three files into a tarball: the FASTA file itself, a FASTA index (.fai), and chromosome sizes (.chrom.sizes). Refget/seqcol provides GA4GH-compliant sequence collection metadata and now includes DRS (Data Repository Service) endpoints for FASTA file access.

The core problem is that these systems overlap in their handling of FASTA data. Refgenie already uses seqcol to compute genome digests during initialization, but then separately stores the FASTA file within an asset tarball. This creates potential data duplication and architectural confusion about which system is authoritative for FASTA data.

Four options were evaluated:

1. Expand seqcol to serve the entire indexed FASTA bundle
2. Store FASTA files twice (one copy per system)
3. Refgenie fasta asset contains only FAI, retrieves FASTA from seqcol
4. Eliminate fasta asset entirely; seqcol serves all FASTA-related data

The recommended approach is option 4: eliminate the fasta asset from refgenie and consolidate all FASTA-related data into seqcol. This option is now fully implementable because refget has added FAI index support:

- FASTA files: served via DRS endpoints (implemented)
- Chromosome sizes: derivable from seqcol `names` + `lengths` (available)
- FAI index: stored in `FastaDrsObject` and served via `/objects/{id}/index` endpoint (implemented)

A secondary design decision addresses DRS object identification: using the file's MD5 hash (rather than seqcol digest) as the DRS object ID allows multiple FASTA files with identical sequence content but different formatting to coexist. This decision remains open.

---

## Background: Current architecture

### Refgenie asset structure

Refgenie defines a "fasta" asset class containing three seek keys:

```yaml
name: fasta
seek_keys:
  fasta:
    value: "{genome}.fa"
    type: file
  fai:
    value: "{genome}.fa.fai"
    type: file
  chrom_sizes:
    value: "{genome}.chrom.sizes"
    type: file
```

These files are bundled into a tarball (`fasta_asset.tar.gz`) and served via refgenie's DRS implementation at `/ga4gh/drs/objects/{asset_digest}`.

### Refget/seqcol structure

Seqcol stores sequence collection metadata:

- `names`: array of sequence/chromosome names
- `lengths`: array of sequence lengths
- `sequences`: array of GA4GH sequence digests
- `name_length_pairs`: combined name-length data
- `sorted_name_length_pairs`: sort-invariant coordinate system identifier

The `FastaDrsObject` model stores FASTA file metadata:

- File size
- Checksums (SHA-256, MD5, refget seqcol digest)
- Access methods (URLs for file retrieval)
- Creation/update timestamps

### Existing integration point

Refgenie's `initialize_genome()` method already calls `refget_db_agent.seqcol.add_from_fasta_file()` to compute the genome digest. The seqcol digest becomes the genome identifier.

---

## Core problem: Data duplication and architectural overlap

The fundamental issue is that both systems store and serve FASTA data:

| Component | Refgenie | Refget/seqcol |
|-----------|----------|---------------|
| FASTA file | In asset tarball | Via DRS (implemented) |
| Chromosome sizes | In asset tarball | Derivable from names+lengths |
| FAI index | In asset tarball | Via `/objects/{id}/index` (implemented) |
| Genome identifier | Uses seqcol digest | Provides seqcol digest |

The refgenie fasta asset tarball contains the same FASTA file that seqcol can serve via DRS. This duplication wastes storage and creates ambiguity about which system is authoritative.

### Additional complication: Tarball structure

Refgenie's DRS serves entire asset archives. The FASTA file is inside a tarball alongside the .fai and .chrom.sizes files. A client cannot retrieve just the FASTA file via refgenie's DRS without downloading and extracting the entire archive.

Seqcol's DRS now serves both the FASTA file directly and FAI index data via the `/objects/{id}/index` endpoint.

---

## Options evaluated

### Option 1: Expand seqcol to serve entire indexed FASTA bundle

Modify seqcol to store and serve FASTA + FAI + chrom.sizes as a unit.

**Pros:**
- Single source of truth
- One DRS endpoint for all FASTA-related files
- Refgenie asset structure unchanged

**Cons:**
- Violates seqcol's design principle of storing sequence metadata, not ancillary files
- Increases seqcol complexity beyond its intended scope
- FAI and chrom.sizes are derived data, not fundamental to sequence identity

**Assessment:** Not preferred. Seqcol should remain simple and focused on sequence collection metadata.

### Option 2: Store FASTA files twice (data duplication)

Store one copy in refgenie's asset tarball and a separate copy accessible via seqcol DRS.

**Pros:**
- No changes to either system's architecture
- Clear separation of concerns
- Both systems work independently

**Cons:**
- Storage duplication (FASTA files can be large)
- Maintenance burden of keeping copies synchronized
- Conceptually redundant

**Assessment:** Not preferred due to storage cost and redundancy.

### Option 3: Refgenie fasta asset contains only FAI (recommended)

Change the refgenie fasta asset to not contain the large FASTA data. The asset stores only the .fai file. Refgenie retrieves the FASTA file from seqcol DRS and chromosome sizes from seqcol metadata.

**Pros:**
- No data duplication
- Seqcol remains simple (no bundle serving)
- Single authoritative source for FASTA data
- Chromosome sizes already derivable from seqcol

**Cons:**
- Fasta assets behave differently than all other refgenie assets
- Refgenie must know to fetch FASTA from external source
- Adds dependency on seqcol service availability

**Assessment:** Preferred approach, but the behavioral difference from other assets is notable.

### Option 4: Eliminate fasta asset entirely (recommended)

Remove the "fasta asset" concept from refgenie altogether. All FASTA-related data is served by seqcol. Refgenie does not store or serve any fasta asset; clients retrieve FASTA data directly from seqcol service.

- FASTA file: served via seqcol DRS (already implemented)
- Chromosome sizes: derived from seqcol `names` + `lengths` (already available)
- FAI index: store FAI offsets in `FastaDrsObject`, serve via new seqcol endpoint

The "fasta asset" can be reconstructed on-the-fly from seqcol if needed, but refgenie has no need to serve it.

**Pros:**
- No data duplication
- No special-case asset behavior in refgenie
- Complete consolidation of FASTA-related data in seqcol
- Conceptually clean: genome initialization IS the fasta registration
- Seqcol becomes the single source of truth for all FASTA-related data

**Cons:**
- Refgenie users must use seqcol service for FASTA data

**Assessment:** This is the recommended approach and is now fully implementable. The refget package has implemented:
- FAI index fields in `FastaDrsObject`: `line_bases`, `extra_line_bytes`, `offsets`
- Automatic FAI computation in `FastaDrsObject.from_fasta_file()`
- FAI index endpoint at `GET /objects/{object_id}/index`

This fully consolidates FASTA handling into seqcol while keeping both systems focused on their core purposes.

---

## Implementation status

### FAI data in FastaDrsObject (implemented)

The FAI file format contains five columns per sequence:

```
NAME    LENGTH    OFFSET    LINEBASES    LINEWIDTH
chr1    248956422    52    80    81
chr2    242193529    252513167    80    81
```

Seqcol already stores `names` and `lengths`. The remaining fields are file-specific and are now stored in `FastaDrsObject`:

- `offsets`: byte position of first base for each sequence (list)
- `line_bases`: number of bases per line (e.g., 60)
- `extra_line_bytes`: extra bytes per line for newline (1 for `\n`, 2 for `\r\n`)

These values depend on the specific FASTA file's formatting, not the sequence content. Two FASTA files with identical sequences but different line wrapping have the same seqcol digest but different offsets.

Current implementation in `refget/models.py`:

```python
class FastaDrsObject(DrsObject, table=True):
    id: str = Field(primary_key=True)
    # ... existing fields ...

    # FAI index fields
    line_bases: Optional[int] = None  # Bases per line (e.g., 60)
    extra_line_bytes: Optional[int] = None  # Extra bytes per line for newline
    offsets: Optional[List[int]] = Field(default=None, sa_column=Column(JSON))
```

FAI data is automatically computed during `FastaDrsObject.from_fasta_file()` via the `_compute_fai_index()` method.

### FAI index endpoint (implemented)

The endpoint at `GET /objects/{object_id}/index` returns the FAI index data:

```python
@fasta_drs_router.get("/objects/{object_id}/index")
async def get_fasta_index(object_id: str, dbagent=Depends(get_dbagent)):
    """Get the FAI index data for a FASTA file."""
    drs_obj = dbagent.fasta_drs.get(object_id)
    return {
        "line_bases": drs_obj.line_bases,
        "extra_line_bytes": drs_obj.extra_line_bytes,
        "offsets": drs_obj.offsets,
    }
```

Clients can combine this with seqcol `names` and `lengths` to reconstruct a complete `.fai` file.

### DRS object ID strategy (pending decision)

The current implementation uses the seqcol digest as `FastaDrsObject.id`. This creates a potential collision: two FASTA files with identical sequences but different formatting would have the same ID.

**Option A: Keep seqcol digest as ID (current)**
- Simple: one FASTA per seqcol
- Constraint: server hosts only one FASTA file per sequence collection
- Acceptable if different file formats for the same sequences are not needed

**Option B: Use MD5 as ID**
- Use the file's MD5 hash as the DRS object ID
- Add `seqcol_digest` as a separate field for linking to sequence metadata

```python
return FastaDrsObject(
    id=md5_checksum_val,        # Unique per file (byte-for-byte)
    seqcol_digest=digest,       # Links to seqcol metadata
    ...
)
```

This would enable:
- Multiple FASTA files per seqcol (different formats of same sequences)
- DRS object ID that is truly file-specific
- Lookup by either file MD5 or seqcol digest

Would require adding a lookup endpoint:

```python
@fasta_drs_router.get("/objects/by-seqcol/{seqcol_digest}")
async def get_fastas_by_seqcol(seqcol_digest: str, dbagent=Depends(get_dbagent)):
    """List all FASTA DRS objects for a given seqcol digest"""
    return dbagent.fasta_drs.list_by_seqcol(seqcol_digest)
```

---

## Data flow after implementation

### Genome initialization

```
FASTA file
  → seqcol.add_from_fasta_file()
    → Creates SequenceCollection (names, lengths, sequences, etc.)
    → Creates FastaDrsObject with:
        - id = MD5 of FASTA file
        - seqcol_digest = sequence collection digest
        - fai_offsets, fai_linebases, fai_linewidth (computed from file)
        - access_methods (URLs where file is hosted)
  → Returns seqcol digest as genome identifier
```

### Client retrieval

| Request | Endpoint | Source |
|---------|----------|--------|
| FASTA file | `GET /fasta/objects/{md5}` → follow access_url | DRS |
| Chromosome sizes | `GET /collection/{seqcol_digest}?level=2` → combine names+lengths | Seqcol |
| FAI index | `GET /fasta/objects/{md5}/fai` | DRS + Seqcol (derived) |
| Sequence metadata | `GET /collection/{seqcol_digest}` | Seqcol |

---

## Open questions

1. **Refgenie integration**: How does refgenie expose these seqcol endpoints to its users? Does it proxy requests or redirect to seqcol?

2. ~~**FAI computation timing**: Should FAI offsets be computed during `add_from_fasta_file()` or lazily on first request?~~ **Resolved**: FAI offsets are computed during `FastaDrsObject.from_fasta_file()`.

3. **Access method population**: Who is responsible for setting `access_methods` on `FastaDrsObject`? The seqcol service or the caller?

4. **DRS object ID strategy**: Should the ID be the seqcol digest (simple, one FASTA per seqcol) or MD5 (allows multiple FASTAs per seqcol)? See "DRS object ID strategy" section above.

5. **Lookup semantics** (only relevant if MD5 ID is adopted): If a client has a seqcol digest and wants the FASTA file, but multiple FASTAs exist for that seqcol, which one is returned?

6. **Refgenie fasta asset removal**: What changes are needed in refgenie to eliminate the fasta asset class and direct users to seqcol for FASTA data?

---

## Summary of components after implementation

| Data | Stored in | Served via |
|------|-----------|------------|
| Sequence names | `NamesAttr` (seqcol) | `GET /collection/{digest}?level=2` |
| Sequence lengths | `LengthsAttr` (seqcol) | `GET /collection/{digest}?level=2` |
| Sequence digests | `SequencesAttr` (seqcol) | `GET /collection/{digest}?level=2` |
| FASTA file bytes | External storage (S3, etc.) | `GET /fasta/objects/{id}` → access_url |
| FASTA file metadata | `FastaDrsObject` | `GET /fasta/objects/{id}` |
| FAI index data | `FastaDrsObject` (line_bases, extra_line_bytes, offsets) | `GET /fasta/objects/{id}/index` |
| Chromosome sizes | Derived from names+lengths | Client combines from seqcol |

---

## Appendix A: Glossary

- **Seqcol**: Sequence collection; a GA4GH standard for representing sets of sequences with their metadata
- **DRS**: Data Repository Service; a GA4GH standard for accessing data objects via URIs
- **FAI**: FASTA index file; enables random access into a FASTA file
- **Seek key**: Refgenie term for a named file within an asset (e.g., "fasta", "fai", "chrom_sizes")
- **Asset class**: Refgenie template defining what files an asset type contains
- **Digest**: Cryptographic hash used as identifier (seqcol uses sha512t24u, files use MD5/SHA-256)

## Appendix B: Related files

- Refget models: `repos/refget/refget/models.py`
- Refget router: `repos/refget/refget/refget_router.py`
- Refget agents: `repos/refget/refget/agents.py`
- Refgenie models: `repos/refgenie1/packages/refgenie/refgenie/db/models.py`
- Refgenie main: `repos/refgenie1/packages/refgenie/refgenie/refgenie.py`
- Fasta asset class: `repos/refgenie1/packages/refgenie/refgenie/schemas/fasta_asset_class.yaml`
- Original DRS plan: `plans/refget-drs-implementation.md`
