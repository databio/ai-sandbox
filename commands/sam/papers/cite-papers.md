# Cite Papers Skill

Takes a list of DOI numbers or paper links and produces a papers.yaml citation list.

## Input

The user provides one or more of:
- DOI numbers (e.g., `10.1038/s41586-024-07386-0`)
- DOI URLs (e.g., `https://doi.org/10.1038/s41586-024-07386-0`)
- PubMed links (e.g., `https://pubmed.ncbi.nlm.nih.gov/12345678/`)
- PMC links (e.g., `https://pmc.ncbi.nlm.nih.gov/articles/PMC12345678/`)
- Direct journal links

## Process

1. For each DOI or link provided:
   - Use WebFetch to retrieve paper metadata from the source
   - For DOIs, fetch from `https://doi.org/{DOI}` or use CrossRef API: `https://api.crossref.org/works/{DOI}`
   - Extract: title, authors, journal, year, abstract/summary

2. Generate paper entries in the required YAML format

3. Write or append to `papers.yaml` in the current working directory (or directory specified by user)

## Output Format

Each paper entry must follow this exact YAML structure:

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

### Field specifications:

- **paper_id**: Lowercase, format is `firstauthorlastnameYEARfirstkeyword` (e.g., `smith2024neural`)
- **title**: Full title in double quotes
- **year**: Four-digit publication year
- **full_text_link**: Prefer PMC links if available, otherwise DOI link or journal URL
- **journal**: Full journal name (can use common abbreviations)
- **citation**: Format as `LastName et al., JournalAbbrev (Year)` - use first author only, abbreviate journal
- **summary**: Brief (1-2 sentence) description of the paper's main contribution or finding
- **type**: One of `review`, `research`, `meta-analysis`, `case-study`, `commentary`, `protocol`
- **status**: Default to `pending`

## Example output

```yaml
papers:
- paper_id: johnson2023microbiome
  title: "The gut-brain axis in neurological disease: mechanisms and therapeutic potential"
  year: 2023
  full_text_link: https://pmc.ncbi.nlm.nih.gov/articles/PMC10234567/
  journal: Nature Reviews Neuroscience
  citation: Johnson et al., Nat Rev Neurosci (2023)
  summary: Comprehensive review examining bidirectional communication between gut microbiota and the central nervous system, with focus on therapeutic interventions for neurological disorders.
  type: review
  status: pending

- paper_id: chen2024crispr
  title: "CRISPR-based epigenome editing for metabolic disease treatment"
  year: 2024
  full_text_link: https://doi.org/10.1016/j.cell.2024.01.015
  journal: Cell
  citation: Chen et al., Cell (2024)
  summary: Demonstrates novel CRISPR-dCas9 approach for targeted epigenetic modification of metabolic genes, achieving sustained glucose regulation in diabetic mouse models.
  type: research
  status: pending
```

## Instructions for Claude

1. Parse all DOIs/links from the user's input
2. Fetch metadata for each paper using WebFetch
3. If a papers.yaml already exists in the target directory, read it first and append new entries
4. If creating new file, start with `papers:` header
5. Generate properly formatted YAML entries
6. Write the complete papers.yaml file
7. Report which papers were successfully added and any that failed
