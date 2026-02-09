---
name: implement
description: Take a complete implementation plan and implement it.
argument-hint: [plan path]
---

Take a complete implementation plan and implement it.

## When to Use

- User has a completed plan ready for implementation
- User invokes `/implement <plan-path>`

## Process

1. Read `./CLAUDE.md` and `./progress.md` (if they exist) to understand context for this plan.
2. Read the plan file specified in `$ARGUMENTS`.
3. Implement the plan by executing each step in the plan systematically.
4. Log the session: Write a 1-3 sentence summary with today's date to `progress.md` in the project root. Format: `YYYY-MM-DD  Description of what was accomplished.`
5. Mark plan complete by running `python3 <skill-dir>/mark_completed.py <plan-file>`.
6. Check for any remaining items in TaskList before finishing.
