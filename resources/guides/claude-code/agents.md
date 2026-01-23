# Agents

Claude Code can spawn specialized agents to handle complex, multi-step tasks autonomously. Agents run as sub-processes with specific capabilities.

## What Are Agents?

When you ask Claude Code to do something complex, it may spawn an agent—a focused sub-process that works on a specific part of the task. Agents have access to tools and can work autonomously, returning results when done.

## Agent Types

### Explore Agent

Fast codebase exploration. Use for:
- Finding files by patterns
- Searching code for keywords
- Understanding codebase structure

```
> where are the API endpoints defined?
> find all files that handle authentication
> what's the project structure?
```

### Plan Agent

Software architecture and planning. Use for:
- Designing implementation approaches
- Breaking down complex tasks
- Identifying files that need changes

```
> plan how to add a new feature for X
> what's the best approach to refactor this?
```

### General Purpose Agent

Handles complex, multi-step tasks that don't fit other categories:
- Research tasks
- Multi-file searches
- Tasks requiring multiple rounds of exploration

### Bash Agent

Command execution specialist:
- Git operations
- Running builds and tests
- System commands

## How Agents Work

1. **Claude decides** - Based on your request, Claude may spawn an agent
2. **Agent works** - The agent uses tools autonomously to complete its task
3. **Results return** - The agent reports back with findings or results
4. **Claude summarizes** - Claude presents the results to you

## When Agents Are Used

You don't need to explicitly request agents. Claude will use them when appropriate:

- **Open-ended searches** → Explore agent
- **Complex implementation planning** → Plan agent
- **Multi-step research** → General purpose agent
- **Command sequences** → Bash agent

## Background Agents

Some agents can run in the background while you continue working:

```
> run the tests in the background and let me know when done
```

You'll be notified when background tasks complete.

## Tips

- **Be descriptive** - More context helps agents work effectively
- **Let Claude choose** - You don't need to specify which agent to use
- **Trust the process** - Agents may take a moment but work autonomously
- **Review results** - Always review what agents produce

## Example Interactions

### Exploring code
```
You: how does the config loading work?

Claude: [spawns Explore agent]
        [agent searches for config-related files]
        [agent reads relevant code]

Claude: The config loading works as follows...
```

### Planning a feature
```
You: I need to add rate limiting to the API

Claude: [spawns Plan agent]
        [agent analyzes current API structure]
        [agent identifies files to modify]

Claude: Here's my recommended approach...
        1. Add rate limit middleware in src/middleware/
        2. Update the API routes in src/routes/
        ...
```

## See Also

- [Workflows](workflows.md) - Common usage patterns
- [Commands](commands.md) - Built-in CLI commands
