---
name: cite-papers
version: 1.1.0
description: |
  Cite Papers Skill. Takes DOI numbers or paper links and produces a papers.yaml
  citation list with structured metadata for research workflows. Merges into
  existing papers.yaml if present, skipping duplicates.
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - WebFetch
  - Glob
---

# Cite Papers Skill

Takes a list of DOI numbers or paper links and produces or updates a `papers.yaml` citation list.

## Input

The user provides one or more of:
- DOI numbers (e.g., `10.1038/s41586-024-07386-0`)
- DOI URLs (e.g., `https://doi.org/10.1038/s41586-024-07386-0`)
- PubMed links (e.g., `https://pubmed.ncbi.nlm.nih.gov/12345678/`)
- PMC links (e.g., `https://pmc.ncbi.nlm.nih.gov/articles/PMC12345678/`)
- Direct journal links

The user may also just say "add these to papers.yaml" after a `/literature-search`, in which case check `doi.md` in the current directory for DOIs to process.

## Process

1. **Check for existing papers.yaml** in the target directory:
   - If it exists, read it and extract all existing DOIs (from `full_text_link` fields and any DOI patterns)
   - Track existing `paper_id` values to avoid collisions
   - New entries will be appended; duplicates (by DOI) are skipped

2. **For each new DOI or link**:
   - Use WebFetch to retrieve paper metadata
   - For DOIs, use CrossRef API: `https://api.crossref.org/works/{DOI}`
   - For PubMed links, fetch the page and extract metadata
   - Extract: title, authors, journal, year, abstract/summary

3. **Generate paper entries** in the YAML format below

4. **Write or update papers.yaml**:
   - If no existing file: create with `papers:` header + all new entries
   - If existing file: append new entries after existing ones
   - Preserve all existing entries exactly as they are (don't reformat or reorder)

5. **Report results**: which papers were added, which were skipped as duplicates, which failed

## Output Format

```yaml
papers:
- paper_id: firstauthorYEARkeyword
  title: "Full Paper Title Here"
  year: 2024
  full_text_link: https://example.com/full/paper/url
  journal: Journal Name
  citation: FirstAuthor et al., Journal Abbrev (Year)
  summary: One-sentence summary of the paper's main finding or contribution.
  type: review|research|meta-analysis|case-study
  status: pending
```

### Field specifications

- **paper_id**: Lowercase, format `firstauthorlastnameYEARfirstkeyword` (e.g., `smith2024neural`). Must be unique within the file.
- **title**: Full title in double quotes
- **year**: Four-digit publication year
- **full_text_link**: Prefer PMC links if available, otherwise DOI link or journal URL
- **journal**: Full journal name (can use common abbreviations)
- **citation**: Format as `LastName et al., JournalAbbrev (Year)` - first author only, abbreviate journal
- **summary**: Brief (1-2 sentence) description of the paper's main contribution or finding
- **type**: One of `review`, `research`, `meta-analysis`, `case-study`, `commentary`, `protocol`
- **status**: One of:
  - `pending` - no PDF yet
  - `downloaded` - PDF obtained in `pdf/` directory
  - `processed` - converted to markdown in `md/` directory

Default new entries to `pending`. If `/literature-search` already downloaded the PDF, it will have set the status to `downloaded` - preserve that.

### Handling entries from /literature-search

If a `papers.yaml` already exists (e.g., created by `/literature-search`), it may contain extra fields like `relevance` and `tier`. Preserve these fields when merging - do not strip them.

## Instructions for Claude

1. Parse all DOIs/links from the user's input (or from `doi.md` if directed)
2. Read existing `papers.yaml` if present, note existing DOIs and paper_ids
3. Fetch metadata for each new paper using WebFetch
4. Skip any paper whose DOI already appears in the existing file
5. Generate properly formatted YAML entries for new papers
6. Append new entries to the file (or create new file)
7. Report: N added, N skipped (duplicate), N failed (with reasons)
