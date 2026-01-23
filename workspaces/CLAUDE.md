# Workspaces System

This repository manages **workspaces** - logical groupings of related git repositories that I work on together.

## What is a Workspace?

A **workspace** is a folder that groups together multiple git repositories I'm actively working on as part of a single project or initiative.

The workspace provides:

- **Logical groupings**. A single place to navigate to when working on the project that spans repos, with shared context and documentation and plans
- **Individual repos** stay independent in `~/code/` with their own git history
- A human-written journal tracking progress and decisions

Think of workspaces as "project folders" that tie together multiple repos I'm actively working on together, plus the ancillary notes and plans that don't belong in any single repo.

## Structure of the /workspaces folder and workspaces it contains

```
~/workspaces/                    # Container for workspaces
├── workspace-name/
│   ├── workspace.toml           # Manifest of entries in this workspace
│   ├── CLAUDE.md                # Context for this specific workspace
│   ├── journal.md               # Human-written work log and notes
│   ├── plans/                   # Cross-repo plans, designs, notes
│   └── repos/                   # Actual repos/folders (gitignored/dropbox-ignored)
│       ├── repo1/               # Git clone
│       ├── repo2/               # Git clone
│       └── dropbox-notes/       # Symlink to ~/Dropbox/...
```

## Key Concepts

- **One workspace = one folder** containing related projects I'm working on together
- **repos/ is gitignored** - the actual contents are NOT tracked here
- **Workspace metadata IS tracked** - workspace.toml, CLAUDE.md, plans/, and any documentation
- **Entries can be git repos OR local folders** - git repos are cloned, local folders (Dropbox, Google Drive, etc.) are symlinked
- **Entries can appear in multiple workspaces** - they're just clones or symlinks

## Journals

Each workspace can have a `journal.md` file - a human-written work log that tracks progress, decisions, and notes over time. Journals are dated entries (newest first) that capture:

- What I'm currently working on and why
- Progress updates and accomplishments
- Open questions and next steps
- Technical notes and discoveries
- TODO items specific to this workspace

Journals have YAML frontmatter with `workspace`, `modified`, and `created` fields. They provide context that helps when returning to a workspace after time away, and give AI assistants insight into recent work and priorities.


## Setup on a New Machine

1. Clone this repo: `git clone <url> ~/workspaces`
2. Run setup: `./workspace.py setup <workspace-name>`
   - This reads `workspace.toml` and sets up all entries into `repos/`
   - Requires Python 3.11+ (uses `tomllib`)
   - Example: `./workspace.py setup intervals`

The script will:
- Create the `repos/` directory if it doesn't exist
- Clone each entry with a `remote` configured
- Symlink each entry with a `source` configured
- Skip entries that already exist locally
- **Create `.claude/` symlinks for skill/agent propagation** (see below)
- Show progress with ✓/✗ indicators

## Checking for Uncommitted Changes

Run `./workspace.py gitcheck` to scan workspaces for git repos with uncommitted or unpushed changes:
- `./workspace.py gitcheck` - check all workspaces (or current workspace if run from within one)
- `./workspace.py gitcheck <name>` - check specific workspace
- `./workspace.py gitcheck -f` - fetch from remotes first

If run from a directory with a `repos/` folder, it auto-detects the workspace and checks only that one.

## Skill and Agent Propagation

The setup script symlinks parent `.claude/skills/` and `.claude/agents/` into each workspace as `core/` subdirectories. This is why you must run the setup script even for empty workspaces.

## File Location Rules for Claude

**CRITICAL:** When creating `progress.md`, `plans/`, or workspace documentation:

✅ **Write to workspace root:**
```
~/workspaces/refgenie/progress.md
~/workspaces/refgenie/plans/my_plan.md
```

❌ **NEVER write to repos/ subdirectories:**
```
~/workspaces/refgenie/repos/gtars/progress.md      # WRONG
~/workspaces/refgenie/repos/refget/plans/foo.md   # WRONG
```

**Why?** Individual repos are independent git repositories. Workspace-level files like `progress.md` and `plans/` belong in the workspace root so they:
- Stay with the workspace, not scattered across repos
- Don't pollute repo git history
- Provide a single place for cross-repo documentation

**Exception:** Repo-specific documentation (README.md, CLAUDE.md) stays in repos.

## workspace.toml Format

```toml
name = "workspace-name"
description = "Optional description of what this workspace is for"

# Git repos (cloned)
[[repos]]
path = "repos/repo-name"
remote = "git@github.com:username/repo-name.git"

# Local folders (symlinked) - Dropbox, Google Drive, etc.
[[repos]]
path = "repos/dropbox-notes"
source = "~/Dropbox/Projects/notes"

[[repos]]
path = "repos/gdrive-docs"
source = "~/Google Drive/My Drive/Projects/docs"

# Entries without remote or source (documentation only)
[[repos]]
path = "repos/local-only-repo"
```

**Entry types:**
- `remote` = git clone from URL
- `source` = symlink to local folder (Dropbox, Google Drive, iCloud, OneDrive, or any local path)
- Neither = skipped by setup script, tracked for documentation only

## Creating a New Workspace (Instructions for Claude)

1. **Create the workspace folder** with a `workspace.toml`:
   ```toml
   name = "workspace-name"
   description = "What this workspace is for"

   [[repos]]
   path = "repos/repo-name"
   remote = "git@github.com:org/repo-name.git"

   [[repos]]
   path = "repos/notes"
   source = "~/Dropbox/Projects/notes"
   ```

   Use `repos = []` if no repos yet.

2. **Run the setup script**: `./workspace.py setup <workspace-name>`

The setup script creates `CLAUDE.md` (from template), `plans/`, `repos/`, and `.claude/` symlinks. Edit the generated `CLAUDE.md` to add workspace-specific context.

---

## Two Types of Workspaces

### Building Workspaces (Traditional)

Most workspaces are **"building" workspaces** - they group git repos to help create software:
- **Purpose:** Create code, software, deployable artifacts
- **Output:** Git commits, repos, deployed services
- **repos/ contains:** Source code to modify
- **Examples:** pepkit, webdev, refgenie, intervals

### Doing Workspaces (Special)

The **assistant** workspace is a special **"doing" workspace** - designed for AI to help accomplish tasks in the world, not build software:
- **Purpose:** Accomplish tasks, produce effects
- **Output:** Knowledge, actions, documents, API updates (not code for git)
- **Skills ARE the primary content**
- **repos/ contains:** Only runtime infrastructure

---

## The Assistant Workspace

**If you're working from `~/workspaces/` (this root folder), you most likely want the `assistant` workspace.**

The assistant workspace is for "doing" - having AI help accomplish tasks:
- Planning your day (`/today`)
- Browser automation (filling forms, web navigation)
- API operations (Todoist tasks, calendar management)
- Drafting and editing documents
- Research and information synthesis

**To work in assistant mode:**
```bash
cd ~/workspaces/assistant
```
---

## Admin (This Root Folder)

The `workspaces/` root is for **workspace infrastructure**, not daily work:
- `workspace.py` - Unified CLI for setup, check, and link commands
- `.claude/skills/` - Shared development skills (propagated to all workspaces)
- `CLAUDE.md` - This documentation about how workspaces work
