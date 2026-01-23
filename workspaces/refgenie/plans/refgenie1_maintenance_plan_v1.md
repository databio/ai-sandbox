# Refgenie1 Python Package Maintenance Plan

## Goal

Simplify and modernize the `repos/refgenie1/` Python monorepo without removing features. This is developmental software with no need to maintain backwards compatibility. The goal is to reduce technical debt, eliminate redundant code, consolidate duplicate patterns, and improve maintainability.

**Total baseline: 16,975 lines of Python**

The codebase is relatively well-structured but has significant opportunities for simplification, particularly in the large 3,725-line `refgenie.py` main file and the 927-line `argparser.py`.

## Context Files to Read Before Implementation

1. `packages/refgenie/refgenie/refgenie.py` - Main Refgenie class (3,725 lines) - **PRIMARY TARGET**
2. `packages/refgenie/refgenie/cli/argparser.py` - CLI argument parser (927 lines)
3. `packages/refgenie/refgenie/cli/cli.py` - CLI implementation (540 lines)
4. `packages/refgenie/refgenie/db/models.py` - Database models (721 lines)
5. `packages/refgenie/refgenie/dash/routers/dash.py` - Dashboard routes (770 lines)
6. `packages/refgenie/refgenie/dash/routers/core.py` - Core API routes (495 lines)
7. `packages/refgenie/refgenie/const.py` - Constants (282 lines)
8. `packages/refgenie/refgenie/resource_manager/recipe/manager.py` - Recipe manager (342 lines)
9. `packages/refgenie/refgenie/resource_manager/configuration/manager.py` - Config manager (252 lines)
10. `packages/refgenie/refgenie/server/client.py` - Server client (384 lines)

## Items to Remove Completely

### 1. Remove commented-out code and TODO hacks

**`refgenie.py:1218-1221`** contains a temporary hack:
```python
force_digest: Optional[
    str
] = None,  # TODO: this is just a temporary hack to get around non-matching digest functions (PROD server vs. new refgenie), to be removed
```

And again at line 1246-1248:
```python
digest = (
    force_digest or digest
)  # TODO: remove this line once the digest functions are aligned
```

**Action:** Remove the `force_digest` parameter and related code entirely.

### 2. Remove unreachable code in `set_genome_alias`

**`refgenie.py:1158`** has unreachable code:
```python
with self._database_session as session:
    return session.exec(select(Alias).where(Alias.name == alias_name)).unique().one()
return alias  # This line is never reached
```

**Action:** Delete the unreachable `return alias` line.

### 3. Remove duplicate CLI command constant definitions

**`const.py`** defines many command constants twice - once as a string and once in a dictionary. For example:
```python
DATA_CHANNEL_ADD_CMD = "add"
...
DATA_CHANNEL_SUBPARSER_MESSAGES = {
    DATA_CHANNEL_ADD_CMD: "Add a data channel.",
    ...
}
```

**Action:** Consider using an Enum or dataclass to consolidate command definitions with their help messages.

## Specific Simplifications

### Step 1: Split `refgenie.py` into focused modules (Priority: Critical)

**Current State:** `refgenie.py` is 3,725 lines - the largest file in the codebase. It contains:
- Database session management
- Genome operations
- Alias operations
- Asset operations
- Asset group operations
- Seek key operations
- Build operations
- Pull operations
- Symlink management
- Population/templating
- Table generation

**Action:** Split into focused modules under `packages/refgenie/refgenie/`:

```
refgenie/
├── refgenie.py          # Keep: Core Refgenie class (~500 lines)
├── operations/
│   ├── __init__.py
│   ├── genome.py        # Genome CRUD operations (~300 lines)
│   ├── alias.py         # Alias CRUD operations (~200 lines)
│   ├── asset.py         # Asset CRUD operations (~400 lines)
│   ├── asset_group.py   # Asset group operations (~200 lines)
│   ├── seek_key.py      # Seek key operations (~150 lines)
│   ├── build.py         # Build asset logic (~500 lines)
│   ├── pull.py          # Pull/download logic (~400 lines)
│   └── symlink.py       # Symlink management (~200 lines)
├── display/
│   ├── __init__.py
│   └── tables.py        # All Table generation methods (~400 lines)
```

The main `Refgenie` class would use composition to include these operation handlers.

### Step 2: Consolidate database session pattern (Priority: High)

**Current State:** Nearly every method in `refgenie.py` uses the pattern:
```python
with self._database_session as session:
    statement = select(...)
    result = session.exec(statement)
    ...
```

**Action:** Create a helper method to reduce boilerplate:
```python
def _query_one(self, statement, error_class=None, **error_kwargs):
    """Execute query expecting exactly one result."""
    with self._database_session as session:
        try:
            return session.exec(statement).unique().one()
        except NoResultFound:
            if error_class:
                raise error_class(**error_kwargs)
            raise

def _query_all(self, statement):
    """Execute query returning all results."""
    with self._database_session as session:
        return session.exec(statement).unique().all()

def _query_exists(self, statement) -> bool:
    """Check if any result exists."""
    with self._database_session as session:
        return bool(session.exec(statement).first())
```

This would reduce repetition across 50+ methods.

### Step 3: Refactor CLI argument parser (Priority: Medium)

**Current State:** `argparser.py` is 927 lines with heavily nested subparser creation.

**Action:** Use a declarative approach with dataclasses:
```python
@dataclass
class SubCommand:
    name: str
    help: str
    arguments: List[Argument]
    subcommands: Optional[List['SubCommand']] = None

COMMANDS = [
    SubCommand(
        name=ALIAS_CMD,
        help=SUBPARSER_MESSAGES[ALIAS_CMD],
        arguments=[...],
        subcommands=[
            SubCommand(name=ALIAS_GET_CMD, ...),
            SubCommand(name=ALIAS_SET_CMD, ...),
        ]
    ),
    ...
]
```

Then generate the argparse parser from this declarative structure.

### Step 4: Consolidate similar `*_exists` methods (Priority: Medium)

**Current State:** Multiple nearly identical existence check methods:
- `genome_exists()`
- `alias_exists()`
- `asset_group_exists()`
- `asset_exists()`
- `seek_key_exists()`

All follow the same pattern.

**Action:** Create a generic existence checker:
```python
def _exists(self, model_class, **filters) -> bool:
    statement = select(model_class).where(
        *[getattr(model_class, k) == v for k, v in filters.items()]
    )
    with self._database_session as session:
        return bool(session.exec(statement).first())
```

### Step 5: Consolidate `_resolve_genome_digest` calls (Priority: Low)

**Current State:** `_resolve_genome_digest()` is called at the start of 25+ methods. This is repetitive.

**Action:** Create a decorator:
```python
def resolve_genome(method):
    """Decorator that resolves genome_name to genome_digest."""
    @functools.wraps(method)
    def wrapper(self, *args, genome_name=None, genome_digest=None, **kwargs):
        genome_digest = self._resolve_genome_digest(genome_digest, genome_name)
        return method(self, *args, genome_digest=genome_digest, **kwargs)
    return wrapper
```

### Step 6: Consolidate Table generation (Priority: Low)

**Current State:** Multiple table generation methods scattered throughout:
- `aliases_table()`
- `genomes_table()`
- `assets_table()`
- Resource manager `table()` methods

**Action:** Extract to a dedicated `display/tables.py` module with a consistent interface.

### Step 7: Simplify `const.py` command definitions (Priority: Low)

**Current State:** 283 lines defining command strings and their help messages separately.

**Action:** Use a single data structure:
```python
from enum import Enum, auto
from dataclasses import dataclass

@dataclass
class Command:
    name: str
    help: str
    subcommands: dict = None

class Commands(Enum):
    INIT = Command("init", "Initialize a genome configuration.")
    PURGE = Command("purge", "Purge the genome configuration.")
    # ...
```

This reduces duplication and keeps related data together.

### Step 8: Review and simplify `dash/routers/dash.py` (Priority: Low)

**Current State:** 770 lines of dashboard routing code.

**Action:** Review for:
- Duplicate route patterns
- Complex nested logic that could be extracted
- Unused routes

## Implementation Order

1. **Remove dead code and hacks** - Quick wins, no risk
2. **Create query helper methods** - Foundation for other changes
3. **Split refgenie.py into modules** - Major structural improvement
4. **Consolidate existence checks** - Reduces repetition
5. **Refactor argparser** - Improves maintainability
6. **Consolidate constants** - Polish

## Verification Steps

1. **Run existing tests:**
   ```bash
   cd repos/refgenie1/packages/refgenie
   pytest
   ```
   All tests should pass.

2. **Test CLI commands:**
   ```bash
   refgenie --help
   refgenie init --help
   refgenie build --help
   refgenie alias --help
   refgenie recipe --help
   ```

3. **Test critical workflows:**
   ```bash
   refgenie init
   refgenie subscribe
   refgenie listr
   refgenie pull <genome>/<asset>
   refgenie list
   ```

4. **Compare line counts before/after:**
   ```bash
   find . -path './.venv' -prune -o -name '*.py' -type f -print | xargs wc -l | sort -n
   ```

## Expected Impact

| Item | Lines Affected |
|------|---------------|
| Split refgenie.py | ~3,725 → multiple smaller modules |
| Query helpers | -200 (reduced boilerplate) |
| Existence check consolidation | -80 |
| Dead code removal | -20 |
| Argparser refactor | -200 (declarative) |
| Constants consolidation | -50 |
| **Total reduction** | **~400-600 lines** |

Note: The main benefit is improved maintainability through smaller, focused files rather than raw line count reduction.

## Important Notes

- **DO NOT MAINTAIN BACKWARDS COMPATIBILITY** - This is developmental software. Old patterns should be replaced, not preserved.
- **DO NOT add new features** - This is maintenance only.
- **DO preserve all existing functionality** - Just reorganize it.
- **Focus on `refgenie.py`** - At 3,725 lines, splitting this file is the highest-impact change.

## Summary

After this cleanup:
1. `refgenie.py` will be split into manageable, focused modules
2. Database query patterns will be DRY
3. CLI argument parsing will be declarative and maintainable
4. Constants will be organized with their metadata
5. Overall code will be easier to navigate and understand

## Baseline File Sizes (Lines of Code)

```
     0 ./packages/refgenie/refgenie/cli/__init__.py
     0 ./packages/refgenie/refgenie/dash/__init__.py
     0 ./packages/refgenie/refgenie/dash/models/request/__init__.py
     0 ./packages/refgenie/refgenie/db/__init__.py
     0 ./packages/refgenieserver/refgenieserver/__init__.py
     0 ./packages/refgenie/tests/__init__.py
     3 ./packages/refgenie/refgenie/dash/models/__init__.py
     3 ./packages/refgenie/refgenie/dash/models/response/__init__.py
     3 ./packages/refgenie/refgenie/resource_manager/archive/__init__.py
     3 ./packages/refgenie/refgenie/resource_manager/asset_class/__init__.py
     3 ./packages/refgenie/refgenie/resource_manager/configuration/__init__.py
     3 ./packages/refgenie/refgenie/resource_manager/recipe/__init__.py
     5 ./packages/refgenie/refgenie/__init__.py
    10 ./packages/refgenie/refgenie/dash/__main__.py
    10 ./packages/refgenieserver/refgenieserver/__main__.py
    12 ./packages/refgenie/refgenie/dash/const.py
    13 ./packages/refgenie/refgenie/dash/models/response/core.py
    13 ./packages/refgenie/refgenie/resource_manager/data_channel/__init__.py
    16 ./packages/refgenie/refgenie/dash/models/request/search.py
    17 ./packages/refgenieserver/refgenieserver/models/version4.py
    18 ./packages/refgenie/refgenie/dash/filters.py
    18 ./packages/refgenie/refgenie/dash/templates.py
    19 ./packages/refgenieserver/refgenieserver/stats/dump.py
    21 ./packages/refgenieserver/refgenieserver/const.py
    23 ./packages/refgenie/refgenie/logger.py
    24 ./packages/refgenieserver/refgenieserver/middleware/endpoint_stats.py
    26 ./packages/refgenie/refgenie/utils/templating.py
    27 ./packages/refgenie/refgenie/config/__init__.py
    28 ./packages/refgenieserver/refgenieserver/stats/handlers.py
    29 ./packages/refgenie/refgenie/db/migrations/utils.py
    30 ./packages/refgenie/refgenie/resource_manager/data_channel/local.py
    30 ./packages/refgenieserver/refgenieserver/models/__init__.py
    31 ./packages/refgenie/refgenie/resource_manager/__init__.py
    32 ./packages/refgenie/refgenie/db/migrations/versions/a61aff4935b4_add_index_for_species_name.py
    34 ./packages/refgenieserver/refgenieserver/filters.py
    40 ./packages/refgenie/refgenie/dash/models/response/pagination.py
    47 ./packages/refgenie/refgenie/resource_manager/data_channel/base.py
    53 ./packages/refgenie/refgenie/resource_manager/data_channel/ftp.py
    58 ./packages/refgenie/refgenie/resource_manager/data_channel/http.py
    59 ./packages/refgenieserver/refgenieserver/utils/remote_assets.py
    61 ./packages/refgenieserver/refgenieserver/stats/endpoint_collector.py
    64 ./packages/refgenie/tests/conftest.py
    65 ./packages/refgenie/refgenie/progress_bar.py
    77 ./packages/refgenie/refgenie/utils/encryption.py
    77 ./packages/refgenie/tests/test_database.py
    83 ./packages/refgenie/refgenie/utils/archiving.py
    85 ./packages/refgenie/refgenie/db/migrations/versions/ec860a65330a_add_species_name_to_genome.py
    89 ./packages/refgenie/refgenie/dash/main.py
    93 ./packages/refgenie/refgenie/db/migrations/env.py
    93 ./packages/refgenie/refgenie/utils/pagination.py
   107 ./packages/refgenieserver/refgenieserver/models/ga4gh_drs.py
   109 ./packages/refgenie/tests/test_subscriptions.py
   110 ./packages/refgenie/refgenie/utils/io.py
   111 ./packages/refgenie/refgenie/utils/build.py
   113 ./packages/refgenie/refgenie/server/models.py
   115 ./packages/refgenie/refgenie/snakefile/generate.py
   118 ./packages/refgenie/refgenie/config/db.py
   122 ./packages/refgenieserver/refgenieserver/models/data_channel.py
   131 ./packages/refgenieserver/refgenieserver/routers/data_channel.py
   139 ./packages/refgenie/tests/test_refgenie.py
   147 ./packages/refgenieserver/refgenieserver/main.py
   150 ./packages/refgenie/refgenie/db/events.py
   164 ./packages/refgenie/tests/test_asset_registry_path.py
   164 ./packages/refgenie/tests/test_utilities.py
   172 ./packages/refgenie/refgenie/utils/search.py
   181 ./packages/refgenie/refgenie/exceptions.py
   184 ./packages/refgenie/tests/test_resource_managers.py
   189 ./packages/refgenie/tests/test_configuration.py
   191 ./packages/refgenie/tests/test_archives.py
   199 ./packages/refgenie/tests/test_genome_operations.py
   215 ./packages/refgenie/tests/test_asset_management.py
   222 ./packages/refgenie/refgenie/resource_manager/asset_class/manager.py
   250 ./packages/refgenie/refgenie/resource_manager/archive/manager.py
   252 ./packages/refgenie/refgenie/resource_manager/configuration/manager.py
   268 ./packages/refgenieserver/refgenieserver/routers/ga4gh_drs.py
   282 ./packages/refgenie/refgenie/const.py
   296 ./packages/refgenie/refgenie/resource_manager/data_channel/manager.py
   296 ./packages/refgenieserver/refgenieserver/routers/version4.py
   301 ./packages/refgenie/tests/test_recipes.py
   319 ./packages/refgenie/tests/test_data_channels.py
   326 ./packages/refgenie/tests/test_asset_classes.py
   342 ./packages/refgenie/refgenie/models.py
   342 ./packages/refgenie/refgenie/resource_manager/recipe/manager.py
   352 ./packages/refgenie/tests/test_aliases.py
   365 ./packages/refgenie/refgenie/db/migrations/versions/7764a79c0c32_initial_migration.py
   384 ./packages/refgenie/refgenie/server/client.py
   495 ./packages/refgenie/refgenie/dash/routers/core.py
   521 ./packages/refgenie/tests/test_core_endpoints.py
   540 ./packages/refgenie/refgenie/cli/cli.py
   721 ./packages/refgenie/refgenie/db/models.py
   770 ./packages/refgenie/refgenie/dash/routers/dash.py
   927 ./packages/refgenie/refgenie/cli/argparser.py
  3725 ./packages/refgenie/refgenie/refgenie.py
 16975 total
```
