---
name: ai-execution-report
version: 1.0.0
description: |
  Generate an AI self-assessment and execution details report documenting
  Claude as primary executor, the full multi-session collaboration history,
  and an honest disclosure of what the human directed, constrained, and
  corrected. Can be embedded in a deliverable or written as a standalone file.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Task
---

# AI Execution Report Generator

Generate an AI self-assessment and execution details report that discloses Claude's role in producing work. This can be **embedded in a deliverable** (report section, README section) or written as a **standalone markdown file** -- ask the user which format they want if unclear.

## When to Use

Call this skill (`/ai-execution-report`) when:
- A report, codebase, or deliverable was substantially produced with Claude's help
- The user wants to disclose AI involvement to collaborators, PIs, or reviewers
- The user asks for a "self-assessment", "execution details", "AI disclosure", "session log", or "how this was made"
- A multi-session project is being wrapped up and needs documentation of the full arc
- The user wants an internal record of the collaboration for their own reference

## Output Formats

**Embedded section:** A markdown section (typically `##` heading) appended to an existing document. Adapt heading levels to match the target document.

**Standalone file:** A full markdown document saved to:
- `plans/YYYY-MM-DD-ai-execution-report-<short-description>.md` (default), or
- Any path the user specifies

Ask the user which format and location they prefer before writing.

## Information Gathering

Before writing, reconstruct the full collaboration history. Use these sources:

### 1. Session transcripts
Check for prior session transcripts in the project's Claude data directory:
```
~/.claude/projects/<project-path>/*.jsonl
```
Read these to extract: what the user asked, what Claude did, what corrections were made, and what constraints were imposed. Use the Task tool with a general-purpose agent for reading large transcript files.

### 2. Git history
Run `git log --oneline` to understand the timeline of changes and who committed what.

### 3. File modification dates
Use `ls -lt` on key directories to understand the order files were created.

### 4. Current conversation context
The current session's context contains the most recent and detailed interaction history.

### 5. User's own notes
Check for any existing documentation the user has written about the project (READMEs, plan files, comments in code).

## Required Sections

### 1. Attribution

A brief statement establishing:
- Claude's model version (e.g., "Claude Opus 4.6 via Claude Code CLI")
- Claude's role (primary executor, code writer, analyst, etc.)
- The human's role (director, supervisor, domain expert, etc.)
- That all substantive decisions were reviewed/approved by the human

Keep this to 2-3 sentences. Be factual, not promotional.

### 2. Collaboration History

A **chronological narrative** of how the project was built across all sessions. For each session or phase:

- **When** it happened (date or date range)
- **What the user asked for** (paraphrase their actual requests)
- **What Claude did** (concrete actions: files created, analyses run, code written)
- **What corrections or redirections occurred** (be specific)

Guidelines:
- Use past tense, third person ("The analyst asked...", "Claude implemented...")
- Name specific files, functions, and tools
- Don't skip sessions where things went wrong -- those are important for honesty
- Group by session or logical phase, whichever reads better
- Keep each session to a short paragraph unless it was particularly complex

### 3. What the Human Asked Claude to Do

A bullet list summarizing the categories of work Claude performed. Be concrete -- "Write R code" is too vague; "Write 9 Rmd analysis files implementing sex-stratified GWAS visualization and comparison" is specific.

Categories to cover as applicable:
- Code writing (which files, what kind)
- Analysis execution (what was run)
- Data processing (what was read, transformed, cross-referenced)
- Writing and drafting (reports, documentation)
- Verification (what was checked)

### 4. What the Human Constrained or Corrected

This is the most important section for honesty. Organize into three categories:

**Constraints imposed from the start:**
Rules the human established before or early in the work. These are design decisions, not corrections.

**Corrections during execution:**
Times the human corrected Claude's misunderstanding, wrong assumption, or incorrect implementation. Be specific about what was wrong and how it was fixed.

**Things Claude was not permitted to do:**
Explicit boundaries -- actions, files, or decisions that were off-limits. Include both stated restrictions and implicit ones (e.g., Claude was never given permission to push to remote).

### 5. Self-Assessment

An honest evaluation with two parts:

**Strengths:**
What went well in the collaboration. Be specific -- "efficient code generation" is weak; "systematic data extraction from 25 RDS files with programmatic cross-verification prevented numerical errors" is strong.

**Weaknesses and limitations:**
- Misunderstandings that required correction
- Wrong assumptions Claude made
- API or tool errors
- Places where Claude's knowledge was insufficient
- Analytical limitations (e.g., biological interpretations not verified by domain expert)

**Data fidelity statement** (when applicable):
If the deliverable contains data or numbers, state how they were sourced and verified. Explicitly note any missing data rather than glossing over gaps.

### 6. Closing Attribution Line

A single italic line at the very end:

```markdown
*This [report/document/analysis] was generated on [date] using [model name] (Anthropic) via Claude Code CLI, under the direction of [the human analyst / the development team / etc.].*
```

## Writing Guidelines

### Tone
- Professional and matter-of-fact, not self-deprecating or boastful
- Write as a transparent disclosure, not a performance review
- The reader should come away understanding exactly what was human judgment vs AI execution

### Honesty standards
- Never minimize corrections or errors -- they demonstrate human oversight working correctly
- Don't inflate Claude's contribution ("Claude designed the study" when the human designed it and Claude implemented it)
- Don't use hedge words to soften failures ("Claude's initial approach was slightly different" when Claude got it wrong)
- If Claude doesn't know something (e.g., number of prior sessions), say so rather than guessing

### Specificity
- Name files, functions, tools, dates
- Quote or closely paraphrase the user's actual requests when possible
- Quantify: "9 Rmd files", "25 RDS files", "3 corrections"
- Reference specific sections of the deliverable when discussing what they cover

### What NOT to include
- Percentage contribution tables (those belong in a different format)
- Numerical ratings (1-10 scale)
- Token counts, API costs, or other technical metrics
- Promotional language about Claude's capabilities
- Apologies or excessive self-criticism

## After Generating

1. Show the user what was written (or point them to the file/section)
2. Ask if any characterizations need adjustment -- especially the constraints/corrections section, since the user may recall interactions differently
3. If the collaboration history spans sessions you don't have transcripts for, note the gaps and ask the user to fill in
