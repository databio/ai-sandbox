# Workspaces

A **workspace** groups related git repositories for a single project or initiative. Instead of scattered repos, everything lives in one folder with shared documentation, plans, and AI context.

Use workspaces when you're working across multiple repos that need to stay coordinated - like a Python library ecosystem (pepkit), a web app with separate frontend/backend repos (webdev), or a research project spanning multiple tools (refgenie). The 'workspaces' folder holds the AI glue, skills, agents, etc on dropbox.

## How to use

Start vscode in a workspace folder. That gives you access to lots of AI helps.

## Quick Start

```bash
./workspace.py setup <workspace-name>
```

## workspace.toml

```toml
name = "webdev"

[[repos]]
path = "repos/frontend"
remote = "git@github.com:user/frontend.git"

[[repos]]
path = "repos/backend"
remote = "git@github.com:user/backend.git"
```

## Claude Code Configuration

Each workspace has a `.claude/` directory with shared and workspace-specific configuration:

```
workspace/.claude/
├── agents/
│   ├── core/              # Symlink to ../../.claude/agents (shared)
│   └── custom-agent.md    # Workspace-specific agents
├── skills/
│   └── core/              # Symlink to ../../.claude/skills (shared)
├── commands/              # Workspace-specific slash commands
└── settings.local.json    # Workspace-specific settings
```

**Setup script automatically creates:**
- `.claude/agents/` and `.claude/skills/` directories
- `core/` symlinks pointing to parent `.claude/` for shared agents/skills
- Preserves any existing workspace-specific configuration

**Adding custom agents/skills:**
- Shared (all workspaces): Add to `/home/nsheff/workspaces/.claude/agents/` or `skills/`
- Workspace-specific: Add directly to `workspace/.claude/agents/` or `skills/`

## Two Types of Workspaces

### Building Workspaces (Traditional)

Most workspaces are **"building" workspaces** - they group git repos to help create software:
- Output: code, commits, deployed services
- repos/ contains source code to modify
- Examples: pepkit, webdev, refgenie

### Doing Workspaces (Special)

The **assistant** workspace is a special **"doing" workspace** - designed for AI to help accomplish tasks in the world:
- Output: knowledge, actions, effects, documents (not code for git repos)
- Skills ARE the primary content
- repos/ contains only runtime infrastructure
