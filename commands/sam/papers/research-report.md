# Research Report Generator

Generate a research report that synthesizes papers from a topic directory to address a specific research question.

## Input

The user will provide:
1. **Topic directory**: Path to a topic folder (e.g., `tgf_sex/` or `sex_estrogen/`)
2. **Research question**: A specific research question to address

## Process

### Step 1: Load Paper Metadata

Read `papers.yaml` from the topic directory to get:
- `paper_id` for each paper (used for citations)
- `title` for context
- `citation` for reference formatting
- `type` (research, review, commentary, etc.)

### Step 2: Read All Available Paper Content

Read all markdown files from the `md/` subdirectory of the topic. These contain the full text of converted papers including:
- Abstracts
- Methods
- Results
- Discussion sections

**Important**: Only papers with corresponding `.md` files in the `md/` directory should be used as primary sources. Papers listed in `papers.yaml` without markdown files cannot be directly cited for specific claims.

### Step 3: Analyze Papers for Relevance

For each paper, identify:
- Key findings relevant to the research question
- Specific data, statistics, or experimental results
- Methodological approaches
- Limitations acknowledged by the authors
- Areas of agreement or disagreement with other papers

### Step 4: Write the Research Report

Structure the report with the following sections:

```markdown
# [Report Title Based on Research Question]

## Executive Summary

[2-3 paragraph overview of key findings from the literature]

## Introduction

[Context for the research question, why it matters, scope of this review]

## Findings

### [Thematic Section 1]

[Synthesize findings from multiple papers, citing specific evidence]

### [Thematic Section 2]

[Continue with additional themes as needed]

## Evidence Gaps and Limitations

[Explicitly state what the available papers do NOT cover, where evidence is insufficient, or where findings conflict]

## Conclusions

[Summary of what can be confidently concluded based on the available evidence]

## References

[List papers cited using format: paper_id - Full citation]
```

## Citation Format

Use inline citations with paper_id in brackets: `[@paper_id]`

Examples:
- Single citation: `Female mice showed greater airway remodeling than males [@tam2016sex].`
- Multiple citations: `Sex differences in COPD are well-documented [@milne2024sex; @townsend2012sex].`

## Critical Requirements

### Grounding in Source Material

**YOU MUST**:
1. Only make claims that are directly supported by text in the markdown files
2. Quote or closely paraphrase specific findings, statistics, and conclusions from the papers
3. Indicate which paper(s) support each claim with proper citations
4. Distinguish between:
   - Direct experimental findings ("Tam et al. found that...")
   - Author interpretations ("The authors suggest that...")
   - Cross-paper synthesis (your own synthesis, clearly labeled)

### Acknowledging Limitations

**YOU MUST explicitly acknowledge**:
1. Questions the papers do not address
2. Areas where evidence is insufficient or conflicting
3. Limitations of the available literature for answering the research question
4. When extrapolating beyond what the papers directly state

Use phrases like:
- "The available papers do not directly address..."
- "This question cannot be answered from the current literature..."
- "Evidence on this point is limited to [X], which may not generalize to..."
- "While [paper] suggests X, this was not directly tested..."
- "The papers reviewed here do not include studies on..."

### Avoiding Hallucination

**DO NOT**:
- Invent findings, statistics, or conclusions not present in the source papers
- Cite papers for claims they do not make
- Extrapolate beyond what the evidence supports without explicit caveats
- Fill gaps with general knowledge not grounded in the provided papers
- Make claims about papers you haven't read the markdown content for

### Writing Style

Write at a level appropriate for **exploratory research in a bioinformatics research lab**:
- Assume the reader has graduate-level biology/bioinformatics background
- Use precise technical terminology without over-explaining basics
- Focus on mechanistic understanding and experimental evidence
- Highlight methodological considerations and data quality
- Identify opportunities for computational analysis or follow-up experiments
- Be direct and concise; avoid filler language

### Post-Processing

After completing the report draft, apply the `/humanizer` skill to:
- Remove signs of AI-generated writing
- Improve natural flow and readability
- Eliminate formulaic patterns

## Output

Write the completed report to a file in the topic directory:
- Default filename: `report_[short_question_slug].md`
- Or a filename specified by the user

## Example Workflow

```
User: /research-report tgf_sex/ "How do female sex hormones affect TGF-β signaling in COPD?"

1. Read tgf_sex/papers.yaml → get paper metadata
2. Read all files in tgf_sex/md/ → get paper content
3. Analyze papers for:
   - TGF-β signaling mechanisms
   - Estrogen/progesterone effects
   - COPD-specific findings
   - Sex difference data
4. Write report with:
   - Synthesis of findings
   - Specific citations to evidence
   - Explicit gaps in the literature
5. Apply /humanizer skill
6. Save to tgf_sex/report_tgf_sex_hormones.md
```
