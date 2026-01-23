# PDF to Markdown Conversion

Converts a research paper PDF to a clean, structured markdown file for efficient context usage.

## Input

The user provides:
- A path to a PDF file (e.g., `tgf_sex/pdfs/tam2016sex.pdf`)
- Optionally, a paper_id to use for the output filename (otherwise inferred from the PDF name or content)

## Process

1. Read the PDF using the Read tool
2. Extract and structure the content into clean markdown:
   - Title and authors at the top
   - Abstract in its own section
   - Main sections (Introduction, Methods, Results, Discussion, etc.)
   - Tables converted to markdown tables where possible
   - References section at the end
3. Clean up common PDF parsing artifacts:
   - Remove page headers/footers
   - Fix broken words from line wraps
   - Merge multi-column text into single flow
   - Fix garbled table formatting
4. Save to the `md/` subfolder in the same directory as the PDF
5. Rename the PDF file to `{paper_id}.pdf` in the same directory

## Output Location

The markdown file is saved as:
```
{project_folder}/md/{paper_id}.md
```

For example:
- Input: `tgf_sex/pdfs/tam-et-al-2016-sex-differences.pdf`
- Output: `tgf_sex/md/tam2016sex.md`

## PDF Renaming

After conversion, the original PDF is renamed to match the paper_id:
```
{project_folder}/pdf/{paper_id}.pdf
```

For example:
- Original: `tgf_sex/pdf/tam-et-al-2016-sex-differences.pdf`
- Renamed: `tgf_sex/pdf/tam2016sex.pdf`

## Output Format

Preserve the paper's actual structure. Use `##` for major sections and `###` for subsections, matching whatever headings exist in the original.

```markdown
# Paper Title

**Authors:** [as listed in paper]

**Journal:** [journal, volume, pages, year - if present]

**DOI:** [if present]

---

## Abstract

[Abstract text, if present]

**Keywords:** [if present]

---

[Remaining sections exactly as they appear in the paper, using ## for major headings and ### for subsections. Do NOT invent standard sections like "Methods" or "Results" if they don't exist - use the actual headings from the paper.]

---

## References

[If present, preserve original numbering/format]
```

**Important:** Different paper types have different structures:
- Research articles: often Introduction/Methods/Results/Discussion
- Reviews: may have topic-based sections
- Commentaries: may have no formal sections
- Case studies: may use Case Presentation/Discussion

Always preserve the original structure rather than imposing a template.

## Instructions for Claude

1. **Check if already converted** before doing any work:
   - Determine the expected paper_id (from user input, PDF filename, or papers.yaml)
   - Check if `{project_folder}/md/{paper_id}.md` already exists
   - If it exists, inform the user the paper has already been converted and stop (do not proceed with conversion)
   - Also check papers.yaml if it exists - if the paper's status is `processed`, inform the user and stop
2. Read the PDF file provided by the user
3. Parse the content, identifying:
   - Title (usually largest text at top)
   - Authors and affiliations
   - Journal info if present
   - Abstract section
   - Main body sections
   - References
4. Structure into clean markdown following the format above
5. Check if the `md/` directory exists; only create it if missing
6. Determine the paper_id:
   - If user provided one, use that
   - Otherwise, try to match against papers.yaml if it exists
   - Otherwise, derive from first author lastname + year + first keyword (e.g., `tam2016sex`)
7. Write the markdown file
8. Rename the original PDF file to `{paper_id}.pdf` in its current directory
9. Report the output location and approximate token savings vs PDF

## Updating papers.yaml

After successful conversion, update the paper's status in `papers.yaml` from `pending` to `processed`.

**Matching rules (to avoid updating the wrong entry):**

1. If user provided an explicit paper_id, use that for matching
2. Otherwise, match ONLY if **both** of these conditions are met:
   - The PDF filename contains the first author's last name (case-insensitive)
   - The year in papers.yaml matches a year found in the PDF content
3. If no confident match is found, ask the user which paper_id to update (or skip)
4. Never update based on title similarity alone - titles can be similar across papers

**Update process:**

1. Read the papers.yaml in the same project folder
2. Find the matching entry using rules above
3. Change `status: pending` to `status: processed`
4. Write the updated papers.yaml
5. Report which entry was updated, or why no update was made

## Notes

- Figures are not preserved (describe them in text if critical)
- Complex tables may need manual cleanup
- Chemical formulas and equations may not convert perfectly
- If the PDF is scanned/image-based, conversion will fail
