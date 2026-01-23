# Refget Client Integration Tests Plan

## Goal

Convert the existing `tests/local/test_refget_clients.py` tests that require a running server (currently skipped) into proper integration tests using the smoketest pattern. This will allow testing the `SequenceCollectionClient`, `FastaDrsClient`, and related client functionality against an ephemeral PostgreSQL database using FastAPI's TestClient.

## Current State

The existing client tests (`test_refget_clients.py`) are marked with `@pytest.mark.require_service` and check if a real server is running at `--api_root` (default `http://0.0.0.0:8100`). When no server is running, these 4 tests are skipped.

**Current test structure:**
- `tests/conftest.py` - Defines `require_service` marker and `api_root` fixture
- `tests/local/test_refget_clients.py` - Uses `requests` to hit a real server
- Uses hardcoded digest `XZlrcEGi6mlopZ2uD8ObHkQB1d0oDwKk` from `test_fasta/base.fa`

**Problems with current approach:**
1. Tests require manually starting a server + database
2. Tests use HTTP requests to real server instead of TestClient
3. No isolation - tests depend on external state
4. Skipped during normal CI runs

## Files to Read for Context

1. `refget/clients.py` - Client classes to test
2. `refget/refget_router.py` - FastAPI router endpoints
3. `refget/agents.py` - Database agent pattern (RefgetDBAgent)
4. `seqcolapi/main.py` - App setup and lifespan
5. `tests/conftest.py` - Existing test fixtures
6. `test_fasta/test_fasta_digests.json` - Known digests for test data
7. `/home/nsheff/Dropbox/workspaces/.claude/skills/smoketest-writing/SKILL.md` - Smoketest pattern reference

## Implementation Steps

### Step 1: Create test database script

Create `tests/integration/scripts/test-db.sh`:
- Use PostgreSQL 17 in Docker
- Port 5433 (not 5432) to avoid dev DB conflicts
- Use `--tmpfs` for fast ephemeral data
- Container name: `refget-postgres-test`

### Step 2: Create integration conftest.py

Create `tests/integration/conftest.py`:

```python
"""
Integration test fixtures for refget client testing.

Uses FastAPI TestClient with ephemeral Docker PostgreSQL.
Prerequisites:
1. Start test database: ./tests/integration/scripts/test-db.sh start
2. Run tests: RUN_INTEGRATION_TESTS=true pytest tests/integration/
"""
import os
import pytest
from pathlib import Path

from fastapi.testclient import TestClient

# Skip all integration tests unless explicitly enabled
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "true",
    reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=true to run."
)

# Test database configuration
TEST_DB_URL = "postgresql://testuser:testpass@localhost:5433/refget_test"

@pytest.fixture(scope="session")
def test_fasta_path():
    """Path to test FASTA files"""
    return Path(__file__).parent.parent.parent / "test_fasta"

@pytest.fixture(scope="session")
def test_dbagent():
    """Create RefgetDBAgent connected to test PostgreSQL"""
    from refget.agents import RefgetDBAgent

    dbagent = RefgetDBAgent(postgres_str=TEST_DB_URL)
    yield dbagent
    if hasattr(dbagent, 'engine'):
        dbagent.engine.dispose()

@pytest.fixture(scope="session")
def loaded_dbagent(test_dbagent, test_fasta_path):
    """DBAgent pre-loaded with test FASTA files"""
    # Load test FASTA files
    for fa_file in ["base.fa", "different_names.fa", "different_order.fa"]:
        fa_path = test_fasta_path / fa_file
        test_dbagent.seqcol.add_from_fasta_file(str(fa_path))
    return test_dbagent

@pytest.fixture(scope="session")
def client(loaded_dbagent):
    """Create TestClient with test database"""
    from seqcolapi.main import app
    from refget.refget_router import get_dbagent

    def override_get_dbagent():
        return loaded_dbagent

    app.dependency_overrides[get_dbagent] = override_get_dbagent
    app.state.dbagent = loaded_dbagent

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
```

### Step 3: Create integration test file

Create `tests/integration/test_seqcolapi_client.py`:

**Test classes to implement:**

1. **TestServiceAvailability**
   - `test_root_endpoint` - GET / returns 200
   - `test_service_info` - GET /service-info returns valid response

2. **TestSequenceCollectionEndpoints**
   - `test_get_collection` - GET /collection/{digest} returns collection
   - `test_get_collection_level1` - GET /collection/{digest}?level=1
   - `test_get_collection_not_found` - GET /collection/{invalid} returns 404
   - `test_list_collections` - GET /list/collection returns paginated results
   - `test_list_attributes` - GET /list/attributes/{attribute}

3. **TestComparisonEndpoints**
   - `test_compare_two_collections` - GET /comparison/{d1}/{d2}
   - `test_compare_with_local` - POST /comparison/{d1} with body

4. **TestFastaDrsEndpoints** (if fasta_drs=True)
   - `test_drs_service_info` - GET /fasta/service-info
   - `test_get_drs_object` - GET /fasta/objects/{id}
   - `test_get_fasta_index` - GET /fasta/objects/{id}/index

5. **TestSequenceCollectionClient**
   - `test_client_get_collection` - Test client wrapper
   - `test_client_list_collections`
   - `test_client_compare`
   - `test_client_build_chrom_sizes`

6. **TestFastaDrsClient**
   - `test_fasta_client_get_object`
   - `test_fasta_client_get_index`
   - `test_fasta_client_build_fai`

### Step 4: Create test runner script

Create `scripts/test-integration.sh`:

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

echo "=== Integration Tests ==="

# Start test database
echo "Starting test database..."
$PROJECT_ROOT/tests/integration/scripts/test-db.sh start

# Run integration tests
echo "Running integration tests..."
cd $PROJECT_ROOT
RUN_INTEGRATION_TESTS=true pytest tests/integration/ -v
TEST_EXIT_CODE=$?

# Stop test database
echo "Stopping test database..."
$PROJECT_ROOT/tests/integration/scripts/test-db.sh stop

echo "=== Integration tests complete ==="
exit $TEST_EXIT_CODE
```

### Step 5: Delete old server-dependent tests

Remove the `@pytest.mark.require_service` tests from `tests/local/test_refget_clients.py` and keep only the unit tests that don't require a server (like `TestEmptyConstructor`).

### Step 6: Update conftest.py

Remove or simplify the server-checking logic in `tests/conftest.py`:
- Remove `check_server_is_running()` function
- Remove `api_root` fixture (no longer needed)
- Remove `require_service` marker registration

## Test Data Strategy

Use the existing `test_fasta/` files with known digests from `test_fasta_digests.json`:

| File | Digest |
|------|--------|
| base.fa | XZlrcEGi6mlopZ2uD8ObHkQB1d0oDwKk |
| different_names.fa | QvT5tAQ0B8Vkxd-qFftlzEk2QyfPtgOv |
| different_order.fa | Tpdsg75D4GKCGEHtIiDSL9Zx-DSuX5V8 |

This provides:
- Known digests for assertions
- Multiple collections for comparison tests
- Same sequences with different names/orders for comparison validation

## Summary

**Before:**
- 4 tests skipped (require running server)
- Manual server setup required
- No CI integration possible

**After:**
- ~15-20 comprehensive integration tests
- Ephemeral Docker PostgreSQL
- TestClient (no network)
- Gated by `RUN_INTEGRATION_TESTS=true`
- CI-friendly with `scripts/test-integration.sh`

## Important Note

**DO NOT MAINTAIN BACKWARDS COMPATIBILITY.** This is developmental software. Delete the old `@pytest.mark.require_service` tests entirely rather than keeping them alongside the new integration tests. The new TestClient-based approach is superior and the old approach should be removed.
