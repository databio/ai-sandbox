# CLI Storage Mode Support

**Status:** Proposed
**Date:** 2026-01-19

## Problem

The refget CLI currently doesn't expose storage mode (Encoded vs Raw) options. This is needed for:

1. **Benchmarking** - Compare performance of Encoded vs Raw modes
2. **User choice** - Some users may prefer Raw for speed, others Encoded for compression
3. **Debugging** - Raw mode is easier to inspect manually

## Proposed Changes

### 1. Add `--mode` flag to `refget store init`

```bash
refget store init [--path PATH] [--mode encoded|raw]
```

**Options:**
- `--mode, -m`: Storage mode. Options: `encoded` (default), `raw`

**Implementation in `refget/cli/store.py`:**

```python
from enum import Enum

class StorageMode(str, Enum):
    encoded = "encoded"
    raw = "raw"

@app.command()
def init(
    path: Optional[Path] = typer.Option(...),
    mode: StorageMode = typer.Option(
        StorageMode.encoded,
        "--mode",
        "-m",
        help="Storage mode: encoded (compressed) or raw",
    ),
) -> None:
    """Initialize a local RefgetStore."""
    from refget.processing import RefgetStore, StorageMode as GtarsStorageMode

    store = RefgetStore.on_disk(str(store_path))

    if mode == StorageMode.raw:
        store.set_encoding_mode(GtarsStorageMode.Raw)
    else:
        store.set_encoding_mode(GtarsStorageMode.Encoded)

    # ... rest of init
```

### 2. Add `--mode` flag to `refget store add`

```bash
refget store add FASTA [--path PATH] [--mode encoded|raw]
```

If mode is specified, it overrides the store's current mode for this addition.

### 3. Show mode in `refget store stats`

```bash
refget store stats
# {"collections": 3, "sequences": 75, "storage_mode": "Encoded", ...}
```

## Alternative: Store mode in config

Could also support setting mode in config:

```toml
[store]
path = "~/.refget/store"
mode = "encoded"  # or "raw"
```

Then CLI flag would override config.

## Impact on Benchmarking

With this change, the benchmark could use CLI for store operations:

```bash
# Encoded mode benchmark
refget store init --path /tmp/bench_encoded --mode encoded
refget store add genome.fa --path /tmp/bench_encoded

# Raw mode benchmark
refget store init --path /tmp/bench_raw --mode raw
refget store add genome.fa --path /tmp/bench_raw

# Compare sizes
refget store stats --path /tmp/bench_encoded
refget store stats --path /tmp/bench_raw
```

## Files to Modify

1. `refget/cli/store.py` - Add mode parameter to init and add commands
2. `refget/cli/config_manager.py` - Add mode to config schema (optional)
3. `refget/cli/store.py` stats command - Include mode in output

## Testing

Add tests for:
- `refget store init --mode raw` creates raw store
- `refget store init --mode encoded` creates encoded store
- Default mode is encoded
- `refget store stats` shows correct mode
