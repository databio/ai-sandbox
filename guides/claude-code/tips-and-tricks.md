# Tips & Tricks

Power user features and lesser-known functionality.

## Slash Commands

Type `/` to see available commands:

| Command | Description |
|---------|-------------|
| `/help` | Show help information |
| `/clear` | Clear conversation history |
| `/compact` | Condense conversation to save context |
| `/config` | View or modify settings |
| `/cost` | Show token usage and cost for session |
| `/commit` | Generate a commit message and commit |
| `/review` | Review code changes |
| `/vim` | Toggle vim mode for input |

## Keyboard Shortcuts

- `Ctrl+C` - Cancel current operation
- `Ctrl+D` - Exit Claude Code
- `Up/Down` - Navigate command history
- `Tab` - Autocomplete file paths

## The CLAUDE.md File

Create a `CLAUDE.md` in your project root to give Claude persistent context:

```markdown
# Project Context

This is a Python pipeline for processing ATAC-seq data.

## Key Files
- `pipeline.py` - Main entry point
- `config.yaml` - Configuration schema

## Conventions
- Use type hints for all functions
- Follow PEP 8
- Tests go in `tests/` directory

## Common Commands
- `python pipeline.py --config config.yaml` to run
- `pytest tests/` to test
```

Claude reads this automatically when you start a session in that directory.

## Context Management

### Check your context usage

```
/cost
```

### Compact when running low

```
/compact
```

This summarizes the conversation to free up context space.

### Start fresh

```
/clear
```

## Working with Files

### Reference files explicitly

```
> look at src/parser.py and explain the parse function
```

### Include file contents in your question

```bash
claude "explain this" -f script.py
```

## Non-Interactive Mode

### Pipe input

```bash
echo "explain this error: $(cat error.log)" | claude
```

### One-shot questions

```bash
claude "convert this json to yaml" -f config.json > config.yaml
```

## MCP Servers

Claude Code can connect to MCP (Model Context Protocol) servers for extended capabilities like database access, API integrations, etc. See [infrastructure/mcp-servers](../../infrastructure/mcp-servers/) for examples.

## Useful Settings

View settings with `/config` or edit `~/.claude/settings.json`:

```json
{
  "theme": "dark",
  "model": "claude-sonnet-4-20250514"
}
```

## Performance Tips

1. **Be specific about file paths** - helps Claude find things faster
2. **Use `/compact` proactively** - don't wait until you hit limits
3. **Start new sessions for unrelated tasks** - keeps context focused
