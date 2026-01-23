# Refget Documentation Evaluation

**Date:** 2026-01-22
**Documentation path:** `/repos/refgenie-docs/docs/refget`
**Code path:** `/repos/refget`

---

## Executive Summary

The refget documentation has a solid foundation with correct audience-first organization and some excellent content. However, there are significant coverage gaps (no Configuration docs, no REST API reference, undocumented clients) and several notebooks need output capture or structural fixes.

**Recommendation:** Address P1 proposals first, focusing on the seqcol-client.ipynb fixes, Configuration reference page, and REST API reference page.

---

## Current Site Structure

```
- Refget:
    - Getting started: README.md
    - Using refget services:
        - Computing digests: digests.ipynb
        - RefgetStore (local storage): refgetstore.py
        - Python SequenceClient: sequence-client.ipynb
        - Python SequenceCollectionsClient: seqcol-client.ipynb
    - Hosting refget services:
        - RefgetDB Agent: agent.ipynb
        - Adding a FastAPI router: fastapi_router.md
        - Compliance testing: compliance.md
    - Reference:
        - CLI reference: cli.md
        - RefgetStore format: refgetstore-format.md
        - Pydantic models: models.md
        - Python API: reference_docs.md
        - Changelog: changelog.md
    - Explanation:
        - Package components: introduction.md
```

**Pattern:** Audience-first (Using vs Hosting separation)

**Assessment:** Good structure, but "Using" mixes tutorials with how-to content, and several key reference pages are missing.

---

## Page-by-Page Assessment

| Page | Type | Consistent? | Key Issues | Priority |
|------|------|-------------|------------|----------|
| README.md | Landing | Clean | No quickstart, no next steps | High |
| introduction.md | Explanation | Mixed | Misleading header, missing RefgetStore | Medium |
| cli.md | Reference | Clean | Minor: verify commands exist, missing sequence_servers | Low |
| models.md | Reference | Clean | Only covers 1 model (SequenceCollection) | High |
| reference_docs.md | Reference | Clean | Missing FastaDrsClient, PangenomeClient, validators | High |
| refgetstore-format.md | Reference | Clean | Well-written, minor timestamp issue | Low |
| fastapi_router.md | How-to | Clean | Wrong import, missing endpoint list, missing config | High |
| compliance.md | How-to | Clean | Too brief, no troubleshooting | Medium |
| digests.ipynb | How-to | Clean | Minimal, missing output, no context | Medium |
| refgetstore.py | Tutorial | Clean | Comprehensive but missing FAI/chrom-sizes | Low |
| sequence-client.ipynb | Tutorial | Clean | Minimal, broken error example | Medium |
| seqcol-client.ipynb | Tutorial | Mixed | Many cells missing output, localhost URL | High |
| agent.ipynb | Reference | Mixed | Cells out of order, no outputs, sparse | High |

---

## Coverage Analysis

### Well Covered

- RefgetStore local operations (refgetstore.py is excellent)
- FASTA processing concepts
- Basic client usage patterns
- RefgetStore file format specification
- CLI commands (mostly complete)

### Partially Covered

- CLI commands (documented but some may not exist/be outdated)
- SequenceCollectionClient (missing: `compare_local()`, `download_fasta_to_store()`, capability checks)
- Database agents (table listing exists but no working examples)

### Not Covered

- **Configuration system** - No docs for `~/.refget/config.toml` structure, env vars, or `sequence_servers`
- **REST API endpoints** - No reference of actual HTTP endpoints served by seqcolapi
- **FastaDrsClient** - Entire class undocumented
- **PangenomeClient** - Entire class undocumented
- **Validation utilities** - `validate_seqcol()`, `validate_seqcol_bool()` undocumented
- **Comparison functions** - `compare_seqcols()`, `calc_jaccard_similarities()` undocumented in Python API
- **Data model relationships** - No explanation of how models relate
- **Conceptual docs** - What is a seqcol? Coordinate systems? Content addressing?

---

## Detailed Page Reviews

### README.md (Getting started)

**Type:** Landing page
**Issues:**
- Very brief - only covers installation
- Lacks quickstart tutorial or common first tasks
- No "What's Next" section

**Suggested Changes:**
- Add "Quick Start" section with 3-5 common tasks
- Add navigation to tutorials and how-to guides

---

### introduction.md (Explanation > Package components)

**Type:** Explanation
**Issues:**
- Line 8 says "you will find how-to guides" but this IS the explanation page
- Missing RefgetStore as a component
- Ends abruptly

**Suggested Changes:**
- Fix misleading text on line 8
- Add RefgetStore as item 7
- Add links to each component's detailed docs

---

### cli.md (Reference > CLI reference)

**Type:** Reference
**Issues:**
- Some commands may not exist: `store pull`, `fasta rgsi`, `fasta rgci`
- Missing `sequence_servers` from config sections list (line 79)

**Suggested Changes:**
- Verify all documented commands exist in current implementation
- Add `sequence_servers` to config sections list
- Add examples for `remote_stores` and `sequence_servers`

---

### models.md (Reference > Pydantic models)

**Type:** Reference
**Issues:**
- Only documents SequenceCollection - many models missing
- No explanation of model relationships
- Generic page title

**Suggested Changes:**
- Add: FastaDrsObject, DrsObject, AccessMethod, Pangenome, Sequence
- Add model hierarchy introduction
- Group by category (sequence, collection, DRS models)

---

### reference_docs.md (Reference > Python API)

**Type:** Reference
**Issues:**
- Missing FastaDrsClient and PangenomeClient
- Missing validation utilities
- Missing comparison functions

**Suggested Changes:**
- Add FastaDrsClient section
- Add PangenomeClient section
- Add validation utilities section
- Add comparison functions section

---

### refgetstore-format.md (Reference > RefgetStore format)

**Type:** Reference
**Issues:**
- Minor: timestamp in example (2025-01-15)
- "Usage Patterns" section mixes How-to content

**Assessment:** Well-written, comprehensive. Low priority for changes.

---

### fastapi_router.md (Hosting > Adding a FastAPI router)

**Type:** How-to
**Issues:**
- Missing `from fastapi import FastAPI` import
- Line 36: `from refget import seqcol_router` should be `from refget import create_refget_router`
- No list of endpoints added
- No database configuration docs

**Suggested Changes:**
- Fix imports
- Add endpoint list section
- Add router parameters explanation
- Add database config requirements

---

### compliance.md (Hosting > Compliance testing)

**Type:** How-to
**Issues:**
- Very brief
- No explanation of what tests verify
- No troubleshooting guidance

**Suggested Changes:**
- Add intro explaining what compliance testing verifies
- Add prerequisites section
- Add troubleshooting for common failures

---

### digests.ipynb (Using > Computing digests)

**Type:** How-to
**Issues:**
- Only 9 cells with minimal explanation
- No intro explaining what digests are
- Cell-9 output not captured
- No explanation of `SQ.` prefix

**Suggested Changes:**
- Add introduction on GA4GH digests
- Capture all cell outputs
- Explain sequence vs collection digests

---

### refgetstore.py (Using > RefgetStore local storage)

**Type:** Tutorial
**Issues:**
- Comprehensive but long (460+ lines)
- Missing FAI index and chrom.sizes coverage
- Brief CLI section at end

**Assessment:** Excellent tutorial. Consider adding FAI/chrom-sizes section.

---

### sequence-client.ipynb (Using > Python SequenceClient)

**Type:** Tutorial
**Issues:**
- Minimal - only 11 cells
- Error example shows 500 (server bug) instead of expected 404
- No discussion of URL fallback behavior

**Suggested Changes:**
- Fix error example with valid 404 case
- Add URL fallback discussion
- Add practical example with known sequence

---

### seqcol-client.ipynb (Using > Python SequenceCollectionsClient)

**Type:** Tutorial (mixed with reference)
**Issues:**
- Many cells have no captured output (cells 4, 6, 8, 10, 12, 14, 16, 18, 21, 23-26, 28-29, 32, 34, 36)
- Uses localhost URL that readers can't use
- Pydantic models section shifts to reference style

**Suggested Changes:**
- Capture all cell outputs
- Use public server URL (https://seqcolapi.databio.org/)
- Split pydantic models to separate reference page
- Add coverage of `compare_local()`, `download_fasta_to_store()`

---

### agent.ipynb (Hosting > RefgetDB Agent)

**Type:** Reference (attempting tutorial)
**Issues:**
- Cells out of order: code before explanatory markdown
- No outputs captured
- Very sparse (8 cells)
- Sub-agents listed in table but not demonstrated

**Suggested Changes:**
- Fix cell ordering
- Capture all outputs
- Add working example for each sub-agent
- Consider converting to reference page

---

## Prioritized Proposals

### P1 - Critical

| # | Type | Description | Files | Effort |
|---|------|-------------|-------|--------|
| 1 | Content fix | Fix seqcol-client.ipynb: capture outputs, use public server URL | seqcol-client.ipynb | Medium |
| 2 | Content fix | Fix agent.ipynb: reorder cells, capture outputs, add examples | agent.ipynb | Medium |
| 3 | New content | Add Configuration Reference page (config.toml sections, all env vars) | new: configuration.md | Medium |
| 4 | New content | Add REST API Reference page (all endpoints with params/responses) | new: rest-api.md | Large |
| 5 | Page expansion | Expand models.md to cover FastaDrsObject, DrsObject, AccessMethod, Pangenome | models.md | Medium |
| 6 | Page expansion | Add FastaDrsClient and PangenomeClient to reference_docs.md | reference_docs.md | Small |
| 7 | Content fix | Fix fastapi_router.md: correct import, add endpoint list, add config section | fastapi_router.md | Small |

### P2 - Important

| # | Type | Description | Files | Effort |
|---|------|-------------|-------|--------|
| 8 | New content | Add "Quickstart" section to README with 3-5 common tasks | README.md | Small |
| 9 | New content | Add conceptual explanation of sequence collections (what/why) | new: concepts.md | Medium |
| 10 | Content fix | Capture missing outputs in digests.ipynb, add context | digests.ipynb | Small |
| 11 | Page expansion | Add validation utilities and comparison functions to reference_docs.md | reference_docs.md | Small |
| 12 | Content fix | Expand compliance.md with prerequisites, troubleshooting | compliance.md | Small |
| 13 | Content fix | Fix introduction.md: remove misleading text, add RefgetStore | introduction.md | Small |

### P3 - Nice to Have

| # | Type | Description | Files | Effort |
|---|------|-------------|-------|--------|
| 14 | Content fix | Fix sequence-client.ipynb error example, add fallback URL discussion | sequence-client.ipynb | Small |
| 15 | Verify | Verify CLI commands exist: `store pull`, `fasta rgsi`, `fasta rgci` | cli.md | Small |
| 16 | New content | Add how-to for generating FAI/chrom-sizes from RefgetStore | new how-to or refgetstore.py | Small |
| 17 | Nav restructure | Separate "Using" into "Tutorials" and "How-to" | mkdocs.yml | Medium |

---

## Recommended Nav Restructure

```yaml
- Refget:
    - Getting started:
        - Introduction: README.md  # Expanded with quickstart
        - Installation: install.md  # (new or expand README)
    - Concepts:
        - What is a sequence collection?: concepts.md  # (new)
        - Package components: introduction.md
    - Tutorials:
        - Computing digests: notebooks/digests.ipynb
        - Using RefgetStore: notebooks/refgetstore.py
        - Using sequence clients: notebooks/sequence-client.ipynb
        - Using seqcol clients: notebooks/seqcol-client.ipynb
    - How-to Guides:
        - Deploying seqcolapi:
            - Adding a FastAPI router: fastapi_router.md
            - Database agent setup: notebooks/agent.ipynb
            - Compliance testing: compliance.md
    - Reference:
        - CLI reference: cli.md
        - REST API reference: rest-api.md  # (new)
        - Python API: reference_docs.md
        - Data models: models.md
        - Configuration: configuration.md  # (new)
        - RefgetStore format: refgetstore-format.md
        - Changelog: changelog.md
```

---

## Quick Wins

Highest-impact, lowest-effort changes to start immediately:

### 1. Fix fastapi_router.md imports

```python
# Line 9: Add missing import
from fastapi import FastAPI

# Line 36: Fix wrong import
# Change: from refget import seqcol_router
# To: from refget import create_refget_router
```

### 2. Expand README.md quickstart

Add section with common commands:
```bash
# Compute seqcol digest
refget fasta digest genome.fa

# Query a seqcol server
refget seqcol show <digest>

# Initialize local store
refget store init
refget store add genome.fa
```

### 3. Add missing clients to reference_docs.md

Add sections for:
- FastaDrsClient (get_object, get_index, download, etc.)
- PangenomeClient (stub, document current state)

---

## Code Inventory Reference

For convenience, here's what the refget package provides that should be documented:

### CLI Command Groups
- `refget config` - Configuration management (init, show, get, set, add, remove, path, validate)
- `refget fasta` - FASTA processing (index, digest, seqcol, fai, chrom-sizes, stats, validate)
- `refget store` - Local store operations (init, add, list, get, export, seq, fai, chrom-sizes, stats, remove)
- `refget seqcol` - Remote seqcol operations (show, compare, list, search, attribute, info, digest, validate, attributes, schema, servers)
- `refget admin` - Database admin (load, register, ingest, status, info)

### Python Clients
- SequenceClient - GA4GH refget sequences
- SequenceCollectionClient - Seqcol API
- FastaDrsClient - FASTA DRS endpoints
- PangenomeClient - Pangenome API (stub)

### Data Models
- SequenceCollection, FastaDrsObject, DrsObject, AccessMethod, Pangenome, Sequence, and attribute tables

### Configuration
- `~/.refget/config.toml` with sections: store, seqcol_servers, remote_stores, sequence_servers, admin
- Environment variables for all settings

### REST Endpoints (seqcolapi)
- Sequence: GET /sequence/{digest}, GET /sequence/{digest}/metadata
- Collection: GET /collection/{digest}, GET /attribute/collection/{attr}/{digest}
- Comparison: GET /comparison/{d1}/{d2}, POST /comparison/{d1}, POST /similarities
- Listing: GET /list/collection, GET /list/attributes/{attr}
- DRS: GET /fasta/objects/{id}, GET /fasta/objects/{id}/access/{aid}, GET /fasta/objects/{id}/index
