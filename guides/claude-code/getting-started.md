# Getting Started with Claude Code

Claude Code is Anthropic's official CLI tool for working with Claude directly in your terminal.

## Installation

```bash
npm install -g @anthropic-ai/claude-code
```

Or with Homebrew:

```bash
brew install claude-code
```

## Authentication

Run Claude Code for the first time and it will prompt you to authenticate:

```bash
claude
```

This opens a browser window to log in with your Anthropic account. Your API key is stored securely in your system keychain.

### Using an API Key Directly

If you prefer to use an API key:

```bash
export ANTHROPIC_API_KEY=your-key-here
claude
```

## Basic Usage

### Start an interactive session

```bash
claude
```

### Ask a one-off question

```bash
claude "explain what this script does" -f script.py
```

### Start in a specific directory

```bash
claude --cwd /path/to/project
```

## First Things to Try

1. **Explore a codebase**: Open Claude Code in a repo and ask "what does this project do?"
2. **Get help with an error**: Paste an error message and ask for help debugging
3. **Review code**: Ask Claude to review a file for potential issues
4. **Write a script**: Describe what you need and let Claude write it

## Configuration

Claude Code stores settings in `~/.claude/`. You can create a `CLAUDE.md` file in any project directory to give Claude context about that project (see [infrastructure/dotfiles](../../infrastructure/dotfiles/) for examples).

## Next Steps

- [Workflows](workflows.md) - Common usage patterns
- [Tips & Tricks](tips-and-tricks.md) - Power user features
