# Implementation plan for Refget Documentation Gap Analysis and Remediation

## The issue

The refget Python package documentation has improved substantially but still lacks:

1. **Audience-first organization** - Documentation should be organized by user persona (users vs server operators), with Reference and Explanation as shared sections.

2. **Proper type labeling** - Many documents are mislabeled. The four types (Tutorial, How-to, Reference, Explanation) should inform *how we write* each doc, while nav structure serves *how users navigate*.

3. **New feature coverage** - Pangenomes, FastaDrsClient, and processing module details remain undocumented.

4. **Architecture/Explanation content** - No high-level overview of how components interact or why design decisions were made.

---

## Key Insight: Audience-First Organization

When a tool has distinct user personas, organize by **audience** at the top level, not by doc type:

- **Using refget services** - For end users (computing digests, querying APIs, local storage)
- **Hosting refget services** - For server operators (database setup, API deployment, compliance)
- **Reference** - Shared (CLI, formats, API docs)
- **Explanation** - Shared (architecture, design rationale)

The four documentation types guide **how you write** each document. The nav structure optimizes for **how users find** things.

---

## Documentation Evaluation (Four Types System)

### Current Document Classification

| Document | Actual Type | Sticks to Type? | Notes |
|----------|-------------|-----------------|-------|
| `README.md` | Landing page | YES | Fine as landing page |
| `introduction.md` | **Explanation** | YES | Describes what/why components exist |
| `cli.md` | **Reference** | YES | Complete command reference |
| `fastapi_router.md` | **How-to** | YES | Goal: "How to add endpoints" |
| `compliance.md` | **How-to** | YES | Goal: "How to test compliance" |
| `refgetstore.py` | **How-to** | YES | Goal: "How to use RefgetStore" |
| `digests.ipynb` | **How-to** | YES | Goal: "How to compute digests" |
| `sequence-client.ipynb` | **How-to** | YES | Goal: "How to query sequence APIs" |
| `seqcol-client.ipynb` | **How-to** | YES | Goal: "How to query seqcol APIs" |
| `agent.ipynb` | **How-to** | **NO** | Has reference table embedded (sub-agents) |
| `refgetstore-format.md` | **Reference** | YES | Specification document |
| `models.md` | **Reference** | YES | API reference (auto-generated) |
| `reference_docs.md` | **Reference** | YES | API reference (auto-generated) |
| `changelog.md` | Changelog | YES | N/A |

### Practical Test: Tutorial vs How-to

> "Did the reader arrive with a goal, or are they here to learn?"

- **Arrived with a goal → How-to** (most practical docs)
- **Here to learn → Tutorial** (rare, for onboarding newcomers)

Most of the notebooks are **how-tos** - users arrive wanting to accomplish something specific (compute a digest, query an API, set up a database).

### Document-Level Issues Found

#### `agent.ipynb` - MIXED (needs cleanup)

| Element | Type | Problem? |
|---------|------|----------|
| "Tutorial" title | - | Misleading - it's a how-to |
| Prerequisites section | How-to | Fine |
| Code examples | How-to | Fine |
| Sub-agents table | **Reference** | Should be in reference docs |
| Cell ordering | - | Markdown cells out of order with code |

**Recommended fixes:**
1. Remove "Tutorial" from title
2. Extract sub-agents table to `reference_docs.md`
3. Fix cell ordering (markdown before corresponding code)

#### `fastapi_router.md` - CLEAN

Sticks to how-to type. No changes needed.

#### `compliance.md` - CLEAN

Sticks to how-to type. No changes needed.

---

## Current Documentation State (as of 2025-01)

### What's Now Well-Documented

| Component | Documentation | Notes |
|-----------|--------------|-------|
| CLI | cli.md (770 lines) | Comprehensive coverage of all 5 command groups |
| RefgetStore | refgetstore.py + refgetstore-format.md | Tutorial + format specification |
| Digest functions | digests.ipynb | Shows gtars integration |
| SequenceClient | sequence-client.ipynb | Complete tutorial |
| SequenceCollectionClient | seqcol-client.ipynb | Complete tutorial |
| RefgetDBAgent | agent.ipynb | Basic usage with sub-agents mentioned |
| FastAPI router | fastapi_router.md | Minimal but functional example |
| Models | models.md | Auto-generated via mkdocstrings |
| API reference | reference_docs.md | Auto-generated via mkdocstrings |

### Remaining Gaps

| Component | Type | Priority |
|-----------|------|----------|
| **Nav reorganization (User/Server tracks)** | Organization | High |
| **Pangenomes** | Missing docs | Medium |
| **FastaDrsClient** | Missing tutorial | Medium |
| **Architecture overview** | Missing docs | Medium |
| **Processing module** | Missing docs | Low |
| **Troubleshooting/FAQ** | Missing docs | Low |

## Files to read for context

### Code (refget package)
- `/home/nsheff/Dropbox/workspaces/refgenie/repos/refget/refget/__init__.py` - Public API exports (lazy loading)
- `/home/nsheff/Dropbox/workspaces/refgenie/repos/refget/refget/models.py` - SQLModel data models (618 lines)
- `/home/nsheff/Dropbox/workspaces/refgenie/repos/refget/refget/agents.py` - Database agents (761 lines)
- `/home/nsheff/Dropbox/workspaces/refgenie/repos/refget/refget/clients.py` - HTTP clients (781 lines)
- `/home/nsheff/Dropbox/workspaces/refgenie/repos/refget/refget/processing/` - Processing submodule (gtars bridge)
- `/home/nsheff/Dropbox/workspaces/refgenie/repos/refget/refget/cli/` - Typer CLI (7628 lines total)

### Existing Docs
- `/home/nsheff/Dropbox/workspaces/refgenie/repos/refgenie-docs/docs/refget/` - Documentation root
- `/home/nsheff/Dropbox/workspaces/refgenie/repos/refgenie-docs/mkdocs.yml` - Nav structure (lines 119-141)

## Current mkdocs.yml Structure (refget section)

```yaml
- Refget:
    - Getting started:
        - Getting started: refget/README.md
    - How-to guides:
        - Introduction: refget/introduction.md
        - Computing digests: refget/notebooks/digests.ipynb
        - RefgetStore: refget/notebooks/refgetstore.py
        - Sequences Client: refget/notebooks/sequence-client.ipynb
        - Sequence Collections Client: refget/notebooks/seqcol-client.ipynb
        - RefgetDB Agent: refget/notebooks/agent.ipynb
        - Adding a fastAPI router: refget/fastapi_router.md
        - Compliance testing: refget/compliance.md
        - Command-line interface: refget/cli.md
    - Reference:
        - RefgetStore file format: refget/refgetstore-format.md
        - Changelog: refget/changelog.md
        - Refget Python API: refget/reference_docs.md
        - Pydantic models: refget/models.md
```

## Proposed mkdocs.yml Structure

Reorganize following **audience-first** pattern with shared Reference and Explanation:

```yaml
- Refget:
    - Getting started: refget/README.md
    - Using refget services:
        - Computing digests: refget/notebooks/digests.ipynb
        - RefgetStore (local storage): refget/notebooks/refgetstore.py
        - Python SequenceClient: refget/notebooks/sequence-client.ipynb
        - Python SequenceCollectionsClient: refget/notebooks/seqcol-client.ipynb
    - Hosting refget services:
        - RefgetDB Agent: refget/notebooks/agent.ipynb
        - Adding a FastAPI router: refget/fastapi_router.md
        - Compliance testing: refget/compliance.md
    - Reference:
        - CLI reference: refget/cli.md
        - RefgetStore format: refget/refgetstore-format.md
        - Pydantic models: refget/models.md
        - Python API: refget/reference_docs.md
        - Changelog: refget/changelog.md
    - Explanation:
        - Package components: refget/introduction.md
        - Architecture overview: refget/architecture.md  # NEW
```

### Why This Structure?

1. **Audience-first** - Users pick their track (using vs hosting) immediately
2. **Content flows naturally** - Within each track, how-tos grouped together
3. **Reference is shared** - CLI, API docs serve both audiences
4. **Explanation is shared** - Architecture helps everyone understand the system
5. **No forced Tutorial/How-to labels** - The four types inform writing, not nav

## Implementation Steps

### Step 1: Reorganize mkdocs.yml Navigation (Audience-First)

**Status: COMPLETE**

Updated nav to follow audience-first pattern with shared Reference and Explanation.

**Final structure:**
```yaml
- Refget:
    - Getting started: refget/README.md
    - Using refget services:
        - Computing digests
        - RefgetStore (local storage)
        - Python SequenceClient
        - Python SequenceCollectionsClient
    - Hosting refget services:
        - RefgetDB Agent
        - Adding a FastAPI router
        - Compliance testing
    - Reference:
        - CLI reference
        - RefgetStore format
        - Pydantic models
        - Python API
        - Changelog
    - Explanation:
        - Package components (introduction.md)
```

**Changes made:**
1. Created "Using refget services" section for end users
2. Created "Hosting refget services" section for server operators
3. Moved `cli.md` to "Reference" (shared across audiences)
4. Created "Explanation" section with `introduction.md`

### Step 1b: Fix agent.ipynb type mixing

**Status: TODO**

The `agent.ipynb` file mixes how-to content with reference content:

1. Remove "Tutorial" from title (it's a how-to)
2. Extract sub-agents reference table to `reference_docs.md`
3. Fix cell ordering (markdown cells out of order with code cells)

### Step 2: Create FASTA DRS Client How-to

Create new how-to: `docs/refget/notebooks/fasta-drs-client.py`

Cover:
- `FastaDrsClient` initialization
- `get_object()` - retrieve DRS metadata
- `get_index()` - get FAI index data
- `download()` - stream FASTA to disk
- `download_to_store()` - import directly to RefgetStore
- `build_fai()`, `write_fai()` - index generation

Use percent format (`.py`) per CLAUDE.md guidelines.

### Step 3: Create Pangenome Client How-to

Create new how-to: `docs/refget/notebooks/pangenome-client.py`

Cover:
- What pangenomes are (collection of sequence collections)
- `PangenomeClient` initialization
- Querying pangenomes from remote API
- `PangenomeAgent` CRUD operations (for servers)
- `build_pangenome_model()` utility

### Step 4: Create Architecture Overview

Create new file: `docs/refget/architecture.md`

Cover:
- Component diagram showing:
  - CLI → Processing/Agents → Database
  - Clients → Remote APIs
  - FastAPI Router integration
  - RefgetStore ↔ gtars relationship
- Data flow for common operations:
  - Loading FASTA → Database
  - Remote client query
  - RefgetStore operations
- When to use which component (decision guide)
- Lazy loading architecture in `__init__.py`

### Step 5: Create Processing Module Documentation

Create new file: `docs/refget/processing.md`

Cover:
- Installation note: requires `gtars` dependency
- Module guard (ImportError handling)
- Digest functions:
  - `sha512t24u_digest()`, `md5_digest()`, `digest_fasta()`
- FASTA processing:
  - `fasta_to_seqcol_dict()` - convert FASTA to canonical seqcol
  - `fasta_to_digest()` - get seqcol digest from FASTA
  - `create_fasta_drs_object()` - build FastaDrsObject with checksums
- Bridge functions:
  - `seqcol_from_gtars()` - convert gtars types to Python models
- RefgetStore re-exports from gtars:
  - `RefgetStore`, `StorageMode`, `RetrievedSequence`

### Step 6: Expand Agent Documentation

Update existing `agent.ipynb` or create `docs/refget/agents.md`

Add detail on sub-agents:
- `SequenceAgent` - `get()`, `add()`, `list()`
- `SequenceCollectionAgent` - `get()` levels, `add_from_fasta_file()`, `add_from_fasta_pep()`
- `FastaDrsAgent` - `get()`, `add()`, `list()`
- `AttributeAgent` - query and manage collection attributes
- `PangenomeAgent` - pangenome collection management

### Step 7: Update mkdocs-jupyter Plugin Config

Add new `.py` files to the plugin include list:

```yaml
plugins:
  - mkdocs-jupyter:
      include:
        # ... existing entries ...
        - refget/notebooks/fasta-drs-client.py
        - refget/notebooks/pangenome-client.py
```

## Priority Order

1. **High Priority** (organization complete, content cleanup):
   - ~~Step 1: Reorganize mkdocs.yml nav~~ DONE
   - Step 1b: Fix agent.ipynb type mixing
   - Step 2: Create FASTA DRS Client how-to
   - Step 7: Update mkdocs-jupyter plugin config

2. **Medium Priority** (new content):
   - Step 4: Create Architecture overview (Explanation)
   - Step 3: Create Pangenome Client how-to
   - Step 6: Expand Agent documentation

3. **Lower Priority** (reference documentation):
   - Step 5: Processing module documentation

## Code Architecture Summary (for reference)

### Package Structure
```
refget/
├── __init__.py          # Lazy-loaded exports
├── models.py            # SQLModel data models
├── agents.py            # Database agents
├── clients.py           # HTTP clients
├── refget_router.py     # FastAPI router
├── utilities.py         # Seqcol processing
├── digest_functions.py  # Digest wrappers
├── cli/                 # Typer CLI (5 command groups)
└── processing/          # gtars-dependent processing
    ├── digest.py        # Digest re-exports
    ├── fasta.py         # FASTA conversion
    ├── store.py         # RefgetStore re-export
    └── bridge.py        # gtars-to-Python conversion
```

### Key Classes
- **Clients**: `SequenceClient`, `SequenceCollectionClient`, `FastaDrsClient`, `PangenomeClient`
- **Agents**: `RefgetDBAgent`, `SequenceAgent`, `SequenceCollectionAgent`, `FastaDrsAgent`, `PangenomeAgent`
- **Models**: `SequenceCollection`, `FastaDrsObject`, `DrsObject`, `Pangenome`

### Data Flows
1. **FASTA → Database**: `add_from_fasta_file()` → `fasta_to_seqcol_dict()` → `SequenceCollection` → DB
2. **Remote Query**: `Client.get_collection()` → `_try_urls()` → JSON response
3. **RefgetStore**: `RefgetStore.in_memory()`/`on_disk()` → gtars Rust implementation

## Backwards compatibility

This is developmental software. Delete outdated content rather than maintaining parallel docs for old versions.

## Cleanup

Once completed, move this plan to `plans/completed/`.
