# Plan: Lambda-based FASTA DRS with Async Generation

## Status: Not Started (Future Enhancement)

This plan describes an optional Lambda-based system for on-demand FASTA generation from a RefgetStore hosted on S3.

## Overview

A Lambda function generates FASTA files on-demand from a RefgetStore, stages them to S3, and serves them via DRS with async (202 Accepted) flow.

## Architecture

```
┌──────────────┐      ┌─────────────────┐      ┌──────────────────┐
│  DRS Request │─────▶│  seqcolapi      │─────▶│  Lambda          │
│  (digest)    │      │  (triggers)     │      │  (generates)     │
└──────────────┘      └─────────────────┘      └──────────────────┘
       │                      │                        │
       │                      │                        ▼
       │                      │               ┌──────────────────┐
       │                      │               │ RefgetStore (S3) │
       │                      │               │ s3://bucket/store/│
       │                      │               └──────────────────┘
       │                      │                        │
       │                      ▼                        ▼
       │              ┌─────────────────┐      ┌──────────────────┐
       │              │  Status Check   │      │ Generated FASTA  │
       │              │  (S3 exists?)   │      │ s3://bucket/fasta/│
       └─────────────▶└─────────────────┘◀─────└──────────────────┘
                              │
                              ▼
                      ┌─────────────────┐
                      │  User Download  │
                      │  (presigned URL)│
                      └─────────────────┘
```

## gtars RefgetStore API

The Lambda uses these RefgetStore methods:

```python
from gtars.refget import RefgetStore

# Load from remote with local cache (disk-backed)
store = RefgetStore.load_remote("/tmp/cache", "s3://bucket/store/")

# Or load into memory first, then optionally persist
store = RefgetStore.in_memory()
# ... load data ...
store.enable_persistence("/tmp/cache")  # Flush to disk
store.disable_persistence()  # Stop caching

# Export FASTA (uncompressed)
store.export_fasta(collection_digest, "/tmp/output.fa")
store.export_fasta(collection_digest, "/tmp/output.fa", ["chr1", "chr2"])  # Subset
store.export_fasta(collection_digest, "/tmp/output.fa", None, 80)  # Custom line width

# Export by sequence digests directly
store.export_fasta_by_digests(["digest1", "digest2"], "/tmp/output.fa")

# Export regions from BED file
store.export_fasta_from_regions(collection_digest, "regions.bed", "/tmp/output.fa")
```

**Note:** gtars does not have a built-in gzip export. The Lambda should gzip using Python's `gzip` module after export.

## Flow

### 1. User Requests FASTA

```
GET /fasta/objects/{digest}/access/s3
```

### 2. seqcolapi Checks S3 Cache

```python
s3_key = f"fasta/{digest}.fa.gz"

if s3_exists(bucket, s3_key):
    # Already generated - return URL immediately
    return {"url": presign(bucket, s3_key)}
```

### 3. If Not Cached, Trigger Lambda + Return 202

```python
# Trigger Lambda async
lambda_client.invoke(
    FunctionName="fasta-generator",
    InvocationType="Event",  # async, don't wait
    Payload=json.dumps({
        "digest": digest,
        "store_url": REFGET_STORE_URL,
        "output_bucket": OUTPUT_BUCKET,
        "output_key": s3_key
    })
)

# Return 202 - come back later
return Response(
    status_code=202,
    headers={"Retry-After": "60"},
    content=json.dumps({
        "status": "generating",
        "message": "FASTA is being generated. Retry in ~60 seconds."
    })
)
```

### 4. Lambda Generates FASTA

```python
# handler.py
import json
import gzip
import shutil
import os
import boto3
from gtars.refget import RefgetStore

s3 = boto3.client("s3")

def handler(event, context):
    digest = event["digest"]
    store_bucket = event["store_bucket"]
    store_prefix = event.get("store_prefix", "store/")
    output_bucket = event["output_bucket"]
    output_key = event["output_key"]

    store_url = f"s3://{store_bucket}/{store_prefix}"

    try:
        # Load store with /tmp as cache (Lambda has 10GB ephemeral storage)
        store = RefgetStore.load_remote("/tmp/cache", store_url)

        # Generate FASTA to /tmp
        tmp_fasta = f"/tmp/{digest}.fa"
        store.export_fasta(digest, tmp_fasta, None, 80)

        # Gzip the FASTA
        tmp_gzipped = f"/tmp/{digest}.fa.gz"
        with open(tmp_fasta, 'rb') as f_in:
            with gzip.open(tmp_gzipped, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Upload to S3
        s3.upload_file(
            tmp_gzipped,
            output_bucket,
            output_key,
            ExtraArgs={"ContentType": "application/gzip"}
        )

        # Clean up
        os.remove(tmp_fasta)
        os.remove(tmp_gzipped)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "complete",
                "bucket": output_bucket,
                "key": output_key
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "message": str(e)
            })
        }
```

### 5. User Retries, Gets URL

```
GET /fasta/objects/{digest}/access/s3

→ 200 OK
{
  "url": "https://bucket.s3.amazonaws.com/fasta/{digest}.fa.gz"
}
```

## S3 Bucket Structure

```
s3://refget-bucket/
├── store/                    # RefgetStore data (source)
│   ├── rgstore.json
│   ├── sequences/
│   └── collections/
└── fasta/                    # Generated FASTAs (cache)
    ├── {digest1}.fa.gz
    ├── {digest2}.fa.gz
    └── ...
```

## Deployment

### Lambda Function (Zip Package)

gtars publishes manylinux wheels, so a simple zip deployment works:

```bash
# Create package directory
mkdir -p package
pip install gtars boto3 -t package/

# Create zip
cd package && zip -r ../lambda.zip .
cd .. && zip lambda.zip handler.py

# Deploy
aws lambda create-function \
    --function-name fasta-generator \
    --runtime python3.11 \
    --handler handler.handler \
    --zip-file fileb://lambda.zip \
    --role arn:aws:iam::${ACCOUNT}:role/lambda-fasta-generator \
    --timeout 300 \
    --memory-size 4096 \
    --ephemeral-storage Size=10240
```

### seqcolapi Integration

Add to `refget_router.py` or create new endpoint file:

```python
import boto3
from fastapi import APIRouter, Response
from botocore.exceptions import ClientError

router = APIRouter(prefix="/fasta", tags=["FASTA DRS"])

lambda_client = boto3.client("lambda")
s3_client = boto3.client("s3")

STORE_BUCKET = os.environ["REFGET_STORE_BUCKET"]
STORE_PREFIX = os.environ.get("REFGET_STORE_PREFIX", "store/")
FASTA_BUCKET = os.environ["FASTA_CACHE_BUCKET"]
FASTA_PREFIX = os.environ.get("FASTA_CACHE_PREFIX", "fasta/")
LAMBDA_FUNCTION = os.environ["FASTA_GENERATOR_LAMBDA"]


def s3_key_exists(bucket: str, key: str) -> bool:
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False


def presign_url(bucket: str, key: str, expiry: int = 3600) -> str:
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expiry
    )


@router.get("/objects/{digest}/access/{access_id}")
def get_access(digest: str, access_id: str):
    """DRS access URL resolution - triggers generation if needed."""

    s3_key = f"{FASTA_PREFIX}{digest}.fa.gz"

    # Check if already generated
    if s3_key_exists(FASTA_BUCKET, s3_key):
        return {"url": presign_url(FASTA_BUCKET, s3_key)}

    # Not cached - trigger Lambda
    lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION,
        InvocationType="Event",  # async
        Payload=json.dumps({
            "digest": digest,
            "store_bucket": STORE_BUCKET,
            "store_prefix": STORE_PREFIX,
            "output_bucket": FASTA_BUCKET,
            "output_key": s3_key
        })
    )

    # Return 202 Accepted
    return Response(
        status_code=202,
        headers={"Retry-After": "60"},
        content=json.dumps({
            "status": "generating",
            "message": "FASTA is being generated. Retry in ~60 seconds.",
            "retry_after": 60
        }),
        media_type="application/json"
    )
```

## Configuration

### Environment Variables (seqcolapi)

```bash
REFGET_STORE_BUCKET=my-refget-bucket
REFGET_STORE_PREFIX=store/
FASTA_CACHE_BUCKET=my-refget-bucket  # can be same bucket
FASTA_CACHE_PREFIX=fasta/
FASTA_GENERATOR_LAMBDA=fasta-generator
AWS_REGION=us-east-1
```

### S3 Lifecycle Policy (Optional)

Auto-expire generated FASTAs after 30 days:

```json
{
  "Rules": [{
    "ID": "expire-fasta-cache",
    "Filter": {"Prefix": "fasta/"},
    "Status": "Enabled",
    "Expiration": {"Days": 30}
  }]
}
```

## Cost Estimate

| Component | Per Request | Notes |
|-----------|-------------|-------|
| Lambda (4GB × 60s) | ~$0.004 | Worst case |
| S3 GET (store) | ~$0.0004 | Multiple objects |
| S3 PUT (fasta) | ~$0.000005 | One object |
| S3 Storage | ~$0.02/month | Per cached genome |
| **Total generation** | **~$0.005** | |
| **Cached request** | **~$0.0001** | Just S3 HEAD + presign |

Egress depends on setup:
- Public Dataset: $0
- Standard S3: ~$0.08 per gzipped genome

## Summary

| Step | Who | What |
|------|-----|------|
| 1 | User | `GET /fasta/objects/{digest}/access/s3` |
| 2 | seqcolapi | Check S3 cache |
| 3a | seqcolapi | If cached → return presigned URL |
| 3b | seqcolapi | If not → trigger Lambda, return 202 |
| 4 | Lambda | Load RefgetStore from S3 |
| 5 | Lambda | Generate FASTA, gzip with Python |
| 6 | Lambda | Upload to S3 fasta cache |
| 7 | User | Retry after 60s → get presigned URL |
| 8 | User | Download from S3 |
