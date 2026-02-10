---
name: changelog-update
description: Update a project's changelog based on git changes between master and dev branches. Follows Keep a Changelog and Semantic Versioning standards. Use when preparing releases or documenting changes.
user_invocable: true
---

# Changelog Update Skill

Update a project's changelog based on git changes between master and dev branches.

## When to Use

Use this skill when:
- Preparing a release and need to document changes
- The user asks to "update the changelog" or "write changelog entries"
- Merging dev branch to master and need release notes

## Standards Reference

### Keep a Changelog (https://keepachangelog.com)

Changelogs are for humans, not machines. Key principles:
- Group changes by type: Added, Changed, Deprecated, Removed, Fixed, Security
- Most recent version first
- Each version gets its own section
- Link versions to diffs when possible

### Semantic Versioning (https://semver.org)

Version format: MAJOR.MINOR.PATCH

- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality, backwards compatible
- **PATCH**: Bug fixes, backwards compatible

### Date Format

Always use ISO 8601: **YYYY-MM-DD** (e.g., 2026-01-26)

## Workflow

### Step 1: Find the Changelog

My convention is to have a separate repository where I keep documentation for several related projects.
So you first need to locate the changelog, often in separate docs repository. Search for it:

```bash
# Check common locations
find .. \( -name "changelog.md" -o -name "CHANGELOG.md" \) -not -path "*/node_modules/*" 2>/dev/null
```

Many will be named 'changelog.md' -- identify is in a folder that matches the project you want to update.

### Step 2: Read Existing Style

Read the changelog to understand the project's conventions:
- How are entries formatted? (bullets, paragraphs, categories)
- What level of detail is typical?
- Are entries grouped by type (Added/Changed/Fixed)?
- What tense is used? (past tense is standard)

Most projects use simple bullet points without category groupings.

### Step 3: Get Version Number

Check the project's version file:

```bash
# Common locations
grep -E "^version|^__version__" */_version.py setup.py pyproject.toml 2>/dev/null
```

### Step 4: Analyze Git Changes

Get commits between master and dev:

```bash
# Summary of commits
git log master..dev --oneline

# Key changes (filter for significant commits)
git log master..dev --oneline | grep -iE "add|implement|fix|remove|change|update|new|major"

# Files changed
git diff master..dev --stat | tail -20

# New files added
git diff master..dev --name-status | grep "^A" | head -20
```

### Step 5: Write the Entry

Create a new version section at the top of the changelog (after the header).

**Format:**
```markdown
## [X.Y.Z] - YYYY-MM-DD

- First change description
- Second change description
- Bug fix for something specific
```

**Writing Guidelines:**
- Start each item with a verb (Add, Fix, Update, Remove, Implement)
- Be specific but concise
- Focus on user-facing changes
- Group related changes into single bullets when appropriate
- Don't include internal refactoring unless it affects users
- Mention breaking changes

### Step 6: Do NOT Commit

Only update the changelog file. Do not create commits - let the user review and commit.

## Example Entry

```markdown
## [0.10.0] - 2026-01-26

- Add new CLI with subcommands for admin, config, and store operations
- Implement FASTA DRS endpoints for GA4GH compliance
- Fix endpoint path mismatch in client (`/list/collection`)
- Update frontend dependencies for security fixes
- Remove deprecated legacy API endpoints
```

## Common Pitfalls

- **Don't copy commit messages verbatim** - Summarize and group related changes
- **Don't include every commit** - Focus on user-visible changes
- **Don't forget the date** - Always include release date in ISO format
- **Don't mix tenses** - Use past tense consistently ("Added" not "Add")
- **Don't be too technical** - Write for users, not developers
