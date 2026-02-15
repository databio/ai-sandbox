---
name: literature-search
version: 1.0.0
description: |
  Deep Literature Search. Takes a scientific topic or research question and
  performs a multi-source, 2-hop citation crawl across biomedical databases.
  Returns papers.yaml with full metadata and doi.md with bare DOI numbers.
  Auto-downloads open-access PDFs where available.
user-invocable: true
allowed-tools:
  - WebFetch
  - WebSearch
  - Read
  - Write
  - Bash
  - Task
  - AskUserQuestion
---

# Deep Literature Search

Performs a systematic, multi-source literature search on a scientific topic. Outputs `papers.yaml` with full metadata for review and `doi.md` with bare DOIs. Auto-downloads open-access PDFs.

## Input

The user provides:
- A **research topic or question**
- Optionally: year range, paper type preferences, number of results desired, exclusion criteria, output directory

## Strategy Overview

```
Query Decomposition → Multi-Source Search → Anchor Selection →
  1st Hop (refs + citers of anchors) → Filter & Score →
    2nd Hop (refs + citers of top 1st-hop) → Deduplicate → Rank →
      Output papers.yaml + doi.md → Download open-access PDFs
```

## Detailed Process

### Phase 1: Query Decomposition

Decompose the research topic into multiple search facets:

1. **Core concept terms** - the central biological phenomenon
2. **MeSH-adjacent terms** - standardized biomedical vocabulary equivalents
3. **Synonyms and alternative phrasings** - different ways the same concept appears in literature
4. **Mechanistic terms** - specific pathways, genes, proteins, cell types involved
5. **Context terms** - disease, tissue, organism, experimental model

Generate 3-5 distinct query formulations that approach the topic from different angles. Derive all queries directly from the user's input - do not inject default terms or assumptions.

### Phase 2: Multi-Source Initial Search

#### Primary: PubMed (via E-utilities)

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query}&retmax=20&retmode=json&sort=relevance
```

Then fetch details:
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={comma_separated_ids}&retmode=json
```

Extract: PMID, DOI, title, authors, journal, year.

PubMed query syntax:
- MeSH terms: `"Term"[MeSH]`
- Field tags: `[Title/Abstract]`, `[MeSH Major Topic]`
- Boolean: `AND`, `OR`, `NOT`
- Filters: `AND "review"[pt]`, `AND "last 5 years"[dp]`

Run **each decomposed query** separately.

#### Secondary: Semantic Scholar

```
https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=20&fields=externalIds,title,year,authors,citationCount,abstract,tldr,openAccessPdf
```

Collect `paperId` values for citation crawling. Note the `openAccessPdf` field for Phase 8.

**Rate limit**: Max 100 requests per 5 minutes without API key.

#### Tertiary: OpenAlex

```
https://api.openalex.org/works?search={query}&per_page=25&sort=relevance_score:desc&filter=type:article
```

Note the `open_access.oa_url` field for Phase 8.

#### Supplementary: WebSearch

Use WebSearch targeting scholarly sources for recent/preprint coverage.

### Phase 3: Anchor Selection

From all initial results:

1. **Deduplicate by DOI**
2. **Score** on: multi-source hits, keyword density, citation count, paper type, recency
3. **Select 5-8 anchor papers** representing diverse facets of the topic

Report anchors to user and ask if the direction looks right before proceeding with the citation crawl.

### Phase 4: First-Hop Citation Crawl

For each anchor, use Semantic Scholar:

**References:**
```
https://api.semanticscholar.org/graph/v1/paper/{paper_id}/references?fields=externalIds,title,year,authors,citationCount,abstract&limit=100
```

**Citations:**
```
https://api.semanticscholar.org/graph/v1/paper/{paper_id}/citations?fields=externalIds,title,year,authors,citationCount,abstract&limit=100
```

Paper ID formats: `DOI:{doi}`, `PMID:{pmid}`, or Semantic Scholar `paperId`.

Filter, score by relevance, track network frequency. Keep top 15-20 per anchor.

### Phase 5: Second-Hop Citation Crawl

Select top 10-15 first-hop papers. Repeat citation crawl. Prioritize:
- Papers appearing in multiple 1st-hop citation lists
- Reviews or highly-cited papers
- Papers covering underrepresented facets

Use the Task tool to parallelize API calls where possible.

### Phase 6: Deduplication and Final Ranking

Score all papers:
1. **Network centrality** (40%): appearances across citation chains
2. **Query relevance** (30%): keyword/concept match against topic facets
3. **Citation impact** (15%): citation count normalized by year
4. **Recency** (15%): newer papers weighted higher

### Phase 7: Output Files

**Target: top 10 primary papers.** Don't force this number - quality over quantity.

#### papers.yaml

Write to `papers.yaml` in the output directory. If `papers.yaml` already exists, read it first and append new entries (skip duplicates by DOI).

Use the standard cite-papers YAML format:

```yaml
papers:
- paper_id: {firstauthorlastnameYEARkeyword}
  title: "Full Paper Title"
  year: YYYY
  full_text_link: {best available URL - prefer PMC, then DOI}
  journal: Journal Name
  citation: LastName et al., JournalAbbrev (Year)
  summary: {2-3 sentence description based on abstract/tldr}
  type: {review|research|meta-analysis|case-study|commentary|protocol}
  relevance: {1-2 sentences on why this paper matters for the user's topic}
  tier: {primary|secondary}
  status: pending
```

The `relevance` and `tier` fields are additions beyond standard cite-papers format, used for triage.

#### doi.md

Write to `doi.md` in the output directory. Bare DOIs only, one per line, grouped by tier:

```markdown
# Primary

10.xxxx/...
10.xxxx/...

# Secondary

10.xxxx/...
```

### Phase 8: Open-Access PDF Download

After writing papers.yaml, attempt to download PDFs for open-access papers:

1. **Check open-access availability** for each paper using data already collected:
   - Semantic Scholar `openAccessPdf.url` (collected in Phase 2)
   - OpenAlex `open_access.oa_url` (collected in Phase 2)
   - If not already known, check **Unpaywall**: `https://api.unpaywall.org/v2/{doi}?email=user@example.com`
   - PMC papers have predictable PDF URLs: `https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/`

2. **Download available PDFs** using Bash with curl:
   ```
   curl -L -o pdf/{paper_id}.pdf "{pdf_url}"
   ```
   Create the `pdf/` directory if it doesn't exist.

3. **Update papers.yaml status** for successfully downloaded papers:
   - `status: downloaded` (PDF obtained, ready for conversion)
   - Papers without available PDFs remain `status: pending`

4. **Report download results**: list which papers were downloaded and which need manual access.

## Important Guidelines

### Rate Limiting

- **Semantic Scholar**: Max 100 requests per 5 minutes. Track call count.
- **PubMed E-utilities**: Max 3 requests/second. Pause between calls.
- **Unpaywall**: Include email parameter. Reasonable rate.
- **OpenAlex**: Generous limits.

### Quality Over Quantity

- Goal is ~10 high-quality primary papers, not exhaustive coverage
- Every primary paper needs a clear reason for inclusion
- Exclude papers with no DOI from final output

### Transparency

- Report which queries were run and against which databases
- Note any databases that were unreachable or returned errors
- Explain any mid-process query reformulation
- Include search metadata for reproducibility

### User Interaction

- After anchor selection (Phase 3), report anchors and confirm direction before the expensive citation crawl
- If initial search returns few results, suggest reformulations
- If results skew to one subfield, flag the imbalance

### Handling Ambiguous Topics

If the topic is broad or ambiguous:
1. Use AskUserQuestion to clarify scope
2. Ask about: organism, disease context, specific pathways, time period
3. Narrow queries accordingly

### Avoiding Bias

- All search terms must derive from the user's stated topic
- No hardcoded terms, example topics, or default assumptions
- Adapt database priority if topic is outside biomedicine

### Status Progression

Papers move through these statuses across the full pipeline:
- `pending` - cited in papers.yaml, no PDF yet (paywalled or not attempted)
- `downloaded` - PDF obtained in `pdf/` directory
- `processed` - converted to markdown in `md/` directory (done by /pdf-to-md)
