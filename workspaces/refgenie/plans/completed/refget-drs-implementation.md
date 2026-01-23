# Plan: Implement DRS Endpoints for FASTA Files

## Overview
Add GA4GH DRS (Data Repository Service) support for FASTA files, enabling retrieval of FASTA file metadata and access URLs via standard DRS endpoints.

## Files to Modify

1. **`refget/agents.py`** - Add `FastaDrsAgent` and modify `RefgetDBAgent`
2. **`refget/refget_router.py`** - Add `fasta_drs_router` and update `create_refget_router()`
3. **`refget/models.py`** - Minor updates to `FastaDrsObject` if needed

## Implementation Steps

### Step 1: Add `FastaDrsAgent` to `agents.py`

Create a new agent class for DRS operations:

```python
class FastaDrsAgent:
    def __init__(self, engine: SqlalchemyDatabaseEngine, url_prefix: Optional[str] = None) -> None:
        self.engine = engine
        self.url_prefix = url_prefix  # e.g., "https://s3.amazonaws.com/mybucket/fastas/"

    def get(self, digest: str) -> FastaDrsObject:
        """Get a FastaDrsObject by its digest (object_id)"""

    def add(self, fasta_drs: FastaDrsObject) -> FastaDrsObject:
        """Add a FastaDrsObject to the database"""

    def list_by_offset(self, limit: int = 50, offset: int = 0) -> dict:
        """List FastaDrsObjects with pagination"""
```

### Step 2: Modify `RefgetDBAgent.__init__`

Add configuration for DRS:

```python
def __init__(
    self,
    engine: Optional[SqlalchemyDatabaseEngine] = None,
    postgres_str: Optional[str] = None,
    schema=SEQCOL_SCHEMA_PATH,
    inherent_attrs: List[str] = DEFAULT_INHERENT_ATTRS,
    fasta_drs_url_prefix: Optional[str] = None,  # NEW
):
    # ... existing init ...
    self.__fasta_drs = FastaDrsAgent(self.engine, fasta_drs_url_prefix)

@property
def fasta_drs(self) -> FastaDrsAgent:
    return self.__fasta_drs
```

### Step 3: Modify `SequenceCollectionAgent.add_from_fasta_file` methods

Update the three FASTA loading methods to optionally create DRS objects:

```python
def add_from_fasta_file(
    self,
    fasta_file_path: str,
    update: bool = False,
    create_fasta_drs: bool = True,  # NEW
) -> SequenceCollection:
    # ... existing logic ...

    if create_fasta_drs:
        # Create FastaDrsObject
        drs_obj = FastaDrsObject.from_fasta_file(fasta_file_path, digest=seqcol.digest)

        # Construct URL from prefix + filename if prefix is configured
        if self.parent.fasta_drs.url_prefix:
            url = self.parent.fasta_drs.url_prefix + os.path.basename(fasta_file_path)
            drs_obj.access_methods = [AccessMethod(type="https", access_url=AccessURL(url=url))]

        self.parent.fasta_drs.add(drs_obj)

    return seqcol
```

Note: `add_from_fasta_file_with_name` and `add_from_fasta_pep` should route through `add_from_fasta_file` or accept the same new parameters.

### Step 4: Add `fasta_drs_router` to `refget_router.py`

Create new router with DRS endpoints:

```python
fasta_drs_router = APIRouter()

@fasta_drs_router.get(
    "/objects/{object_id}",
    summary="Get DRS object by ID",
    tags=["DRS"],
)
async def get_drs_object(
    object_id: str,
    dbagent=Depends(get_dbagent),
):
    """GA4GH DRS endpoint to retrieve object metadata"""
    try:
        drs_obj = dbagent.fasta_drs.get(object_id)
        return drs_obj.to_response(base_uri="drs://seqcolapi.databio.org")
    except ValueError:
        raise HTTPException(status_code=404, detail="Object not found")

@fasta_drs_router.get(
    "/objects/{object_id}/access/{access_id}",
    summary="Get access URL for DRS object",
    tags=["DRS"],
)
async def get_drs_access_url(
    object_id: str,
    access_id: str,
    dbagent=Depends(get_dbagent),
):
    """GA4GH DRS endpoint to get access URL"""
    # Return the access URL for the given access_id

@fasta_drs_router.get(
    "/service-info",
    summary="DRS service info",
    tags=["DRS"],
)
async def drs_service_info():
    """GA4GH DRS service-info endpoint"""
```

### Step 5: Update `create_refget_router()`

Add the new flag:

```python
def create_refget_router(
    sequences: bool = False,
    collections: bool = True,
    pangenomes: bool = False,
    fasta_drs: bool = False,  # NEW
) -> APIRouter:
    refget_router = APIRouter()
    if sequences:
        refget_router.include_router(seq_router)
    if collections:
        refget_router.include_router(seqcol_router)
    if pangenomes:
        refget_router.include_router(pangenome_router)
    if fasta_drs:  # NEW
        refget_router.include_router(fasta_drs_router)
    return refget_router
```

### Step 6: Create S3 Upload Script in `data_loaders/`

Create a separate utility script for S3 uploads that mirrors the FASTA loading interface:

**File: `data_loaders/upload_fasta_to_s3.py`**

```python
"""
Utility script to upload FASTA files to S3.
Uses the same input patterns as the refget FASTA loading functions.

Requires: boto3 (install separately: pip install boto3)
"""

import boto3
import os

def upload_fasta_file(fasta_file_path: str, bucket: str, prefix: str = "") -> str:
    """
    Upload a single FASTA file to S3.

    Args:
        fasta_file_path: Path to the FASTA file
        bucket: S3 bucket name
        prefix: Optional prefix/folder in the bucket

    Returns:
        str: The S3 URL of the uploaded file
    """
    s3 = boto3.client('s3')
    key = os.path.join(prefix, os.path.basename(fasta_file_path))
    s3.upload_file(fasta_file_path, bucket, key)
    return f"https://{bucket}.s3.amazonaws.com/{key}"


def upload_fasta_pep(pep, fa_root: str, bucket: str, prefix: str = "") -> dict:
    """
    Upload FASTA files from a PEP to S3.
    Same interface as SequenceCollectionAgent.add_from_fasta_pep.

    Args:
        pep: peppy.Project object
        fa_root: Root directory containing the FASTA files
        bucket: S3 bucket name
        prefix: Optional prefix/folder in the bucket

    Returns:
        dict: Mapping of FASTA filenames to S3 URLs
    """
    results = {}
    for s in pep.samples:
        fa_path = os.path.join(fa_root, s.fasta)
        url = upload_fasta_file(fa_path, bucket, prefix)
        results[s.fasta] = url
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Upload FASTA files to S3")
    parser.add_argument("--fasta-file", help="Single FASTA file to upload")
    parser.add_argument("--pep", help="PEP file for batch upload")
    parser.add_argument("--fa-root", help="Root directory for FASTA files (with --pep)")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--prefix", default="", help="S3 key prefix")
    # ... parse and execute
```

This keeps boto3 as an optional dependency only needed for the upload scripts, not the core refget package.

## Summary of Changes

| File | Changes |
|------|---------|
| `agents.py` | Add `FastaDrsAgent` class, modify `RefgetDBAgent.__init__` to accept `fasta_drs_url_prefix`, add `fasta_drs` property, update `add_from_fasta_file*` methods |
| `refget_router.py` | Add `fasta_drs_router` with DRS endpoints, update `create_refget_router()` signature |
| `models.py` | No changes needed (models already exist) |
| `data_loaders/upload_fasta_to_s3.py` | New script for S3 uploads with same interface as FASTA loading functions |

## Design Decisions

1. **No boto3 in core package** - S3 upload is handled by separate script in `data_loaders/`, keeping refget lightweight
2. **URL prefix configuration** - `RefgetDBAgent` accepts `fasta_drs_url_prefix` to construct access URLs
3. **Opt-in DRS creation** - `create_fasta_drs=True` (default) in `add_from_fasta_file*` methods
4. **Matching interfaces** - Upload script uses same inputs (fasta file, pep, fa_root) as loading functions for easy workflow integration
