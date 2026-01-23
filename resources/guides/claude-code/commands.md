# Commands

Built-in slash commands for controlling Claude Code.

## Quick Reference

| Command | Description |
|---------|-------------|
| `/help` | Show help information |
| `/clear` | Clear conversation history |
| `/compact` | Condense conversation to save context |
| `/config` | View or modify settings |
| `/cost` | Show token usage and cost |
| `/vim` | Toggle vim mode for input |
| `/tasks` | Show running background tasks |

## Session Management

### /clear

Clears the conversation history and starts fresh.

```
> /clear
```

Use when:
- Switching to a completely different task
- Context has become cluttered
- You want a fresh start

### /compact

Summarizes the conversation to reduce context usage without losing important information.

```
> /compact
```

Use when:
- You've been working for a while
- `/cost` shows high token usage
- You want to continue but free up context space

## Information Commands

### /help

Shows help information and available commands.

```
> /help
```

### /cost

Displays token usage and estimated cost for the current session.

```
> /cost

Session cost: $0.23
Tokens: 15,432 input / 3,211 output
```

### /config

View or modify Claude Code settings.

```
> /config
> /config set theme dark
```

### /tasks

Shows currently running background tasks (agents, shell commands).

```
> /tasks
```

## Input Mode

### /vim

Toggles vim-style keybindings for the input prompt.

```
> /vim
```

When enabled, you can use vim motions to edit your input.

## Command vs Skill

**Commands** control Claude Code itself:
- `/clear`, `/compact`, `/cost`, `/config`
- These are built-in and always available

**Skills** perform tasks:
- `/commit`, `/review-pr`
- These invoke Claude to do work

## Tips

- Commands are instant—they don't use API calls
- Use `/cost` periodically to track usage
- Use `/compact` proactively, not just when you hit limits
- `/clear` is useful when context becomes confusing

## See Also

- [Skills](skills.md) - Task-oriented slash commands
- [Tips & Tricks](tips-and-tricks.md) - Power user features
