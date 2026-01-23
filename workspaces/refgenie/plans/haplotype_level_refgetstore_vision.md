# Haplotype-Level RefgetStore: A Vision for Pangenome Storage

## Executive Summary

This document describes a future extension of RefgetStore that would enable efficient pangenome storage through haplotype-level deduplication. While the current RefgetStore provides excellent random access and GA4GH compliance, its sequence-level granularity limits deduplication benefits for pangenomes where sequences differ by small variants.

## Current RefgetStore Architecture

### What It Does

RefgetStore is a content-addressable sequence storage system built on gtars. It provides:

1. **Sequence storage by digest** - Each unique sequence is stored once, identified by its GA4GH refget digest (TRUNC512)
2. **Fast random access** - Efficient retrieval of arbitrary subsequences via indexed storage
3. **Sequence collections** - Groupings of sequences with metadata (names, lengths) following the GA4GH seqcol standard
4. **API compatibility** - Designed for integration with refget/seqcol APIs

### Storage Model

```
RefgetStore
├── sequences/
│   ├── {digest_1} → ACGTACGT...  (full chr1 from genome A)
│   ├── {digest_2} → ACGTACGT...  (full chr1 from genome B, differs by 1 SNP)
│   └── {digest_3} → ACGTACGT...  (full chr2, shared by A and B)
└── collections/
    ├── genome_A → [digest_1, digest_3, ...]
    └── genome_B → [digest_2, digest_3, ...]
```

### Deduplication Behavior

Deduplication occurs when **entire sequences are identical**:
- If genome A and genome B have identical chr2 → stored once ✓
- If genome A and genome B have chr1 differing by 1 SNP → stored twice ✗

## The Pangenome Problem

### Why Sequence-Level Granularity Falls Short

In a pangenome with N haplotypes:

| Scenario | Current RefgetStore | Ideal |
|----------|-------------------|-------|
| All haplotypes identical | 1x storage | 1x storage |
| Each haplotype has 1 unique SNP | Nx storage | ~1x storage + variants |
| Highly divergent sequences | Nx storage | Nx storage |

For human pangenomes, most chromosomes are >99% identical across haplotypes. Storing full sequences for each haplotype wastes enormous space on redundant data.

### The Math

- Human chr1: ~250 Mb
- 100 haplotypes with 0.1% divergence each
- Current: 100 × 250 Mb = 25 GB
- Ideal: 250 Mb + variant data ≈ 300 Mb

**Potential 80-100x storage reduction for typical pangenomes.**

## Vision: Dual-Mode RefgetStore

### Core Concept

Extend RefgetStore to support **both** traditional sequence storage **and** pangenome-style segment-based storage in a unified system. The key insight: segments are just sequences at a different granularity—they share the same `sequences/` folder.

### Proposed Directory Structure

```
RefgetStore/
├── sequences/           # ALL content-addressed sequences (shared)
│   ├── {full_chr_digest}    → 250 Mb chromosome
│   └── {segment_digest}     → 10 kb haploblock
├── collections/         # Traditional seqcol (points to full sequences)
│   └── {digest}.json
├── pangenomes/          # Groups of sequence collections
│   └── {digest}.json
└── graphs/              # Segment connectivity + haplotype paths
    └── {digest}.json
```

### Key Design Decisions

1. **Shared sequences folder** - Full chromosomes and small segments coexist. A segment's digest won't collide with a chromosome's digest. Simpler than separate folders.

2. **Pangenomes and graphs are separate concepts**:
   - **Pangenome** = a collection of sequence collections (the haplotypes/genomes that belong together)
   - **Graph** = segment connectivity structure with haplotype paths
   - They're orthogonal: one pangenome could have multiple graphs (different segmentation strategies)

3. **GraphPaths live with graphs** - A path represents "how does haplotype X traverse this graph"—meaningless without the graph context.

### Rust Structs

```rust
/// A pangenome is a collection of sequence collections
#[derive(Debug, Clone)]
pub struct Pangenome {
    pub digest: String,
    pub name: String,                      // e.g., "HPRC-v1.0"
    pub description: Option<String>,
    pub collections: Vec<String>,          // Sequence collection digests
}

/// A node in the graph - references a sequence by digest
#[derive(Debug, Clone)]
pub struct GraphNode {
    pub digest: String,                    // Points to sequences/ folder
    pub length: u64,                       // Cached for position math
}

/// An edge between nodes
#[derive(Debug, Clone)]
pub struct GraphEdge {
    pub from: String,                      // Node digest
    pub to: String,                        // Node digest
}

/// A path through the graph (one per haplotype/sequence)
#[derive(Debug, Clone)]
pub struct GraphPath {
    pub name: String,                      // e.g., "HG002:hap1" or sequence digest
    pub segments: Vec<String>,             // Ordered segment digests
    pub cumulative_lengths: Vec<u64>,      // For O(log n) position lookup
}

/// A graph: nodes, edges, and paths for each haplotype
#[derive(Debug, Clone)]
pub struct SegmentGraph {
    pub digest: String,
    pub name: String,                      // e.g., "HPRC-chr1"
    pub nodes: Vec<GraphNode>,             // Segment digests + lengths
    pub edges: Vec<GraphEdge>,             // Valid transitions
    pub paths: Vec<GraphPath>,             // One per haplotype
}
```

### Relationships

```
Pangenome (HPRC-v1.0)
    └── collections: [seqcol_A, seqcol_B, seqcol_C, ...]
                            │
                            │ (same haplotypes appear as paths)
                            ▼
SegmentGraph (chr1-graph) ──→ paths: [GraphPath, GraphPath, ...]
                                          │
                                          │ (paths reference segments)
                                          ▼
                                   sequences/ (shared pool)
```

The pangenome groups collections conceptually; the graph provides mechanical reconstruction via paths.

### Position Lookup Algorithm

The `cumulative_lengths` field in `GraphPath` enables O(log n) position lookup:

```rust
impl GraphPath {
    /// Find which segment contains a position
    pub fn segment_at(&self, pos: u64) -> Option<(&str, u64)> {
        // Binary search cumulative_lengths to find segment index
        // Return (segment_digest, offset_within_segment)
    }
}
```

### Extended RefgetStore API

```rust
impl RefgetStore {
    // Existing
    pub fn get_sequence(&self, digest: &str) -> Result<Sequence>;
    pub fn get_collection(&self, digest: &str) -> Result<SequenceCollection>;

    // New
    pub fn get_pangenome(&self, digest: &str) -> Result<Pangenome>;
    pub fn get_graph(&self, digest: &str) -> Result<SegmentGraph>;
    pub fn get_haplotype_sequence(
        &self,
        graph: &str,
        haplotype: &str,
        start: u64,
        end: u64
    ) -> Result<Vec<u8>>;
}
```

### Relationship to Existing Standards

| Standard | Role |
|----------|------|
| GFA | Graph structure format (could use for interchange) |
| GA4GH refget | Segment retrieval API |
| GA4GH seqcol | Collection-level metadata |
| VG/GBWT | Inspiration for path encoding |

### Open Questions

1. **Segmentation strategy**: Fixed-size blocks? Variant-boundary? Anchor-based?
2. **Graph encoding**: Full GFA? Compressed path representation?
3. **Query performance**: Can we match current RefgetStore speeds for random access?
4. **Coordinate systems**: How to handle insertions/deletions in position mapping?
5. **Incremental updates**: Adding new haplotypes without rebuilding?
6. **Graph-collection linkage**: How to associate a seqcol with its path through a graph? Store in graph? In a separate index?

## Implementation Phases

### Phase 1: Core Structs

Add the new struct definitions to gtars:
- `Pangenome`, `SegmentGraph`, `GraphNode`, `GraphEdge`, `GraphPath`
- Serialization/deserialization (JSON or binary)
- Basic CRUD operations

### Phase 2: Directory Structure

Extend RefgetStore disk layout:
- Add `pangenomes/` and `graphs/` folders
- Implement load/save for new types
- Ensure backward compatibility with existing stores

### Phase 3: Path-Based Retrieval

Implement `get_haplotype_sequence()`:
- Binary search for position → segment mapping
- Multi-segment retrieval and concatenation
- Handle edge cases (spanning segments, boundaries)

### Phase 4: Graph Construction

Tools to build graphs:
- Import from GFA
- Build from VCF + reference
- Segmentation algorithms

### Phase 5: API Integration

Expose via refget/seqcol APIs:
- New endpoints for pangenomes and graphs
- Maintain backward compatibility

## Research Questions

1. **What's the optimal segment size?** Too small = index overhead; too large = reduced deduplication
2. **How does query latency scale with graph complexity?**
3. **Can we achieve sub-millisecond random access for typical queries?**
4. **What's the crossover point where haplotype-level beats sequence-level?**

## Conclusion

This dual-mode approach lets RefgetStore handle both traditional reference genomes and pangenomes in a unified system. By sharing the `sequences/` folder and separating the concepts of pangenomes (collection grouping) from graphs (segment connectivity), we maintain clean architecture while enabling dramatic storage savings for pangenome use cases.

---

*This document describes future research directions, not current RefgetStore capabilities.*
