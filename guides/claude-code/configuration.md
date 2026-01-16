# Configuration

Claude Code uses `.claude` directories for configuration. There are two levels: personal (home directory) and project-level.

## Overview

| Location | Path | Scope | Shared |
|----------|------|-------|--------|
| Personal | `~/.claude/` | All your projects | No (gitignored) |
| Project | `.claude/` | This repo only | Yes (commit to git) |

Project-level settings override personal settings when both exist.

---

## Personal Configuration (`~/.claude/`)

Your personal settings, applied to all projects.

```
~/.claude/
├── settings.json       # Global settings
├── commands/           # Personal slash commands
│   └── my-command.md
├── skills/             # Personal skills
│   └── my-skill/
│       └── SKILL.md
└── ...
```

### What to Put Here

- Commands you use across all projects
- Personal preferences and workflows
- API keys and credentials (stored securely)
- Settings you don't want to share

### settings.json

Global settings file:

```json
{
  "theme": "dark",
  "model": "claude-sonnet-4-20250514",
  "permissions": {
    "allow": [],
    "deny": []
  }
}
```

---

## Project Configuration (`.claude/`)

Project-specific settings, shared with your team via git.

```
your-repo/
└── .claude/
    ├── CLAUDE.md       # Project context and memory
    ├── settings.json   # Project-specific settings
    ├── commands/       # Team commands
    │   └── deploy.md
    └── skills/         # Team skills
        └── our-skill/
            └── SKILL.md
```

### What to Put Here

- `CLAUDE.md` - Project context Claude should always know
- Team commands everyone should have
- Project-specific skills
- Shared settings and conventions

### Should You Commit `.claude/`?

**Yes, commit these:**
- `CLAUDE.md` - Project documentation
- `commands/` - Shared team commands
- `skills/` - Shared team skills
- `settings.json` - Non-sensitive project settings

**Don't commit:**
- Anything with secrets or credentials
- Personal preferences that don't apply to the team

Add to `.gitignore` if needed:
```
# Keep .claude but ignore specific files
.claude/local-settings.json
```

---

## CLAUDE.md

The most important file. Claude reads this automatically when you start a session in the project.

### Location Priority

Claude reads `CLAUDE.md` from multiple locations (all are merged):

1. `~/.claude/CLAUDE.md` - Personal, all projects
2. `./CLAUDE.md` - Project root (also works here)
3. `./.claude/CLAUDE.md` - Inside .claude directory

### What to Include

```markdown
# Project Name

Brief description of what this project does.

## Quick Start

How to install, run, and test.

## Project Structure

Key directories and what they contain.

## Conventions

- Coding style
- Naming conventions
- Testing requirements

## Key Files

Important files Claude should know about.

## Common Tasks

How to do frequent operations.

## Don't

Things Claude should avoid doing.
```

### Example for a Pipeline Project

```markdown
# ATAC-seq Pipeline

Pipeline for processing ATAC-seq data using pypiper.

## Quick Start

```bash
pip install -r requirements.txt
python pipeline.py --config config.yaml sample.fastq
```

## Structure

- `pipeline.py` - Main entry point
- `src/` - Processing modules
- `config/` - Configuration schemas
- `tests/` - Test suite

## Conventions

- Use type hints for all functions
- Config uses YAML, validated against `config/schema.yaml`
- Output files go to `output/{sample_name}/`

## Testing

```bash
pytest tests/ -v
```

## Don't

- Don't modify files in `reference/` (downloaded data)
- Don't hardcode paths; use config
```

---

## Commands Directory

Store reusable slash commands.

### Personal Commands

```
~/.claude/commands/
├── review.md           # /review - available everywhere
└── utils/
    └── cleanup.md      # /utils/cleanup
```

### Project Commands

```
.claude/commands/
├── deploy.md           # /deploy - team command
├── test/
│   ├── unit.md         # /test/unit
│   └── integration.md  # /test/integration
└── docs/
    └── update.md       # /docs/update
```

See [skills.md](skills.md) for command format details.

---

## Skills Directory

Store complex, multi-file skills.

### Personal Skills

```
~/.claude/skills/
└── my-helper/
    ├── SKILL.md
    └── reference.md
```

### Project Skills

```
.claude/skills/
└── pipeline-tools/
    ├── SKILL.md
    ├── reference.md
    └── scripts/
        └── validate.py
```

See [skills.md](skills.md) for skill format details.

---

## Settings Priority

When the same setting exists in multiple places:

1. **Project `.claude/settings.json`** (highest priority)
2. **Personal `~/.claude/settings.json`**
3. **Defaults** (lowest priority)

This lets you override personal settings for specific projects.

---

## Common Patterns

### Team Setup

For a shared project:

```
.claude/
├── CLAUDE.md              # Project context (required)
├── commands/
│   ├── lint.md            # /lint
│   ├── test.md            # /test
│   └── deploy/
│       ├── staging.md     # /deploy/staging
│       └── prod.md        # /deploy/prod
└── settings.json          # Team defaults
```

### Personal Overlay

Add personal commands that don't belong in the repo:

```
~/.claude/commands/
├── my-shortcuts.md        # Personal shortcuts
└── experiments/
    └── try-thing.md       # Stuff you're testing
```

### Multi-Repo Consistency

Put shared commands in `~/.claude/commands/` so they work across all your repos:

```
~/.claude/commands/
├── pr-summary.md          # Works in any repo
├── quick-review.md
└── explain-error.md
```

---

## Tips

- **Start with `CLAUDE.md`** - This gives the most value with least effort
- **Commit team commands** - Keeps everyone consistent
- **Keep personal stuff personal** - Don't clutter the repo with your preferences
- **Use subdirectories** - Organize commands by category
- **Document conventions** - Put coding standards in `CLAUDE.md` so Claude follows them

## See Also

- [Skills](skills.md) - Creating custom commands and skills
- [Tips & Tricks](tips-and-tricks.md) - The CLAUDE.md section
- [infrastructure/dotfiles](../../infrastructure/dotfiles/) - Example CLAUDE.md template
