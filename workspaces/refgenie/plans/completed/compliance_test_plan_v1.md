# Compliance Test Plan v1

## Summary

This plan updates `tests/api/test_compliance.py` and `create_compliance_answers.py` to ensure full coverage of the GA4GH Seqcol v1.0.0 specification.

## Current vs Required Coverage

### Current Tests

| Endpoint | Test Method | Notes |
|----------|-------------|-------|
| `GET /collection/:digest` | `test_collection_endpoint` | Tests level 2 only |
| `GET /comparison/:d1/:d2` | `test_comparison_endpoint` | Uses known answer files |
| `GET /attribute/collection/:attr/:digest` | `test_attribute_endpoint` | Only tests `lengths`, `names` |
| `GET /list/collection` | `test_attribute_list_endpoint` | Tests filtering |
| `GET /collection/:digest?level=1` | `test_collections`, `test_sorted_name_length_pairs` | Uses DIGEST_TESTS |

### Missing Test Coverage (per spec)

| Endpoint | Status | Spec Requirement |
|----------|--------|------------------|
| `GET /service-info` | **NOT TESTED** | REQUIRED |
| `POST /comparison/:digest` | **NOT TESTED** | RECOMMENDED |
| Level 1 vs Level 2 representation | Partial | Level 2 should NOT include transient attrs |
| Pagination format (`results` + `pagination`) | **NOT TESTED** | REQUIRED |
| `/attribute` rejection of transient attrs | **NOT TESTED** | REQUIRED |
| `/openapi.json` | **NOT TESTED** | RECOMMENDED |

## Testing Strategy: Known Answers vs Function Calls

### Current Approach

The existing tests use a hybrid approach:
1. **Known answer files** (JSON): `test_api/collection/*.json`, `test_api/comparison/*.json`
2. **Computed at test time**: `fasta_to_digest()` calls to compute expected digests

### Recommended Approach

Use **known correct answers** for all compliance tests because:

1. **Independence**: Tests verify the API server, not the refget library functions
2. **Stability**: Answers don't change if library code has bugs
3. **Clarity**: Failing tests point to server issues, not library issues
4. **Spec compliance**: We can verify responses match spec format exactly

### Implementation

Update `create_compliance_answers.py` to generate complete answer fixtures:

```python
# Generate fixtures for all endpoints:
# 1. /service-info response
# 2. /collection responses (level 1 AND level 2)
# 3. /comparison responses (including POST variant)
# 4. /list/collection responses (with pagination)
# 5. /attribute responses (including expected errors for transient)
```

## Test Cases to Add

### 1. Service Info Endpoint (REQUIRED)

```python
def test_service_info(self, api_root):
    """Test /service-info endpoint returns required fields"""
    response = requests.get(f"{api_root}/service-info")
    assert response.status_code == 200
    data = response.json()

    # Required GA4GH service-info fields
    assert "id" in data
    assert "name" in data
    assert "type" in data
    assert data["type"].get("artifact") == "refget-seqcol"

    # Required seqcol-specific field
    assert "seqcol" in data
    assert "schema" in data["seqcol"]

    # Schema must define inherent attributes
    schema = data["seqcol"]["schema"]
    assert "ga4gh" in schema
    assert "inherent" in schema["ga4gh"]
```

### 2. Collection Level 1 vs Level 2 (REQUIRED)

```python
def test_collection_level1_vs_level2(self, api_root, digest):
    """Test that level 1 returns digests, level 2 returns values"""
    level1 = requests.get(f"{api_root}/collection/{digest}?level=1").json()
    level2 = requests.get(f"{api_root}/collection/{digest}?level=2").json()

    # Level 1 values should be digest strings (32 chars)
    for attr in ["names", "lengths", "sequences"]:
        assert isinstance(level1[attr], str)
        assert len(level1[attr]) == 32  # GA4GH digest length

    # Level 2 values should be arrays
    for attr in ["names", "lengths", "sequences"]:
        assert isinstance(level2[attr], list)
```

### 3. Transient Attributes (REQUIRED)

```python
def test_transient_not_in_level2(self, api_root, digest):
    """Test that transient attributes are NOT present at level 2"""
    level2 = requests.get(f"{api_root}/collection/{digest}?level=2").json()

    # sorted_name_length_pairs is transient, should NOT be at level 2
    assert "sorted_name_length_pairs" not in level2

    # But it SHOULD be at level 1
    level1 = requests.get(f"{api_root}/collection/{digest}?level=1").json()
    assert "sorted_name_length_pairs" in level1

def test_attribute_rejects_transient(self, api_root):
    """Test that /attribute endpoint rejects transient attribute requests"""
    # Get a level 1 digest for sorted_name_length_pairs
    digest = "..."  # from known answers
    response = requests.get(
        f"{api_root}/attribute/collection/sorted_name_length_pairs/{digest}"
    )
    # Should return 404 or 400, not 200
    assert response.status_code in [400, 404]
```

### 4. POST Comparison (RECOMMENDED)

```python
def test_comparison_post(self, api_root, digest, local_collection):
    """Test POST /comparison/:digest with local collection"""
    response = requests.post(
        f"{api_root}/comparison/{digest}",
        json=local_collection
    )
    assert response.status_code == 200
    data = response.json()

    # Must have required keys
    assert "digests" in data
    assert "attributes" in data
    assert "array_elements" in data

    # digests.a is server digest, digests.b may be null (not computed)
    assert data["digests"]["a"] == digest
```

### 5. List Pagination (REQUIRED)

```python
def test_list_pagination_format(self, api_root):
    """Test /list/collection returns proper pagination format"""
    response = requests.get(f"{api_root}/list/collection?page=0&page_size=10")
    assert response.status_code == 200
    data = response.json()

    # Must have results and pagination sections
    assert "results" in data
    assert "pagination" in data
    assert isinstance(data["results"], list)

    # Pagination must have required fields
    assert "page" in data["pagination"]
    assert "page_size" in data["pagination"]
    assert "total" in data["pagination"]

def test_list_filtering(self, api_root, attr_digest):
    """Test /list/collection with attribute filter"""
    response = requests.get(f"{api_root}/list/collection?names={attr_digest}")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
```

### 6. OpenAPI Documentation (RECOMMENDED)

```python
def test_openapi(self, api_root):
    """Test /openapi.json is available"""
    response = requests.get(f"{api_root}/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "paths" in data
```

## Updates to create_compliance_answers.py

Add generation for:

1. **Service info expected response** (validate schema structure)
2. **Level 1 representations** for all demo collections
3. **POST comparison test cases** (store a local collection + expected result)
4. **Pagination response format** (results + pagination)
5. **Transient attribute digests** (for testing rejection)

```python
# Structure of generated fixtures:

test_api/
├── collection/
│   ├── base.fa.level1.json      # NEW: level 1 representation
│   ├── base.fa.level2.json      # existing (renamed)
│   └── ...
├── comparison/
│   ├── compare_base.fa_subset.fa.json
│   └── compare_post_base.json   # NEW: POST comparison fixture
├── list/
│   └── list_all.json            # NEW: expected list format
├── attribute/
│   └── ...
└── service_info_schema.json     # NEW: expected schema structure
```

## Files to Modify

1. **`tests/api/test_compliance.py`**: Add new test methods
2. **`tests/api/conftest.py`**: Add new test fixtures/parameters
3. **`create_compliance_answers.py`**: Generate all required answer files
4. **`tests/conftest.py`**: May need updates for new fixtures

## Implementation Order

1. Update `create_compliance_answers.py` to generate complete fixtures
2. Run the script against a known-good server to generate fixtures
3. Add new test methods to `test_compliance.py`
4. Run tests and verify all pass
5. Commit fixtures as known correct answers
