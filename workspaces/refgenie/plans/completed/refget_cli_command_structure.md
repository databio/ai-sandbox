# Refget CLI Command Structure

**Status**: Revised - Ready for implementation

This document defines the refget CLI structure with two main interfaces: RefgetStore (for sequences/FASTAs) and SeqCol API (for comparisons/metadata).

## Design Principles

1. **Two main interfaces**: `store` (RefgetStore) and `seqcol` (SeqCol API)
2. **Configuration-driven**: Set up once, commands "just work"
3. **Consistent flags**: `--server` for any remote URL override
4. **SeqCol JSON as exchange format**: `.seqcol.json` files are first-class citizens
5. **Progressive disclosure**: Simple commands visible, advanced features discoverable

## Configuration System

### Config File

**Location:** `~/.refget/config.toml` (override with `REFGET_CONFIG` env var)

```toml
# Local RefgetStore cache
[store]
path = "~/.refget/store"

# Remote RefgetStores (tried in order)
[[remote_stores]]
url = "s3://primary-bucket/store/"
name = "primary"

[[remote_stores]]
url = "https://backup.example.com/store/"
name = "backup"

# Remote seqcol servers (tried in order)
[[seqcol_servers]]
url = "https://seqcolapi.databio.org"
name = "databio"

[[seqcol_servers]]
url = "https://internal.myorg.com/seqcol"
name = "internal"

# Remote sequence servers (tried in order)
[[sequence_servers]]
url = "https://www.ebi.ac.uk/ena/cram"
name = "ebi"

# Admin database (compatible with refgenie)
[admin]
postgres_host = "localhost"
postgres_port = "5432"
postgres_db = "refget"
postgres_user = "admin"
# postgres_password via POSTGRES_PASSWORD env var
```

### Environment Variables

| Env Var | Overrides | Notes |
|---------|-----------|-------|
| `REFGET_CONFIG` | Config file path | Default: `~/.refget/config.toml` |
| `REFGET_STORE_PATH` | `store.path` | Local cache path |
| `REFGET_STORE_URL` | `remote_stores` | Single URL only |
| `REFGET_SEQCOL_URL` | `seqcol_servers` | Single URL only |
| `REFGET_SEQUENCE_URL` | `sequence_servers` | Single URL only |
| `POSTGRES_HOST` | `admin.postgres_host` | Compatible with refgenie |
| `POSTGRES_PORT` | `admin.postgres_port` | |
| `POSTGRES_DB` | `admin.postgres_db` | |
| `POSTGRES_USER` | `admin.postgres_user` | |
| `POSTGRES_PASSWORD` | `admin.postgres_password` | |

**Priority:** Command-line flag > env var > config file > built-in default

### Config Commands

```bash
refget config init                              # Interactive setup wizard
refget config show                              # View all config
refget config get <key>                         # Get specific value
refget config set <key> <value>                 # Set a value
refget config add seqcol_server <url> [--name]  # Add server to list
refget config add remote_store <url> [--name]   # Add store to list
refget config remove seqcol_server <name>       # Remove from list
```

## Command Structure

### Store Commands (RefgetStore - collections and sequences)

```bash
refget store init [--path <dir>]                # Initialize local store
refget store add <fasta>                        # Import FASTA to local store
refget store list                               # List collections in store
refget store pull <digest>                      # Pull collection from remote
refget store pull --file <digests.txt>          # Batch pull from file
refget store export <digest> -o out.fa          # Export collection as FASTA
refget store export <digest> --bed regions.bed  # Export regions from BED
refget store seq <seq_digest>                   # Get full sequence by digest
refget store seq <seq_digest> --start 100 --end 200  # Get subsequence
refget store seq <coll_digest> --name chr1      # Get sequence from collection
refget store seq <coll_digest> --name chr1 --start 100 --end 200  # Subsequence from collection
refget store fai <digest> -o out.fai            # Generate .fai index
refget store chrom-sizes <digest> -o out.sizes  # Generate chrom.sizes
refget store stats                              # Store statistics
```

**Note:** Store operates on collections (add FASTA → creates collection). Individual sequences accessed by their digest or by collection + name.

**Pull resolution order:**
1. Check local store (already cached?)
2. Try `remote_stores` in priority order
3. Try `seqcol_servers` (query service-info for RefgetStore URL)
4. Fail with helpful message

### FASTA Commands (standalone file utilities)

```bash
refget fasta index <file>                       # Generate ALL derived files at once
refget fasta digest <file>                      # Compute seqcol digest (top-level)
refget fasta seqcol <file> -o out.seqcol.json   # Compute full seqcol JSON
refget fasta seqcol <file> --level 1            # Compute level 1 (attribute digests)
refget fasta fai <file> -o out.fai              # Compute FAI index
refget fasta chrom-sizes <file> -o out.sizes    # Compute chrom.sizes
refget fasta rgsi <file> -o out.rgsi            # Compute .rgsi (RefgetStore sequence index)
refget fasta rgci <file> -o out.rgci            # Compute .rgci (RefgetStore collection index)
refget fasta stats <file>                       # Stats (count, total length, N50, etc.)
```

**`fasta index` output:** For `genome.fa`, creates:
- `genome.fa.fai` - FASTA index (samtools-compatible)
- `genome.seqcol.json` - Sequence collection JSON
- `genome.chrom.sizes` - Chromosome sizes
- `genome.rgsi` - RefgetStore sequence index (binary, for efficient sequence lookup)
- `genome.rgci` - RefgetStore collection index (binary, for collection metadata)
- Prints digest to stdout

**RefgetStore index files (.rgsi/.rgci):** These are binary index files used by RefgetStore for efficient on-disk sequence storage and retrieval. The `.rgsi` maps sequence digests to byte offsets; `.rgci` stores collection metadata. These are created by `fasta index` or individually when pre-computing indexes before loading into a store.

**Note:** These are standalone utilities that work directly on FASTA files without requiring a store or server.

### SeqCol Commands (API - comparisons and metadata)

```bash
refget seqcol show <digest>                     # Get seqcol (local store first, then server)
refget seqcol show <digest> --level 1           # Get level 1 (digests only)
refget seqcol compare <a> <b>                   # Compare two seqcols
refget seqcol list                              # List collections on server
refget seqcol search --names <attr_digest>      # Find collections by names array digest
refget seqcol search --lengths <attr_digest>    # Find collections by lengths array digest
refget seqcol attribute <attr_digest>           # Retrieve attribute array by its digest
refget seqcol info                              # Server info/capabilities
```

**Resolution order for `show`:** local store → configured seqcol_servers → `--server` override

**Flexible inputs for compare:**
- `<fasta>` - computes seqcol on the fly
- `<seqcol.json>` - uses local seqcol file
- `<digest>` - fetches from local store or server

**seqcol search:** Finds collections that share an attribute. The `<attr_digest>` is the digest of an attribute array (e.g., the names array digest from level 1 output).

**seqcol attribute:** Retrieves the actual array values given an attribute digest. This hits the `/attribute/collection/<digest>` API endpoint.

### Admin Commands (PostgreSQL infrastructure)

```bash
refget admin load <fasta>                       # Load seqcol metadata from FASTA
refget admin load <seqcol.json>                 # Load seqcol metadata from JSON
refget admin load --pep <project.yaml>          # Batch load from PEP
refget admin register <fasta> --bucket <name>   # Upload FASTA to S3, create DRS record
refget admin ingest <fasta> --bucket <name>     # Load metadata + register FASTA
```

**Admin command details:**
- `load` - Parses input (FASTA or .seqcol.json) and stores seqcol metadata in PostgreSQL
- `register` - Uploads FASTA to S3 bucket and creates DRS object record for access
- `ingest` - Combines load + register in one step

## Exchange Format: SeqCol JSON

The `.seqcol.json` file is the portable exchange format:

```json
{
  "names": ["chr1", "chr2", "chr3"],
  "lengths": [248956422, 242193529, 198295559],
  "sequences": ["SQ.abc...", "SQ.def...", "SQ.ghi..."]
}
```

This can be:
- Computed from FASTA (`refget fasta seqcol`)
- Saved to file and shared
- Compared with remote collections
- Used offline without the full FASTA

## Example Workflows

### Workflow 1: First-time setup

```bash
# Interactive configuration
refget config init
# "Local store path? [~/.refget/store]: "
# "Add a seqcol server? [https://seqcolapi.databio.org]: "
# "Add a remote RefgetStore? []: "
# Config saved to ~/.refget/config.toml
```

### Workflow 2: Download and cache genomes

```bash
# Pull uses configured servers automatically
refget store pull abc123def456
# Checking local store... not found
# Trying https://seqcolapi.databio.org... found store
# Pulling abc123def456... done

# Export to FASTA
refget store export abc123def456 -o genome.fa

# Extract specific regions
refget store export abc123def456 --bed regions.bed -o regions.fa
```

### Workflow 3: Compare local FASTA with remote reference

```bash
# Option 1: Direct comparison
refget seqcol compare my_genome.fa abc123

# Option 2: Compute seqcol first, then compare
refget fasta seqcol my_genome.fa -o my.seqcol.json
refget seqcol compare my.seqcol.json abc123

# Find collections that share the same chromosome names
# Step 1: Get the names array digest (level 1)
names_digest=$(refget fasta seqcol my_genome.fa --level 1 | jq -r '.names')
# Step 2: Search for collections with that names digest
refget seqcol search --names $names_digest
```

### Workflow 4: Generate index files without full FASTA

```bash
# Get .fai and chrom.sizes from store or server
refget store fai abc123 -o genome.fa.fai
refget store chrom-sizes abc123 -o genome.chrom.sizes
```

### Workflow 5: Admin - load genomes to server

```bash
# Set up database connection
export POSTGRES_HOST=localhost
export POSTGRES_DB=refget
export POSTGRES_USER=admin
export POSTGRES_PASSWORD=secret

# Load and register with cloud storage
refget admin ingest genome.fa --bucket my-refget-bucket

# Batch load from PEP
refget admin ingest --pep genomes.yaml --fa-root /data/fasta --bucket my-bucket
```

### Workflow 6: Quick sequence lookup

```bash
# Get full sequence by its digest
refget store seq def456

# Get subsequence from a known sequence digest
refget store seq def456 --start 1000 --end 2000

# Get sequence from collection by name
refget store seq abc123 --name chr1

# Get subsequence from collection by name + range
refget store seq abc123 --name chr1 --start 1000000 --end 1001000
```

### Workflow 7: FASTA file utilities

```bash
# Generate ALL derived files at once
refget fasta index genome.fa
# → Creates: genome.fa.fai, genome.seqcol.json, genome.chrom.sizes,
#            genome.rgsi, genome.rgci
# → Prints: abc123def456... (the digest)

# Or generate individual files as needed
refget fasta digest genome.fa           # Just the digest
refget fasta fai genome.fa              # Just the .fai
refget fasta stats genome.fa            # File statistics
```

## Server Override

All commands accept `--server` to override configured defaults:

```bash
refget store pull abc123 --server s3://other-bucket/store/
refget seqcol compare a b --server https://other-api.com
refget store fai abc123 --server https://internal.myorg.com
```

## Dependencies by Command Group

| Command Group | Required Packages |
|---------------|-------------------|
| `store *` | `gtars` |
| `fasta *` | `gtars` |
| `seqcol *` | `requests` |
| `admin *` | `sqlmodel`, `psycopg2`, `boto3` |
| `config *` | (none) |

### Graceful Dependency Handling

```bash
refget store pull abc123
# Error: 'store' commands require gtars.
# Install with: pip install refget[store]

refget admin load genome.fa
# Error: 'admin' commands require PostgreSQL support.
# Install with: pip install refget[admin]
```

## Help Output

```
usage: refget <command> [options]

GA4GH refget CLI - reference sequence access and management

Commands:

  Store (local/remote RefgetStore):
    store init          Initialize local store
    store add           Import FASTA to store
    store list          List collections
    store pull          Pull collection from remote
    store export        Export collection as FASTA
    store seq           Get sequence/subsequence
    store fai           Generate .fai from digest
    store chrom-sizes   Generate chrom.sizes from digest
    store stats         Store statistics

  FASTA (standalone file utilities):
    fasta index         Generate ALL derived files
    fasta digest        Compute seqcol digest
    fasta seqcol        Compute full seqcol JSON
    fasta fai           Compute .fai index
    fasta chrom-sizes   Compute chrom.sizes
    fasta rgsi          Compute .rgsi (sequence index)
    fasta rgci          Compute .rgci (collection index)
    fasta stats         File statistics

  SeqCol (sequence collection API):
    seqcol show         Get seqcol (local or remote)
    seqcol compare      Compare two seqcols
    seqcol list         List collections on server
    seqcol search       Find collections by attribute digest
    seqcol attribute    Retrieve attribute array by digest
    seqcol info         Server capabilities

  Config:
    config init         Interactive setup
    config show         Show configuration
    config set          Set config value
    config add          Add server to list

  Admin (server infrastructure):
    admin load          Load seqcol to database
    admin register      Upload FASTA to cloud
    admin ingest        Load + register

Use 'refget <command> --help' for more information.
```

## RefgetStore API Reference

```python
from gtars.refget import RefgetStore

# Constructors
store = RefgetStore.in_memory()
store = RefgetStore.on_disk("/path/to/store")
store = RefgetStore.load_remote("/cache", "s3://bucket/store/")

# Adding data
store.add_sequence_collection_from_fasta("genome.fa")

# Querying
store.list_collections()
store.get_sequence(seq_digest)
store.get_substring(seq_digest, start, end)

# Exporting
store.export_fasta(collection_digest, "out.fa")
store.export_fasta(digest, "out.fa", ["chr1", "chr2"])  # subset

# BED extraction
store.export_fasta_from_regions(collection_digest, "regions.bed", "out.fa")
```

## Migration from Current CLI

```
Current Command      → New Command
────────────────────────────────────────────
load                 → admin load
register             → admin register
load-and-register    → admin ingest
digest-fasta         → fasta digest
digest-fasta -l 2    → fasta seqcol
```

## Output Format by Command

Commands are categorized by their output format requirements:

### JSON-Only (Machine-Oriented)

These commands output pretty-printed JSON by default. Use `jq` to extract fields.

| Command | Example Output |
|---------|----------------|
| `fasta digest` | `{"digest": "abc123...", "file": "genome.fa"}` |
| `fasta seqcol` | `{"names": [...], "lengths": [...], "sequences": [...]}` |
| `store add` | `{"digest": "abc123...", "sequences": 25}` |
| `store list` | `{"collections": [{"digest": "...", "sequences": N}, ...]}` |
| `store stats` | `{"collections": 3, "sequences": 75, "total_size": "2.1 GB"}` |
| `seqcol show` | Full seqcol JSON structure |
| `seqcol compare` | `{"compatible": true, "shared_sequences": 24, ...}` |
| `seqcol search` | `{"matches": [{"digest": "...", ...}, ...]}` |
| `seqcol attribute` | `["chr1", "chr2", ...]` (the actual array values) |
| `seqcol info` | Server capabilities JSON |
| `config show` | Config structure |
| `config get` | `{"value": "..."}` |

### Human-Readable Only (Standard Formats)

These commands output standard bioinformatics formats.

| Command | Output Format |
|---------|---------------|
| `fasta fai` | Tab-separated `.fai` format (samtools-compatible) |
| `fasta chrom-sizes` | Tab-separated `chrom.sizes` (UCSC-compatible) |
| `fasta rgsi` / `rgci` | Binary index files |
| `store fai` | Same as fasta fai |
| `store chrom-sizes` | Same as fasta chrom-sizes |
| `store seq` | Raw sequence (FASTA or plain bases) |
| `store export` | FASTA file |
| `config init` | Interactive wizard |

### Both Options

| Command | `--json` | Default |
|---------|----------|---------|
| `fasta stats` | `{"sequences": N, ...}` | Pretty table |
| `fasta index` | `{"digest": "...", "files": [...]}` | Progress + digest |

## Exit Codes

Consistent exit codes across all commands:

| Exit Code | Meaning | Example |
|-----------|---------|---------|
| 0 | Success / compatible | Digest computed, comparison shows compatibility |
| 1 | Failure / incompatible | Comparison shows incompatibility |
| 2 | File not found or I/O error | Missing input file |
| 3 | Network/server error | Server unreachable, timeout |
| 4 | Configuration error | Missing required config |

**Scripting-friendly:** Exit codes enable `&&` chaining and conditionals:

```bash
# Chain commands
refget fasta digest genome.fa && echo "Digest computed"

# Use comparison exit code
if refget seqcol compare genome.fa reference --quiet; then
  echo "Compatible with reference"
fi
```

## Gzip Handling

**All `fasta` and `store` commands seamlessly handle `.gz` files.** No special flags needed.

The underlying Rust library (`gtars`) uses `flate2::MultiGzDecoder` to auto-detect and decompress gzipped input. Digests are computed on decompressed data, so `genome.fa` and `genome.fa.gz` produce identical digests.

**FAI limitation:** For `.gz` files, byte offsets in FAI output are unavailable (cannot seek in compressed streams). The FAI is still generated with name/length data.

## Next Steps

1. Implement config system (`config init/show/set/get`)
2. Implement fasta commands (digest, seqcol, fai, chrom-sizes, rgsi, rgci, stats)
3. Implement store commands with config integration
4. Implement seqcol commands
5. Rename admin commands (keep aliases for backward compat)
6. Update documentation
7. Implement CLI test suite (see `refget_cli_testing_plan.md`)

## References

- RefgetStore docs: `repos/refgenie-docs/docs/refget/notebooks/refgetstore.ipynb`
- Client library: `repos/refget/refget/clients.py`
- Service-info plan: `plans/seqcolapi_service_info_capabilities_plan_v1.md`
