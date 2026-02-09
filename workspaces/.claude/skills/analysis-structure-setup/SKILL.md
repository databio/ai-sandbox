---
name: analysis-structure-setup
description: Scaffold a new analysis project with the standard structure (CLAUDE.md, src/, input/, output/, .gitignore). Creates all directories, the CLAUDE.md template with analysis rules, README, and .gitignore. Use when starting a new data analysis project.
---

# Analysis Structure Setup

Scaffold a new analysis project with the standard structure for Claude-assisted data analysis.

## What This Creates

```
project/
├── CLAUDE.md              # Project context + analysis rules
├── README.md              # Human overview
├── .gitignore             # Ignores input/, output/, .env
├── src/                   # Analysis code goes here
├── input/                 # Raw data (immutable, may be symlink)
└── output/                # Generated artifacts (regenerable)
    ├── data/              # Computed intermediates
    ├── plots/             # Generated figures
    └── reports/           # Reports referencing plots
```

## Steps

1. **Ask the user** for:
   - Project name
   - Brief description (1-2 sentences)
   - Data sources (API, files, database)
   - Key analysis questions
   - Language (Python or R)
   - Whether `input/` or `output/` should be symlinks (and to where)

2. **Create the directory structure:**
   ```
   mkdir -p src input output/data output/plots output/reports
   ```
   If the user specified symlink targets for input/ or output/, create symlinks instead of directories.

3. **Write CLAUDE.md** from this template (fill in user's answers):

```markdown
# [Project Name]

[Description]

## Data Sources

- [Data sources from user]

## Key Questions

- [Questions from user]

## Structure

- `input/` — Raw data (immutable)
- `output/data/` — Computed intermediates
- `output/plots/` — Generated figures
- `output/reports/` — Analysis reports
- `src/` — Analysis code

## How to Run

[Entry point — e.g., `python src/main.py` or `Rscript src/main.R`]

## Analysis Rules

**All quantitative information must appear in programmatically-generated plots, never in hand-written text.**

- NEVER write tables with numbers in reports — use bar charts or heatmaps
- NEVER quote specific values (correlations, p-values, means) in prose
- ALL quantitative claims must be visible in a referenced plot
- Reports reference plots by path: `![Caption](output/plots/filename.png)`
- Plots must be self-documenting: embed values, context lines, sample sizes
- Keep interpretive text minimal and qualitative — let plots speak

**Why:** AI fabricates numbers in text. Plots generated from computed data cannot.

## Code Conventions

- `input/` is immutable — never write to it
- `output/` is fully regenerable — delete and re-run
- All analysis code lives in `src/`
- Both `input/` and `output/` are gitignored (may be symlinks)
- Save intermediate data to `output/data/` before plotting from it
```

4. **Write README.md:**

```markdown
# [Project Name]

[Description]

## Setup

[Any environment setup, dependencies, credentials]

## How to Run

[Entry point and instructions]

## Structure

- `src/` — Analysis code
- `input/` — Raw data (not tracked in git)
- `output/` — Generated results (not tracked in git)
  - `data/` — Intermediate computed data
  - `plots/` — Figures
  - `reports/` — Analysis reports
```

5. **Write .gitignore:**

```gitignore
# Data (may be symlinks, always large)
input/
output/

# Credentials
.env
*.env

# Python
.venv/
__pycache__/
*.pyc

# R
.Rhistory
.RData
.Rproj.user/

# OS
.DS_Store
```

6. **Language-specific starter files:**

   **Python:** Create `src/__init__.py` (empty) and `src/main.py` with a basic skeleton:
   ```python
   """[Project Name] analysis."""

   # Entry point — run with: python src/main.py
   if __name__ == "__main__":
       pass  # Add analysis steps here
   ```

   **R:** Create `src/main.R` with a basic skeleton:
   ```r
   # [Project Name] analysis
   # Entry point — run with: Rscript src/main.R
   ```

   **For non-trivial projects**, suggest splitting `src/` into modules by concern:
   ```
   src/
   ├── __init__.py
   ├── main.py          # Entry point — orchestrates steps
   ├── data.py          # Data fetching and loading
   ├── compute.py       # Calculations and statistics
   └── plotting.py      # All plot-generating functions
   ```
   Only create these if the analysis is complex enough to warrant it — a single `main.py` is fine for small projects.

7. **If this is a git repo**, initialize it:
   ```
   git init && git add -A && git commit -m "Initial analysis project structure"
   ```
   Only if the user confirms — don't assume.

## Important

- Do NOT create example data or placeholder plots
- Do NOT add dependencies to requirements.txt unless the user specifies them
- Keep everything minimal — the user will fill in real content
