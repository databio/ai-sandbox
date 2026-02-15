---
name: bulk-pdf-md
version: 1.0.0
description: |
  Bulk PDF to Markdown Conversion. Converts all PDFs in a directory to markdown
  using markitdown CLI. Generates and runs a bash script for batch processing.
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
---

# Bulk PDF to Markdown

Converts all PDFs in a `pdf/` directory to markdown files in `md/` using `markitdown`.

## Input

The user provides a **topic directory** path. The skill expects PDFs in `{dir}/pdf/` and writes markdown to `{dir}/md/`.

Optionally, the user can specify a `papers.yaml` tier filter (e.g., "primary only") to skip PDFs for secondary papers.

## Process

1. **Scan** `{dir}/pdf/` for all `.pdf` files
2. **Check** `{dir}/md/` for already-converted files (skip any where `{basename}.md` exists)
3. **Filter by tier** (optional): if `{dir}/papers.yaml` exists and the user wants tier filtering, read it and only convert PDFs whose `paper_id` matches the PDF basename and has the requested tier
4. **Generate** a bash script at `{dir}/convert.sh` that runs `markitdown` on each PDF
5. **Run** the script
6. **Update** `papers.yaml` statuses from `downloaded` to `processed` for successfully converted papers
7. **Report** results

## Generated Script

The script should:
- Use absolute paths
- Create the `md/` directory if needed
- Run each conversion independently (no `set -e`) so one failure doesn't stop the batch
- Log success/failure per file
- Use the pattern: `markitdown "$PDF_DIR/$pdf" -o "$MD_DIR/${basename}.md"`

## After Conversion

1. Check which `.md` files were created and their sizes
2. Flag any that are suspiciously small (<1KB) as potential failures
3. Update `papers.yaml` if present: change `status: downloaded` to `status: processed` for each successfully converted paper
4. Print a summary table: filename, size, status

## Notes

- `markitdown` must be installed (`pip install markitdown`)
- Figures are not preserved
- Some PDFs (scanned/image-only) will produce empty or garbage output
- The generated `convert.sh` is left in the directory for reproducibility
