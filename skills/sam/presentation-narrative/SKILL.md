---
name: presentation-narrative
version: 1.0.0
description: |
  Presentation Narrative Builder. Takes markdown report files, extracts key
  points, and proposes ranked presentation narratives aligned with an optional
  topic. Outputs step-by-step narrative outlines grounded in source material.
user-invocable: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - Task
---

# Presentation Narrative Builder

Analyze markdown reports and propose coherent presentation narratives from their key points.

## Input

The user provides:
1. **Report sources** — one of:
   - Explicit file paths: `/presentation-narrative report1.md report2.md`
   - A directory phrase: `/presentation-narrative reports in ./results/quarterly/`
   - A glob pattern: `/presentation-narrative ./reports/*.md`
2. **Topic** (optional): A phrase or sentence describing the intended presentation focus. May include audience framing.
   - Example: `/presentation-narrative ./reports/*.md --topic "sex differences in COPD airway remodeling"`
   - Example with audience: `/presentation-narrative ./reports/*.md --topic "sex differences in COPD for a department seminar audience"`
   - If audience context is included in the topic, use it to inform narrative framing, terminology level, and what to emphasize — but do not let it override the content of the source material
   - If no topic is given, narratives are proposed purely from the content

## Process

### Step 1: Resolve Input Files

Determine which markdown files to read:
- If explicit paths are given, verify they exist
- If a directory phrase is given (e.g., "report md files in ./results/"), use Glob to find `*.md` files in that directory
- If a glob pattern is given, resolve it directly
- Report the resolved file list to the user before proceeding

If no valid markdown files are found, stop and inform the user.

### Step 2: Read and Extract Key Points

For each report, read the full content and extract:

- **Findings**: Conclusions, results, quantitative claims, statistical outcomes
- **Themes**: Recurring concepts, frameworks, or questions the report addresses
- **Figures/visuals**: Any figures, tables, or visual elements referenced (these may become slides)
- **Open questions**: Limitations, gaps, unresolved issues, or future directions noted by the author
- **Methodology**: Approaches, tools, or pipelines described (when relevant to the narrative)

For each extracted point, record:
- A concise summary of the point
- The source file and approximate location (section header or context)

Do NOT filter or editorialize at this stage. Capture what the reports say.

### Step 3: Identify Cross-Report Themes

Across all extracted key points:
1. Group related points by theme or topic area
2. Note where reports **agree**, **complement** each other, or **conflict**
3. Identify any natural progressions (chronological, methodological pipeline, question → answer chains)
4. Flag points that are isolated — not connected to anything else

### Step 4: Propose Narrative Arcs

Based on the cross-report themes, propose **plausible narratives**. A narrative is plausible when:
- It connects at least 2-3 substantive key points across reports
- It has a coherent throughline (not just a list of loosely related facts)
- The source material genuinely supports the story being told

**Propose at most 3 narratives.** If the material supports more, select the 3 strongest (or most topic-aligned, if a topic is given). Mention briefly if additional weaker narratives were considered but omitted.

**Output 0 narratives if**:
- The reports are too disjoint (no meaningful connections)
- The source material is too thin to support a presentation-worthy story
- In this case, explain why and suggest what additional material might bridge the gap

**For each proposed narrative, provide**:
1. **Title**: A short, descriptive name for the narrative arc
2. **Throughline**: 1-2 sentences describing what this narrative argues or demonstrates
3. **Type**: The narrative structure (e.g., problem→solution, chronological progression, compare/contrast, methodological pipeline, question→evidence→conclusion)
4. **Strength assessment**: How well-supported is this narrative by the source material? (strong / moderate / tentative)
5. **Coverage**: Which reports contribute, and which are left out

If a **topic** was provided, rank the narratives by apparent alignment with that topic. Briefly note why each narrative is more or less aligned. Narratives with no clear connection to the topic should be listed last with a note that they diverge from the requested focus.

If no topic was given, order narratives by strength of support from strongest to weakest.

### Step 5: Outline Each Narrative

For each plausible narrative (in ranked order), produce a step-by-step presentation outline:

```
## Narrative: [Title]

**Throughline**: [1-2 sentence summary]
**Structure**: [narrative type]
**Strength**: [strong/moderate/tentative]

### Outline

1. **[Section/slide concept]**
   - Key point: [what this section communicates]
   - Source: [report file — section or context where this comes from]
   - Figure suggestion: [if applicable, a brief note on a figure/table/visual from the source that would support this point, or a simple visual concept to create — omit if no figure is relevant]
   - Notes: [any caveats, how to frame this for the audience]

2. **[Section/slide concept]**
   - Key point: ...
   - Source: ...
   - Figure suggestion: ...
   - Notes: ...

[continue for each step]

### Gaps
- [Anything the narrative needs that the source material doesn't provide]
- [Suggested additions or follow-up needed to strengthen the narrative]
```

Each step should reference specific content from the input reports. If a step requires inference or synthesis beyond what the reports explicitly state, flag it as such.

## Critical Requirements

### Grounding

- Every narrative step must trace back to specific content in the input reports
- When synthesizing across reports, label it as synthesis
- Do not invent findings, statistics, or claims not present in the sources
- If a compelling narrative step would require evidence the reports don't contain, list it as a gap rather than fabricating support

### Honest Assessment

- Do not force narratives where the material doesn't support them
- A result of "0 plausible narratives" is a valid and useful output
- Strength assessments should be honest — "tentative" is fine
- Flag when a narrative is appealing but weakly supported

### Topic Alignment

When a topic is provided:
- Rank by genuine alignment, not surface keyword overlap
- A narrative that deeply addresses one aspect of the topic outranks one that superficially mentions many aspects
- Be transparent about narratives that only partially align

### Domain Neutrality

- Do not assume any particular research domain
- Adapt terminology and framing to match whatever domain the input reports reflect
- Do not impose domain-specific presentation conventions unless the reports themselves suggest them

## Output

Write the full output to a markdown file:
- Filename: `narrative_[topic_slug].md` (slug derived from the topic, e.g., `narrative_copd_airway_remodeling.md`)
- If no topic is given: `narrative_output.md`
- Save to the current working directory unless the user specifies otherwise

The file should contain the complete output: resolved file list, key points summary, narrative proposals, and detailed outlines.

In the conversation, present only a brief summary: the resolved file count, narrative titles with strength ratings, and the output file path.
