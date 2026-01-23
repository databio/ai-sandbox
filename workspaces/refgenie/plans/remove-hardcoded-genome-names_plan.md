# Plan: Remove Hardcoded Genome Names from const.py

## Goal
Remove the hardcoded lists of genome names (`HUMANS_SAMPLE_LIST` and `MOUSE_SAMPLES_LIST`) from `refget/const.py` and replace them with a dynamic, database-driven approach that allows species classification to be stored and queried from the database rather than maintained in code.

## Architecture Decision: Where Should This Live?

Based on the codebase structure:

- **`/refget`**: A reusable Python package providing core refget functionality (models, agents, clients, utilities)
- **`/seqcolapi`**: A thin FastAPI wrapper/application layer built on top of the `refget` package

**Decision: Core functionality belongs in `refget`, API-specific logic stays in `seqcolapi`**

### What Goes Where:

**In `refget` package** (reusable core):
- ✅ Database models (`HumanReadableNames` with species field)
- ✅ Database agent methods (query by species)
- ✅ Species management utilities (if broadly useful)
- ✅ Data loaders that populate species metadata

**In `seqcolapi`** (API-specific):
- ✅ Lifespan loader that pre-loads species digests (this is FastAPI-specific optimization)
- ✅ The `_SAMPLE_DIGESTS` cache (API runtime state)
- ❌ ~~Hardcoded lists~~ (being removed entirely)

**Rationale**: The species concept is a fundamental property of genome collections that should be queryable from the database. This makes it part of the data model, not API-specific logic. The pre-loading optimization in `seqcolapi/main.py` can query species dynamically from the database using methods provided by the `refget` package.

## Problem Diagnosis

### Why Are They Hardcoded?
The genome names are hardcoded in `refget/const.py` (lines 60-160) for two main reasons:

1. **Performance Optimization**: During application startup (`seqcolapi/main.py:28-68`), the `lifespan_loader` function pre-loads digests for specific genome collections to optimize the `/similarities/` endpoint. By having a curated list of known genomes, the API can filter similarity comparisons to only relevant genomes instead of comparing against the entire database.

2. **Species Filtering**: The similarity calculation endpoints (`refget_router.py:203-261` and `269-341`) accept a `species` parameter ("human" or "mouse") to filter comparisons. The hardcoded lists define which human-readable genome names belong to each species category.

### Current Usage Pattern
1. **Startup**: `seqcolapi/main.py` imports `HUMANS_SAMPLE_LIST` and `MOUSE_SAMPLES_LIST` (line 14)
2. **Pre-loading**: The lifespan loader queries the database for all genomes matching these names and caches their digests in `_SAMPLE_DIGESTS` dict (lines 40-59)
3. **Filtering**: The similarity endpoints use `_SAMPLE_DIGESTS[species]` to restrict comparisons to pre-loaded genomes (lines 215-230 in refget_router.py)

### Issues with Current Approach
- **Maintenance Burden**: Every new genome assembly requires code changes
- **No Flexibility**: Users cannot add custom species or categorizations
- **Tight Coupling**: Species logic is split between const.py (data) and API code (logic)
- **No Validation**: If genome names in the database don't match the hardcoded lists, the feature silently fails

## Context Files to Review

Before implementing changes, review these files to understand the full context:

1. `/home/nsheff/sandbox/refgenie/refget/refget/const.py` - Current hardcoded lists (lines 60-160)
2. `/home/nsheff/sandbox/refgenie/refget/refget/models.py` - Database models, especially `HumanReadableNames` (line 239) and `SequenceCollection` (line 253)
3. `/home/nsheff/sandbox/refgenie/refget/seqcolapi/main.py` - Lifespan loader that pre-loads digests (lines 28-68)
4. `/home/nsheff/sandbox/refgenie/refget/refget/refget_router.py` - Similarity endpoints that use species filtering (lines 203-341)
5. `/home/nsheff/sandbox/refgenie/refget/refget/agents.py` - Database agent methods (need to verify query capabilities)
6. `/home/nsheff/sandbox/refgenie/refget/data_loaders/load_demo_seqcols.py` - Example of how data is loaded

## Implementation Steps

### 1. Add Species Field to Database Models

**File**: `refget/models.py`

- Add a `species` field to the `HumanReadableNames` model (around line 245):
  ```python
  species: Optional[str] = Field(default=None, index=True)
  ```
- Update the `from_dict` method in `SequenceCollection` class (around line 432-446) to accept and propagate species information
- Create database migration script to add the species column to existing tables

### 2. Create Species Management Module

**New File**: `refget/species.py`

- Create functions to:
  - Query available species from database: `get_available_species() -> List[str]`
  - Query genomes by species: `get_genomes_by_species(species: str) -> List[str]`
  - Add/update species metadata: `set_genome_species(human_readable_name: str, species: str)`
- Add validation to ensure species names are consistent (e.g., lowercase, no special chars)

### 3. Update Database Agent

**File**: `refget/agents.py`

- Add method to query digests by species dynamically:
  ```python
  def get_digests_by_species(self, species: str) -> List[str]
  ```
- This should replace the hardcoded list lookup with a database query
- Add caching mechanism if needed for performance

### 4. Update Lifespan Loader

**File**: `seqcolapi/main.py`

- Remove import of `HUMANS_SAMPLE_LIST` and `MOUSE_SAMPLES_LIST` (line 14)
- Modify `lifespan_loader` function (lines 28-68):
  - Query database for all available species: `dbagent.get_available_species()`
  - For each species, query digests: `dbagent.get_digests_by_species(species)`
  - Populate `_SAMPLE_DIGESTS` dynamically from database instead of hardcoded lists
- Add logging to show which species were loaded and how many genomes per species

### 5. Update API Router

**File**: `refget/refget_router.py`

- No major changes needed since it already uses `_SAMPLE_DIGESTS` dict
- Improve error messaging in validation (lines 215-218, 294-298) to list dynamically available species
- Consider adding a GET endpoint to list available species: `/list/species`

### 6. Create Data Migration Tool

**New File**: `data_loaders/migrate_species_metadata.py`

- Read the current `HUMANS_SAMPLE_LIST` and `MOUSE_SAMPLES_LIST` from const.py
- For each name in the lists, update the corresponding `HumanReadableNames` record in the database to set species="human" or species="mouse"
- Handle cases where names don't exist in database (log warnings)
- This is a one-time migration script to populate initial species data

### 7. Update Data Loaders

**File**: `data_loaders/load_demo_seqcols.py` and other loaders

- Add optional `species` parameter to `add_from_fasta_file_with_name` calls
- Example:
  ```python
  dbc.seqcol.add_from_fasta_file_with_name(
      f, human_readable_name=name, species="human", update=True
  )
  ```

### 8. Remove Hardcoded Lists

**File**: `refget/const.py`

- Delete `HUMANS_SAMPLE_LIST` (lines 60-121)
- Delete `MOUSE_SAMPLES_LIST` (lines 123-160)
- Add deprecation comment if needed for reference

### 9. Update Tests

**Files**: Test files (need to identify which test files exist)

- Update any tests that reference the hardcoded lists
- Add new tests for species management functions
- Test dynamic species loading in lifespan loader
- Test similarity filtering with database-backed species

### 10. Update Documentation

**Files**: README.md and any API documentation

- Document the new species field in data model
- Explain how to set species when loading new genomes
- Document the migration script for existing deployments
- Add examples of querying by species

## Final Summary

After implementation:
- **Before**: ~100 lines of hardcoded genome names in const.py
- **After**: 0 hardcoded names, replaced with ~100-150 lines of species management code across multiple files
- **Benefits**:
  - Dynamic species management without code changes
  - Better separation of concerns (data in DB, not code)
  - Extensible to new species without deployment
  - Consistent with database-driven architecture
- **Migration Path**: One-time migration script to populate species field for existing data

## Important Notes

**DO NOT MAINTAIN BACKWARDS COMPATIBILITY**. This is developmental software. We are eliminating the hardcoded lists entirely, not keeping them as fallbacks. Any code that references `HUMANS_SAMPLE_LIST` or `MOUSE_SAMPLES_LIST` should be updated or removed. If external systems depend on these constants, they will need to be updated to use the new API or database queries.

**Database Schema Change**: This plan requires a database schema migration. Ensure proper backup and migration testing before deploying to production.

**Performance Consideration**: The pre-loading mechanism in lifespan loader is maintained but now loads from database queries instead of hardcoded lists. If performance degrades, consider adding database indexes on the species field or implementing more sophisticated caching.
