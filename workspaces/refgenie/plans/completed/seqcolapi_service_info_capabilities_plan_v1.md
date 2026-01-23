# Implementation plan for advertising fasta_drs and refget_store capabilities via service-info

## The issue

The seqcolapi service currently has a `/service-info` endpoint that returns GA4GH-compliant service metadata, including a `seqcol` object with `schema` and `sorted_name_length_pairs` fields. However, there is no way for clients to discover:

1. Whether the server has FastaDRS endpoints enabled (`fasta_drs`)
2. Whether the server is backed by a RefgetStore and its URL (`refget_store`)

Following the GA4GH service-info specification pattern, we should advertise these capabilities under the `seqcol` object so clients can discover available features programmatically.

## Files to read for context

- `repos/refget/seqcolapi/main.py` - Contains the `/service-info` endpoint and router configuration
- `repos/refget/refget/refget_router.py` - Contains `create_refget_router()` with `fasta_drs` flag

## Current State

The current `/service-info` endpoint returns:

```python
{
    "id": "org.databio.seqcolapi",
    "name": "Sequence collections",
    "type": {"group": "org.ga4gh", "artifact": "refget-seqcol", "version": "1.0.0"},
    ...
    "seqcol": {
        "schema": dbagent.schema_dict,
        "sorted_name_length_pairs": True
    }
}
```

The `fasta_drs=True` flag is already passed to the router constructor in `main.py` line 89:
```python
refget_router = create_refget_router(sequences=False, pangenomes=False, fasta_drs=True)
```

## Target State

The `/service-info` endpoint should return:

```python
{
    ...
    "seqcol": {
        "schema": dbagent.schema_dict,
        "sorted_name_length_pairs": True,
        "fasta_drs": {
            "enabled": True  # or False
        },
        "refget_store": {
            "enabled": True,  # or False
            "url": "s3://bucket/store/"  # only if enabled
        }
    }
}
```

## Implementation Steps

### Step 1: Add refget_store_url parameter to create_refget_router

In `refget/refget_router.py`, add a new parameter:

```python
def create_refget_router(
    sequences: bool = True,
    pangenomes: bool = False,
    fasta_drs: bool = False,
    refget_store_url: str = None,  # NEW
) -> APIRouter:
    ...
```

Store these values so they can be accessed by service-info. One approach is to store them on the router or in a module-level config dict:

```python
# At module level
_ROUTER_CONFIG = {}

def create_refget_router(..., refget_store_url: str = None):
    _ROUTER_CONFIG["fasta_drs"] = fasta_drs
    _ROUTER_CONFIG["refget_store_url"] = refget_store_url
    ...
```

### Step 2: Update seqcolapi/main.py to pass refget_store_url

```python
# Configuration at top of file
REFGET_STORE_URL = "s3://my-bucket/store/"  # Or None if not configured

refget_router = create_refget_router(
    sequences=False,
    pangenomes=False,
    fasta_drs=True,
    refget_store_url=REFGET_STORE_URL
)
```

### Step 3: Update service_info endpoint to use router config

In `seqcolapi/main.py`, update the `service_info()` function:

```python
from refget.refget_router import _ROUTER_CONFIG  # or however config is exposed

@app.get("/service-info", summary="GA4GH service info", tags=["General endpoints"])
async def service_info():
    # Build seqcol capabilities object
    seqcol_info = {
        "schema": dbagent.schema_dict,
        "sorted_name_length_pairs": True,
        "fasta_drs": {
            "enabled": _ROUTER_CONFIG.get("fasta_drs", False)
        },
    }

    # Add refget_store info
    store_url = _ROUTER_CONFIG.get("refget_store_url")
    if store_url:
        seqcol_info["refget_store"] = {
            "enabled": True,
            "url": store_url
        }
    else:
        seqcol_info["refget_store"] = {
            "enabled": False
        }

    ret = {
        "id": "org.databio.seqcolapi",
        "name": "Sequence collections",
        "type": {
            "group": "org.ga4gh",
            "artifact": "refget-seqcol",
            "version": ALL_VERSIONS["seqcol_spec_version"],
        },
        "description": "An API providing metadata such as names, lengths, and other values for collections of reference sequences",
        "organization": {"name": "Databio Lab", "url": "https://databio.org"},
        "contactUrl": "https://github.com/refgenie/refget/issues",
        "documentationUrl": "https://seqcolapi.databio.org",
        "updatedAt": "2025-02-20T00:00:00Z",
        "environment": "dev",
        "version": ALL_VERSIONS,
        "seqcol": seqcol_info,
    }
    return JSONResponse(content=ret)
```

### Step 4: Update client library to use discovery

In `refget/clients.py`, add capability discovery methods to `SequenceCollectionClient`:

```python
class SequenceCollectionClient(RefgetClient):
    # ... existing methods ...

    def is_fasta_drs_enabled(self) -> bool:
        """Check if FastaDRS endpoints are available."""
        info = self.service_info()
        return info.get("seqcol", {}).get("fasta_drs", {}).get("enabled", False)

    def get_refget_store_url(self) -> Optional[str]:
        """Discover RefgetStore URL from service-info if available."""
        info = self.service_info()
        store_config = info.get("seqcol", {}).get("refget_store", {})
        if store_config.get("enabled"):
            return store_config.get("url")
        return None

    def get_refget_store(self, cache_dir: str) -> "RefgetStore":
        """
        Get a RefgetStore instance connected to the server's backing store.

        Args:
            cache_dir: Local directory for caching store data

        Returns:
            RefgetStore instance loaded from remote

        Raises:
            ValueError: If server doesn't have a RefgetStore configured
            ImportError: If gtars is not installed
        """
        url = self.get_refget_store_url()
        if not url:
            raise ValueError("Server does not have a RefgetStore configured")

        try:
            from gtars.refget import RefgetStore
        except ImportError:
            raise ImportError("gtars is required: pip install gtars")

        return RefgetStore.load_remote(cache_dir, url)
```

## Example Client Usage

After implementation, clients can discover capabilities and use them:

```python
from refget import SequenceCollectionClient

client = SequenceCollectionClient(["https://seqcolapi.databio.org"])

# Check FastaDRS availability
if client.is_fasta_drs_enabled():
    # Use DRS endpoints to download FASTA
    client.download_fasta(digest, "genome.fa")

# Use RefgetStore directly (recommended for large/multiple files)
store_url = client.get_refget_store_url()
if store_url:
    # Option 1: Use convenience method
    store = client.get_refget_store("/tmp/cache")
    store.export_fasta(digest, "genome.fa")

    # Option 2: Manual setup with more control
    from gtars.refget import RefgetStore
    store = RefgetStore.load_remote("/tmp/cache", store_url)
    store.export_fasta(digest, "genome.fa", ["chr1", "chr2"])  # subset
```

## Backwards Compatibility

This is developmental software. We are trying to eliminate old code, not keep it around.

The change is additive - new fields in `seqcol` object and new optional parameter to `create_refget_router()`. Existing code that doesn't pass `refget_store_url` will continue to work.

## Cleanup

Once completed, move the completed plan to `/plans/completed/` subfolder.
