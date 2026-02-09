---
name: diagnose-and-plan
description: Diagnose a problem, and write a plan to solve it
argument-hint: [problem-to-diagnose]
---

# Diagnose and Plan

Diagnose a problem and write a plan file to solve it. This skill emphasizes understanding the root cause before proposing solutions.

## When to Use

- Bug or issue needs investigation before fixing
- Problem is not well understood
- Need to figure out what's wrong before planning the fix

## Process

### 1. Review Context

Read `./CLAUDE.md` and `./progress.md` to understand:
- Project overview and structure
- Recent work and context
- No need to maintain backwards compatibility

### 2. Diagnose the Issue

Figure out what is wrong:
- Investigate the problem thoroughly
- Identify root causes
- Understand the scope of the issue

### 3. Write the Plan

Write your plan to `./plans/<project>_<descriptive-name>_plan_v1.md` in the **workspace root** (NOT inside repos/).

Plan structure:

```markdown
# Implementation plan for <BRIEF DESCRIPTION>

## The issue

<PROBLEM SUMMARY - what you diagnosed>

## Files to read for context

<LIST OF SPECIFIC FILES TO READ>

## Implementation Steps

<NUMBERED LIST OF SPECIFIC, CONCRETE STEPS>

## Backwards compatibility

Do not maintain backwards compatibility. This is developmental software. We are eliminating old code, not preserving it.

## Cleanup

Once completed, move this plan to `plans/completed/`.
```

### 4. Register the Plan

Run: `python3 <skill-dir>/../plan/add_plan.py <plan-file>`

## Important Rules

1. **Write to file, not chat.** Don't output the plan in the conversation.
2. **Don't implement.** This skill writes plans only. Do not change any other files.
3. **No time estimates.** Never include how long things will take.
4. **Diagnose first.** The value of this skill is in understanding the problem before solving it.

## After Writing

Confirm to the user:
- The filename and path where the plan was written
- What you diagnosed as the root cause
- A one-sentence summary of the proposed solution
