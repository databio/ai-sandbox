# Refgenie Workspace

Reference genome management ecosystem - tools for managing, serving, and accessing reference genome assets following GA4GH standards.

## Workspace Structure

This is a **workspace** - a folder grouping related repos for coordinated work.

- `repos/` - Git clones (gitignored, not tracked here)
- `plans/` - Design documents and implementation plans
- `progress.md` - AI session logs
- `journal.md` - Human work log

**File locations:** All plans and progress go in THIS folder (workspace root), never inside `repos/` subdirectories.

## Repository Overview

### Core Libraries

- **refget** (`repos/refget/`) - Python package implementing GA4GH refget standards for sequences and sequence collections (seqcol). Includes:
  - `/refget` - Core Python library with clients, agents, and database models
  - `/seqcolapi` - FastAPI wrapper providing Sequence Collections API service
  - `/frontend` - React frontend for seqcolapi
  - `/deployment` - Server configs and GitHub workflows for AWS ECS deployment
  - `/test_fasta`, `/test_api` - Compliance testing

- **refgenconf** (`repos/refgenconf/`) - Configuration object library for refgenie

- **refgenie1** (`repos/refgenie1/`) - Main refgenie package (version 1)
- **refget-ga4gh** (`repos/refget-ga4gh`) - Standard specification, technical details, for both refget sequences and refget sequence collections (seqcol).

### Server Implementations

- **refgenieserver** (`repos/refgenieserver/`) - API server for serving reference genomes. Can `archive` a refgenie folder and `serve` it via HTTP
- **seqcolapi** (`repos/seqcolapi/`) - Sequence Collections API server (based on refget package)

### Deployment & Infrastructure

- **refgenomes.databio.org** (`repos/refgenomes.databio.org/`) - Public refgenie server deployment
- **rg.databio.org** (`repos/rg.databio.org/`) - Refgenie web interface deployment
- **server_deploy_demo** (`repos/server_deploy_demo/`) - Example server deployment
- **rg_deploy_demo** (`repos/rg_deploy_demo/`) - Example refgenie deployment

### Plugins & Extensions

- **refgenie_myplugin** (`repos/refgenie_myplugin/`) - Example plugin template
- **refgenie_nfcore** (`repos/refgenie_nfcore/`) - nf-core integration

### Demos & Documentation

- **refgenie-docs** (`repos/refgenie-docs/`) - User documentation (hosted at refgenie.org)
- **refgenie_looper_demo** (`repos/refgenie_looper_demo/`) - Demo of refgenie + looper integration

### Standards & Specifications

- **refget-ga4gh** (`repos/refget-ga4gh/`) - GA4GH refget specification (upstream spec repo)
- **ref_decoy** (`repos/ref_decoy/`) - Decoy sequence handling

### Supporting Libraries

- **yacman** (`repos/yacman/`) - YAML configuration management (dependency)

## Key Concepts

### GA4GH Standards
- **Refget sequences**: Standard for retrieving reference sequences by digest
- **Sequence collections (seqcol)**: Standard for representing and comparing sets of sequences with metadata
- **DRS (Data Repository Service)**: Standard for accessing data objects via URIs

### Seqcol Data Model
A sequence collection contains:
- `names` - Array of sequence/chromosome names
- `lengths` - Array of sequence lengths
- `sequences` - Array of GA4GH sequence digests
- `name_length_pairs` - Combined name-length data
- `sorted_name_length_pairs` - Sort-invariant coordinate system identifier

### Refgenie Assets
Refgenie organizes genomic data into "assets" - bundles of related files. The "fasta" asset traditionally includes:
- The FASTA file
- FASTA index (.fai)
- Chromosome sizes (.chrom.sizes)

## Architecture Notes

### FASTA Data Flow (Current Direction)
The workspace is moving toward consolidating FASTA handling in seqcol/refget rather than refgenie:
- FASTA files served via DRS endpoints
- FAI index data stored in `FastaDrsObject`
- Chromosome sizes derived from seqcol `names` + `lengths`

See `plans/seqcol_refgenie_fasta_integration_guide.md` for detailed design discussion.

### Key Files in refget Package
- `refget/models.py` - SQLModel definitions including `FastaDrsObject`, `SequenceCollection`
- `refget/agents.py` - Database agents (`RefgetDBAgent`, `SeqColAgent`, `FastaDrsAgent`)
- `refget/refget_router.py` - FastAPI routes for seqcol and DRS endpoints
- `refget/clients.py` - Client classes for remote API access

## Development

### Running refget locally
```bash
cd repos/refget
bash deployment/demo_up.sh  # Launches postgres + uvicorn with demo data
```

### Running tests
```bash
cd repos/refget
pytest  # Local unit tests
```

### Documentation
- User docs: https://refgenie.org
- Refget package docs: https://refgenie.org/refget/

## Architecture Decision Records (ADRs)

Significant architecture decisions are documented in `repos/refgenie-docs/docs/decisions/`.

**Format:** `YYYY-MM-DD-short-description.md`

ADRs should include:
- **Date** and **Status** (Proposed/Accepted/Deprecated)
- **Context** - What problem are we solving?
- **Decision** - What did we decide?
- **Rationale** - Why this choice over alternatives?
- **Consequences** - Positive, negative, and neutral impacts

Use ADRs for decisions that affect multiple repos or have long-term architectural implications.

## Active Work Areas

Check `plans/` for current design documents and `journal.md` for recent work context.
