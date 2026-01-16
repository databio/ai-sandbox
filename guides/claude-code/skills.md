# Skills

Skills are specialized capabilities that extend Claude Code. There are two types:

1. **Slash Commands** - Simple prompts you invoke explicitly (`/command-name`)
2. **Agent Skills** - Complex capabilities Claude can discover and use automatically

## Built-in Skills

### /commit

Generates a commit message based on your staged changes and creates the commit.

```
> /commit
```

### /review-pr

Review a pull request.

```
> /review-pr 123
> /review-pr https://github.com/org/repo/pull/123
```

---

## Custom Slash Commands

The simplest way to create reusable prompts. Each command is a single markdown file.

### Where to Put Them

| Location | Path | Scope |
|----------|------|-------|
| Personal | `~/.claude/commands/` | You, all projects |
| Project | `.claude/commands/` | Team, this repo only |

### Basic Format

Create a `.md` file with optional frontmatter:

```markdown
---
description: Brief description shown in /help
---

Your instructions for Claude here.
```

### Example: Code Review Command

File: `.claude/commands/review.md`

```markdown
---
description: Review code for common issues
---

Review the specified code for:
1. Security vulnerabilities
2. Performance issues
3. Error handling gaps
4. Code style

Provide actionable feedback organized by severity.
```

Usage:
```
> /review src/utils/parser.py
```

### Example: With Arguments

Use `$ARGUMENTS` for all args, or `$1`, `$2`, etc. for positional args.

File: `.claude/commands/fix-issue.md`

```markdown
---
description: Fix a GitHub issue
argument-hint: [issue-number]
---

Fix GitHub issue #$1.

First, fetch the issue details:
!`gh issue view $1`

Then implement a fix following our coding standards.
```

Usage:
```
> /fix-issue 42
```

### Example: With Dynamic Context

Prefix commands with `!` to execute them and include output:

File: `.claude/commands/pr-summary.md`

```markdown
---
description: Summarize current branch changes for a PR
---

## Current State

Branch: !`git branch --show-current`
Changes: !`git diff main --stat`
Recent commits: !`git log main..HEAD --oneline`

## Task

Write a PR description summarizing these changes.
```

### Organizing Commands

Use subdirectories for namespacing:

```
.claude/commands/
├── review.md           →  /review
├── deploy/
│   ├── staging.md      →  /deploy/staging
│   └── production.md   →  /deploy/production
└── test/
    └── integration.md  →  /test/integration
```

---

## Agent Skills

More powerful than slash commands. Skills are directories with a `SKILL.md` file and optional supporting files.

### Where to Put Them

| Location | Path | Scope |
|----------|------|-------|
| Personal | `~/.claude/skills/skill-name/` | You, all projects |
| Project | `.claude/skills/skill-name/` | Team, this repo only |

### Basic Structure

```
~/.claude/skills/my-skill/
├── SKILL.md          # Required: metadata + instructions
├── reference.md      # Optional: detailed docs
├── examples.md       # Optional: usage examples
└── scripts/
    └── helper.py     # Optional: utility scripts
```

### SKILL.md Format

```yaml
---
name: skill-name
description: What it does and when to use it. Include trigger keywords.
---

# Skill Title

## Instructions

Step-by-step guidance for Claude.

## Examples

Concrete usage examples.
```

### Key Metadata Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Lowercase, hyphens allowed (max 64 chars) |
| `description` | Yes | What it does + when to use (max 1024 chars) |
| `allowed-tools` | No | Restrict which tools the skill can use |
| `model` | No | Specific model to use |

### Example: Commit Helper Skill

File: `~/.claude/skills/commit-helper/SKILL.md`

```yaml
---
name: commit-helper
description: Generate clear commit messages from staged changes. Use when writing commits or when user mentions commit messages.
---

# Commit Message Helper

## Instructions

1. Run `git diff --staged` to see staged changes
2. Analyze what changed and why
3. Generate a commit message with:
   - Summary line (under 50 chars, imperative mood)
   - Blank line
   - Detailed description if needed

## Style Guide

- Use present tense: "Add feature" not "Added feature"
- Explain what and why, not how
- Reference issue numbers when applicable

## Examples

Good:
```
Add rate limiting to API endpoints

Prevents abuse by limiting requests to 100/minute per user.
Closes #234
```

Bad:
```
fixed stuff
```
```

### Example: Restricted Tool Access

Limit what tools a skill can use for safety:

File: `.claude/skills/code-analysis/SKILL.md`

```yaml
---
name: code-analysis
description: Analyze code quality and generate reports. Read-only analysis.
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Code Analysis (Read-Only)

This skill can only read files—it cannot make changes.

## Available Analyses

1. Complexity analysis
2. Documentation coverage
3. Dependency review

Generate a comprehensive report based on the requested analysis.
```

### Example: Multi-File Skill with Scripts

```
.claude/skills/data-pipeline/
├── SKILL.md
├── reference.md
└── scripts/
    ├── validate.py
    └── transform.py
```

File: `SKILL.md`

```yaml
---
name: data-pipeline
description: Process and transform data files. Use for CSV, JSON, or data manipulation tasks.
allowed-tools:
  - Read
  - Write
  - Bash(python:*)
---

# Data Pipeline

## Quick Start

Validate input data:
```bash
python scripts/validate.py input.csv
```

Transform data:
```bash
python scripts/transform.py input.csv output.csv
```

## Detailed Reference

See [reference.md](reference.md) for complete API documentation.
```

Scripts execute without loading into context, saving tokens.

---

## How Skills Are Discovered

1. **Startup** - Claude loads skill names and descriptions
2. **Request** - When you ask for something, Claude checks if a skill matches
3. **Confirmation** - Claude asks permission to use the skill
4. **Execution** - After approval, the full skill content loads

### Writing Good Descriptions

The description determines when Claude uses your skill. Be specific:

**Bad:**
```yaml
description: Helps with code
```

**Good:**
```yaml
description: Generate unit tests for Python functions using pytest. Use when writing tests, adding test coverage, or when user mentions pytest or unit tests.
```

---

## Frontmatter Reference

Works for both slash commands and skills:

| Field | Description |
|-------|-------------|
| `description` | What it does (shown in `/help`) |
| `allowed-tools` | Restrict available tools |
| `argument-hint` | Show expected args in autocomplete |
| `model` | Use specific model |
| `disable-model-invocation` | Prevent Claude from auto-invoking |

---

## Practical Examples for the Lab

### /explain-genomics

File: `.claude/commands/explain-genomics.md`

```markdown
---
description: Explain genomics code with biology context
---

Explain the following code with attention to:
1. What biological data it processes
2. The genomics concepts involved (intervals, peaks, etc.)
3. Any bioinformatics file formats (BED, BAM, FASTA, etc.)
4. Potential edge cases in genomic data

Assume the reader knows Python/R but may need genomics context.
```

### /pipeline-debug

File: `.claude/commands/pipeline-debug.md`

```markdown
---
description: Debug pipeline errors with log context
argument-hint: [log-file]
---

## Error Context

Log contents:
!`tail -100 $1`

## Task

Analyze this pipeline error:
1. Identify the root cause
2. Check for common issues (file paths, permissions, memory)
3. Suggest specific fixes
4. Note any upstream issues that may have caused this
```

### /bed-operations

File: `.claude/commands/bed-operations.md`

```markdown
---
description: Generate BED file manipulation code
---

Generate Python code to manipulate BED files.

Available tools: pybedtools, pandas, bedtools CLI

Follow these conventions:
- Validate chromosome names
- Handle 0-based coordinates correctly
- Check for overlapping intervals when relevant
- Use streaming for large files
```

---

## Tips

- **Start simple** - Begin with slash commands, graduate to skills when needed
- **Good descriptions** - Include trigger words users would naturally say
- **Test incrementally** - Try commands before adding complexity
- **Share with team** - Put project commands in `.claude/commands/`

## See Also

- [Commands](commands.md) - Built-in CLI commands
- [Agents](agents.md) - How Claude handles complex tasks
- [Workflows](workflows.md) - Common usage patterns
