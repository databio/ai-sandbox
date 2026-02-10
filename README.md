# ai-sandbox

A collection of AI resources, guides, and brainstorming space for the lab.

## What's Here

```
ai-sandbox/
├── agents/           # Agent examples
├── commands/         # Custom slash commands (organized by user)
├── skills/           # Skill definitions (organized by user)
├── workspaces/       # Multi-repo project workspaces
│   ├── workspace.py  # Setup script for workspaces
│   └── <name>/       # Individual workspace (e.g. refgenie)
│       ├── .claude/  # Shared AI config (tracked)
│       ├── plans/    # Cross-repo plans and docs
│       └── repos/    # Cloned git repos (gitignored)
└── resources/        # Guides, ideas, and references
    ├── guides/       # How-to guides for AI tools
    ├── ideas/        # Brainstorming space
    └── links.md      # Curated external links
```

## Getting Started

New to AI tools? Start here:

1. **[Getting Started](resources/guides/claude-code/getting-started.md)** - Install and configure Claude Code
2. **[Configuration](resources/guides/claude-code/configuration.md)** - `.claude/` directory and CLAUDE.md
3. **[Workflows](resources/guides/claude-code/workflows.md)** - Common ways to use it
4. **[Commands](resources/guides/claude-code/commands.md)** - Built-in slash commands
5. **[Skills](resources/guides/claude-code/skills.md)** - Task-oriented capabilities
6. **[Agents](resources/guides/claude-code/agents.md)** - How Claude handles complex tasks
7. **[Tips & Tricks](resources/guides/claude-code/tips-and-tricks.md)** - Power user features

## Contributing Ideas

Have an idea for how AI could help with lab work? Add it to `resources/ideas/proposed/` using the [idea template](resources/ideas/README.md).

## Resources

See [resources/links.md](resources/links.md) for curated external links.
