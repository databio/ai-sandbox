---
name: analysis-structure-check
description: Evaluate an existing analysis project for compliance with the standard structure conventions. Reports what's missing, misplaced, or non-compliant and offers to fix issues. Use when auditing an analysis project or bringing a chaotic folder into compliance.
---

# Analysis Structure Check

Evaluate an existing analysis project against the standard structure and report compliance issues.

## Expected Structure

```
project/
├── CLAUDE.md              # Must contain Analysis Rules section
├── README.md              # Must explain how to run
├── .gitignore             # Must ignore input/, output/
├── src/                   # All analysis code
├── input/                 # Raw data (immutable)
└── output/                # Generated artifacts
    ├── data/              # Computed intermediates
    ├── plots/             # Generated figures
    └── reports/           # Reports referencing plots
```

## Evaluation Steps

### 1. Check directory structure

Verify these exist (as directories or symlinks):
- [ ] `src/` exists
- [ ] `input/` exists (may be symlink)
- [ ] `output/` exists (may be symlink)
- [ ] `output/data/` exists
- [ ] `output/plots/` exists
- [ ] `output/reports/` exists

Report any analysis code files found OUTSIDE of `src/` (stray scripts in project root, nested analysis folders, etc.). Entry point files like `main.py` or `main.R` in the project root are acceptable if documented in README.

### 2. Check CLAUDE.md

- [ ] CLAUDE.md exists
- [ ] Contains an "Analysis Rules" section (or equivalent heading)
- [ ] Rules section includes the key directives:
  - No text tables with numbers
  - No quoting specific values in prose
  - Plots must be self-documenting
  - Reports reference plots by path
- [ ] Contains a "How to Run" section
- [ ] Contains a "Structure" section describing the layout

If CLAUDE.md is missing or incomplete, offer to create/update it.

### 3. Check .gitignore

- [ ] `.gitignore` exists
- [ ] `input/` is gitignored
- [ ] `output/` is gitignored
- [ ] `.env` is gitignored

### 4. Check reports for compliance

Scan any markdown files in `output/reports/` (or project root report files):
- [ ] No markdown tables containing numerical data
- [ ] No specific numerical values quoted in prose (correlations, p-values, means, percentages)
- [ ] Plot references use correct relative paths
- [ ] Referenced plot files actually exist

### 5. Check data pipeline integrity

- [ ] `output/data/` contains intermediate data files (CSV, parquet, RDS, etc.)
- [ ] `output/plots/` contains generated figures (PNG, SVG, PDF)
- [ ] Plotting code reads from `output/data/`, not directly from `input/`
- [ ] No code writes to `input/`

### 6. Check for common anti-patterns

- [ ] No Jupyter notebooks with analysis logic outside `src/` (notebooks for exploration are OK, but core analysis should be in `src/`)
- [ ] No hardcoded absolute paths in code (use relative paths or config)
- [ ] No credentials committed to git (check for `.env` files tracked by git)

## Output Format

Present results as a compliance report:

```
## Analysis Structure Check: [project name]

### ✓ Passing
- [list items that pass]

### ✗ Issues Found
- [list items that fail, with explanation and suggested fix]

### Recommendations
- [optional improvements, not blocking]
```

## Fixing Issues

After reporting, offer to fix each issue:
- Missing directories → create them
- Missing CLAUDE.md → create from template (use analysis-structure-setup template)
- Missing .gitignore entries → add them
- Report compliance issues → flag for human review (don't auto-fix reports)
- Stray scripts → suggest moving to `src/` (don't move without confirmation)

Always ask before making changes. Present the full list of proposed fixes and let the user approve.
