# Claude Code Workflows

Common ways to use Claude Code for everyday tasks.

## Code Understanding

### Explore an unfamiliar codebase

```
> what does this project do?
> where is the main entry point?
> how does the authentication work?
```

### Understand a specific file

```
> explain src/utils/parser.py
> what are the main functions in this file and when would I use them?
```

## Code Review & Debugging

### Review changes before committing

```
> review my staged changes
> are there any bugs or issues in the code I modified?
```

### Debug an error

```
> I'm getting this error: [paste error]
> help me understand why this is failing
```

### Find potential issues

```
> are there any edge cases I'm missing in this function?
> review this file for potential bugs
```

## Writing Code

### Generate boilerplate

```
> create a python script that reads a BED file and filters by chromosome
> write a function to parse this config format
```

### Refactor existing code

```
> refactor this function to be more readable
> convert this R code to Python
```

### Add tests

```
> write unit tests for the parse_intervals function
> what edge cases should I test for?
```

## Documentation

### Generate docstrings

```
> add docstrings to the functions in this file
```

### Explain for documentation

```
> explain how to use this module, formatted for a README
```

## Git Operations

### Commit with context

```
> /commit
```

Claude will look at your changes and suggest a commit message.

### Understand history

```
> what changed in the last 5 commits?
> who last modified this file and why?
```

## Tips for Better Results

1. **Be specific** - "fix the bug" is worse than "fix the off-by-one error in the loop on line 42"
2. **Provide context** - mention relevant files, error messages, or expected behavior
3. **Iterate** - if the first result isn't right, refine your request
4. **Use file references** - point Claude to specific files when relevant
