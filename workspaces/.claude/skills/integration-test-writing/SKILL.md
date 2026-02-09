---
name: integration-test-writing
description: Write parallel-safe integration tests for web backends using ephemeral Docker databases. Language-agnostic patterns for services.sh, test-integration.sh, and directory structure work across Python/FastAPI and Node.js/Express projects. Use when adding integration tests to any backend project.
---

# Integration Test Writing Guide

Write isolated, parallel-safe integration tests for web backends using ephemeral Docker databases.

## Test Scopes

| Scope | What it tests | Dependencies | Speed |
|-------|---------------|--------------|-------|
| **Unit** | Single function/class in isolation | Mocked | Fast |
| **Component** | Module with internal parts wired together | External deps mocked | Fast |
| **Integration** | Multiple components with real dependencies | Real DB, APIs | Slower |
| **End-to-end (E2E)** | Entire system as user experiences it | Everything real | Slowest |

**Smoke test** is orthogonal to scope—it's a *purpose*, not a level. A smoke test asks "does anything work at all?" as a quick sanity check before deeper testing. You can have smoke tests at any scope.

## Core Principles (All Languages)

1. **True isolation** - Tests use a temporary Docker database container, not dev database
2. **Parallel-safe** - Dynamic ports and unique container names allow simultaneous test runs
3. **Ephemeral data** - Database is created fresh, destroyed after tests
4. **Environment gating** - Skip tests unless `RUN_INTEGRATION_TESTS=true`
5. **Vanilla Docker** - Use plain `docker run` commands, NOT docker-compose
6. **Consistent structure** - Same internal organization regardless of language

## Directory Structure

The test root location follows language conventions, but the **internal structure is consistent**:

```
<test-root>/                      # Language-specific location
├── scripts/
│   ├── test-integration.sh       # One-command test runner (ALWAYS HERE)
│   └── services.sh               # Service management (parallel-safe)
├── integration/
│   ├── conftest.py / setup.js    # Integration fixtures
│   └── test_*.py / *.spec.js     # Integration tests
├── fixtures/                     # Test data (SQL, CSV, JSON)
└── helpers/                      # Shared test utilities
```

**Test root by language:**
- Python: `tests/`
- Node.js/Vitest: `src/__tests__/`
- Node.js/Jest: `__tests__/` or `tests/`

**The key invariant:** Integration tests are always run via `<test-root>/scripts/test-integration.sh`

## Parallel-Safety Techniques

To allow multiple test runs simultaneously without conflicts:

### 1. Dynamic Port Allocation
```bash
DB_PORT="${MYAPP_TEST_DB_PORT:-$(( 5433 + (RANDOM % 1000) ))}"
```

### 2. Unique Container Names
```bash
RUN_ID="${MYAPP_TEST_RUN_ID:-$$}"  # Use PID as default
CONTAINER_NAME="${MYAPP_TEST_CONTAINER:-myapp-db-test-${RUN_ID}}"
```

**Naming convention:** `<project>-<db>-test-<run_id>`
- Prefix with project name to identify orphaned containers
- Suffix with run ID (PID) for parallel isolation
- Allow override via `<PROJECT>_TEST_CONTAINER` env var

### 3. Environment Variable Configuration
```bash
export MYAPP_TEST_DB_PORT="$DB_PORT"
export MYAPP_TEST_CONTAINER="$CONTAINER_NAME"
```

### 4. Cleanup Trap Handlers
```bash
cleanup() {
    docker rm -f "$CONTAINER_NAME" 2>/dev/null
}
trap cleanup EXIT INT TERM
```

## Step 1: Create services.sh Script

Manages test services (database, etc.). Use plain `docker run` - no docker-compose.

Create `<test-root>/scripts/services.sh`:

```bash
#!/bin/bash
# Test Services Management Script
# Manages services required for integration tests
#
# Usage:
#   ./scripts/services.sh start   # Start all services
#   ./scripts/services.sh stop    # Stop all services
#   ./scripts/services.sh status  # Show service status

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Replace MYAPP with your project name (e.g., MNEXUS, ESHEFF)
RUN_ID="${MYAPP_TEST_RUN_ID:-$$}"
CONTAINER_NAME="${MYAPP_TEST_CONTAINER:-myapp-db-test-${RUN_ID}}"
DB_PORT="${MYAPP_TEST_DB_PORT:-$(( 5433 + (RANDOM % 1000) ))}"

DB_USER="testuser"
DB_PASS="testpass"
DB_NAME="myapp_test"

# Export for child processes
export MYAPP_TEST_RUN_ID="$RUN_ID"
export MYAPP_TEST_CONTAINER="$CONTAINER_NAME"
export MYAPP_TEST_DB_PORT="$DB_PORT"

# === PostgreSQL version ===
start_postgres() {
    echo "Starting PostgreSQL..."
    echo "  Container: $CONTAINER_NAME"
    echo "  Port: $DB_PORT"

    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

    docker run -d \
        --name "$CONTAINER_NAME" \
        -e POSTGRES_USER="$DB_USER" \
        -e POSTGRES_PASSWORD="$DB_PASS" \
        -e POSTGRES_DB="$DB_NAME" \
        -p "${DB_PORT}:5432" \
        --tmpfs /var/lib/postgresql/data \
        postgres:17

    echo "Waiting for PostgreSQL..."
    for i in {1..30}; do
        if docker exec "$CONTAINER_NAME" pg_isready -U "$DB_USER" -d "$DB_NAME" 2>/dev/null; then
            echo "PostgreSQL is ready!"
            return 0
        fi
        sleep 1
    done
    echo "Failed to start PostgreSQL"
    docker logs "$CONTAINER_NAME"
    return 1
}

# === MySQL version ===
start_mysql() {
    echo "Starting MySQL..."
    echo "  Container: $CONTAINER_NAME"
    echo "  Port: $DB_PORT"

    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

    docker run -d \
        --name "$CONTAINER_NAME" \
        -e MYSQL_ROOT_PASSWORD="$DB_PASS" \
        -e MYSQL_DATABASE="$DB_NAME" \
        -e MYSQL_USER="$DB_USER" \
        -e MYSQL_PASSWORD="$DB_PASS" \
        -p "${DB_PORT}:3306" \
        --tmpfs /var/lib/mysql \
        --health-cmd="mysqladmin ping -h localhost -u $DB_USER -p$DB_PASS" \
        --health-interval=5s \
        --health-timeout=5s \
        --health-retries=10 \
        mysql:8.0

    echo "Waiting for MySQL..."
    for i in {1..60}; do
        STATUS=$(docker inspect --format="{{.State.Health.Status}}" "$CONTAINER_NAME" 2>/dev/null || echo "starting")
        if [ "$STATUS" = "healthy" ]; then
            echo "MySQL is ready!"
            return 0
        fi
        sleep 1
    done
    echo "Failed to start MySQL"
    docker logs "$CONTAINER_NAME" 2>&1 | tail -20
    return 1
}

stop_db() {
    echo "Stopping database ($CONTAINER_NAME)..."
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
}

case "$1" in
    start)
        echo "=== Starting Test Services (Run ID: $RUN_ID) ==="
        start_postgres  # or start_mysql
        echo ""
        echo "To use manually:"
        echo "  export MYAPP_TEST_DB_PORT=$DB_PORT"
        echo "  export MYAPP_TEST_CONTAINER=$CONTAINER_NAME"
        ;;
    stop)
        echo "=== Stopping Test Services ==="
        stop_db
        ;;
    restart)
        echo "=== Restarting Test Services ==="
        stop_db
        start_postgres  # or start_mysql
        ;;
    status)
        echo "=== Test Services Status (Run ID: $RUN_ID) ==="
        docker ps -f "name=$CONTAINER_NAME" --format "DB: {{.Names}} | {{.Ports}} | {{.Status}}" 2>/dev/null || echo "DB: Not running"
        ;;
    logs)
        docker logs -f "$CONTAINER_NAME"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Environment variables for parallel execution:"
        echo "  MYAPP_TEST_RUN_ID    - Unique identifier (default: PID)"
        echo "  MYAPP_TEST_DB_PORT   - Database port (default: 5433 + random)"
        echo "  MYAPP_TEST_CONTAINER - Container name (default: myapp-db-test-\$RUN_ID)"
        exit 1
        ;;
esac
```

**Key points:**
- Dynamic port avoids conflicts with dev DB and parallel runs
- Unique container name identifies orphaned containers
- Use `--tmpfs` for database data directory (fast, ephemeral)
- Replace `myapp`/`MYAPP` with your project name
- Choose `start_postgres` or `start_mysql` based on your stack

Make executable:
```bash
chmod +x <test-root>/scripts/services.sh
```

## Step 2: Create test-integration.sh Script

Create `<test-root>/scripts/test-integration.sh`:

```bash
#!/bin/bash
# Integration Test Runner
# Handles Docker setup, test execution, and cleanup automatically.
# Supports parallel execution - each run gets unique ports and containers.
#
# Usage: ./scripts/test-integration.sh [test args]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/../.."  # Adjust based on your structure
cd "$PROJECT_ROOT"

SERVICES_SCRIPT="$SCRIPT_DIR/services.sh"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Generate unique identifiers for this run (parallel-safety)
export MYAPP_TEST_RUN_ID="$$"
export MYAPP_TEST_DB_PORT=$(( 5433 + (RANDOM % 1000) ))
export MYAPP_TEST_CONTAINER="myapp-db-test-${MYAPP_TEST_RUN_ID}"

SERVICES_STARTED=false

cleanup() {
    local exit_code=$?
    if [ "$SERVICES_STARTED" = true ]; then
        echo -e "\n${YELLOW}Cleaning up...${NC}"
        "$SERVICES_SCRIPT" stop
    fi
    exit $exit_code
}
trap cleanup EXIT INT TERM

echo -e "${GREEN}=== Integration Tests (Run ID: $MYAPP_TEST_RUN_ID) ===${NC}"

echo -e "${GREEN}Starting test database...${NC}"
"$SERVICES_SCRIPT" start
SERVICES_STARTED=true

# Export for tests
export RUN_INTEGRATION_TESTS=true

echo -e "\n${GREEN}Running integration tests...${NC}"

# === Python/pytest version ===
python3 -m pytest tests/integration/ -v "$@"

# === Node.js/Vitest version ===
# npm test -- --no-file-parallelism src/__tests__/integration/ "$@"

# === Node.js/Jest version ===
# npm test -- --runInBand tests/integration/ "$@"

echo -e "\n${GREEN}Integration tests completed successfully!${NC}"
```

Make executable:
```bash
chmod +x <test-root>/scripts/test-integration.sh
```

---

# Python/FastAPI Section

## Test Database Configuration

Create `tests/integration/conftest.py`:

```python
"""Integration test fixtures for FastAPI backend."""
import os
import pytest
from fastapi.testclient import TestClient

# Skip all integration tests unless explicitly enabled
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "true",
    reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=true to run."
)

# Read from environment for parallel-safety
TEST_DB_URL = os.getenv(
    "TEST_DB_URL",
    f"postgresql://testuser:testpass@localhost:{os.getenv('MYAPP_TEST_DB_PORT', '5433')}/myapp_test"
)


@pytest.fixture(scope="session")
def test_engine():
    """Create engine connected to test PostgreSQL"""
    from sqlmodel import create_engine, SQLModel

    engine = create_engine(TEST_DB_URL)
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def client(test_engine):
    """Create TestClient with test database"""
    from backend.main import app
    from backend.database import get_session
    from sqlmodel import Session

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
```

## Writing Python Integration Tests

Create `tests/integration/test_api.py`:

```python
"""API integration tests."""
import os
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "true",
    reason="Integration tests disabled."
)


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
```

---

# Node.js/Express Section

## Test Database Configuration

Create `src/__tests__/helpers/db-setup.js`:

```javascript
/**
 * Test database setup for integration tests.
 * Reads port from environment for parallel-safety.
 */

export const TEST_DB_CONFIG = {
    host: process.env.MYAPP_TEST_DB_HOST || 'localhost',
    port: parseInt(process.env.MYAPP_TEST_DB_PORT, 10) || 5433,
    user: process.env.MYAPP_TEST_DB_USER || 'testuser',
    password: process.env.MYAPP_TEST_DB_PASS || 'testpass',
    database: process.env.MYAPP_TEST_DB_NAME || 'myapp_test'
};

export async function setupTestDatabase() {
    // Create connection, load schema, load fixtures
    // Return connection pool and test metadata
}

export async function teardownTestDatabase(pool) {
    // Clean up and close connection
}
```

## Writing Node.js Integration Tests (Vitest)

Create `src/__tests__/integration/api.spec.js`:

```javascript
/**
 * API integration tests.
 * Skip unless RUN_INTEGRATION_TESTS=true
 */
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { setupTestDatabase, teardownTestDatabase } from '../helpers/db-setup.js';

const shouldSkip = process.env.RUN_INTEGRATION_TESTS !== 'true';

describe.skipIf(shouldSkip)('API Integration', () => {
    let pool;

    beforeAll(async () => {
        const setup = await setupTestDatabase();
        pool = setup.pool;
    }, 30000);

    afterAll(async () => {
        await teardownTestDatabase(pool);
    });

    it('should return health status', async () => {
        // Test implementation
    });
});
```

**Important for Vitest:** Use `--no-file-parallelism` when running integration tests to avoid database conflicts:
```bash
npm test -- --no-file-parallelism src/__tests__/integration/
```

---

## Running Tests

### Full test run (recommended):
```bash
./scripts/test-integration.sh
```

### Run specific tests:
```bash
# Python
./scripts/test-integration.sh -k "test_health"

# Node.js
./scripts/test-integration.sh api-results-stats
```

### Parallel execution (multiple terminals):
```bash
# Terminal 1
./scripts/test-integration.sh -k "test_health"

# Terminal 2 (simultaneously - no conflicts!)
./scripts/test-integration.sh -k "test_crud"
```

### Manual service control (for debugging):
```bash
./scripts/services.sh start
RUN_INTEGRATION_TESTS=true pytest tests/integration/  # or npm test
./scripts/services.sh stop
```

## Checklist for New Integration Tests

- [ ] `<test-root>/scripts/services.sh` with dynamic ports and unique container names
- [ ] `<test-root>/scripts/test-integration.sh` with cleanup trap handlers
- [ ] `<test-root>/integration/` directory for integration test files
- [ ] Test files check `RUN_INTEGRATION_TESTS` environment variable
- [ ] Database config reads port from environment for parallel-safety
- [ ] Tests run sequentially (shared database state)
