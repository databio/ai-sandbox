---
name: discuss-report
version: 1.0.0
description: |
  Discuss Report. Interactive discussion of a research report with grounded,
  evidence-based responses. Loads source papers on-demand and maintains
  epistemic honesty throughout the conversation.
user-invocable: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - WebSearch
---

# Discuss Report

Interactive discussion of a research report with grounded, evidence-based responses.

## Input

The user provides:
- A path to a report markdown file (e.g., `tgf_sex/report_tgf_sex_differences.md`)
- Optionally, a specific question or topic to start the discussion

## Setup

1. **Read the report** to understand its content, structure, and conclusions
2. **Extract all citations** from the report (format: `[@paper_id]` or `[@paper_id; @paper_id2]`)
3. **Identify the topic directory** from the report path (e.g., `tgf_sex/` from `tgf_sex/report_tgf_sex_differences.md`)
4. **Read papers.yaml** from the topic directory to map paper_ids to full citations
5. **Note which papers are available** by checking the `md/` subdirectory

Do NOT preemptively load all paper markdown files. Load them on-demand during discussion.

## Discussion Guidelines

### Loading Papers On-Demand

When the user asks about a specific claim, finding, or paper:

1. Identify which paper(s) are relevant to the question
2. Load the corresponding markdown file(s) from the `md/` directory **before responding**
3. Base your response on the actual content of the paper, not on summaries in the report
4. If a paper is cited in the report but no markdown file exists, state this limitation

### Epistemic Honesty

**YOU MUST:**

1. **Distinguish evidence strength:**
   - "Paper X directly demonstrates..." (experimental finding)
   - "Paper X suggests..." (author interpretation)
   - "The report synthesizes... but this is an inference across papers"
   - "This is plausible but not directly tested in the available papers"

2. **Acknowledge uncertainty:**
   - If the papers don't address a question, say so
   - If findings conflict, present both sides without forced resolution
   - If evidence is indirect or from different contexts (different species, tissues, diseases), note this
   - Use "I don't know" or "the papers don't say" when appropriate

3. **Resist pressure to be specific:**
   - If asked for quantitative details and the papers don't give numbers, don't invent them
   - If asked for mechanisms and the papers only show correlations, say that
   - If asked to predict outcomes and the evidence doesn't support prediction, decline

4. **Correct the report if needed:**
   - If you find the report overstated a finding, say so
   - If a citation doesn't actually support the claim, flag it
   - The report may contain synthesis errors; the source papers are ground truth

### What NOT to Do

**DO NOT:**

- Answer questions about paper content without loading the paper first
- Invent specific numbers, mechanisms, or conclusions not in the sources
- Force agreement between conflicting findings
- Extrapolate beyond what the evidence supports to give a "complete" answer
- Pretend to know things the papers don't address
- Defend report claims that aren't supported when you check the sources
- Fill gaps with general knowledge from training data

### Response Format

For substantive questions, structure responses as:

1. **Direct answer** (if the evidence supports one) or acknowledgment of uncertainty
2. **Evidence basis** - which paper(s) support this, with specific details
3. **Caveats** - limitations, conflicting evidence, or gaps
4. **What's unknown** - if relevant, what the papers don't address

Keep responses focused and avoid padding with tangential information.

## Session Continuity

Throughout the discussion:
- Keep track of which papers you've loaded
- Reference specific sections/findings from loaded papers
- If asked about something in a paper you haven't loaded yet, load it first
- Build on previous answers in the conversation, but always verify claims against sources when challenged

## Google Scholar Labs Query Suggestions

When the user asks for help finding additional literature, or when discussion reveals evidence gaps, you can suggest queries for [Google Scholar Labs](https://scholar.google.com/scholar_labs/search).

### About Scholar Labs

Scholar Labs is an AI-powered search that analyzes complex research questions by breaking them into key topics, aspects, and relationships. Unlike traditional keyword search, it:
- Evaluates results for relevance to your specific question
- Provides brief explanations of how each paper answers your query
- Supports follow-up questions to explore nuances

### When to Suggest Queries

- User explicitly asks for search suggestions
- Discussion identifies a gap the current papers don't address
- User wants to validate or extend findings from the report
- A question arises that requires literature beyond the current collection

### Crafting Effective Queries

Scholar Labs works best with **detailed research questions**, not keyword strings. Examples of effective query styles:

- **Method/technique questions:** "Has anyone used single molecule footprinting to examine transcription factor binding in human cells?"
- **Comparative questions:** "Are hydrogen powered cars, compared to electric / internal combustion engine cars, really better for the environment?"
- **Clinical/practice questions:** "What is the standard of care for intraductal papilloma without atypia? When is surgical excision recommended, and when can it be managed conservatively?"
- **Time-bounded requests:** "Find papers from the past 2 years about how to determine whether an abstractive summary generated by an LLM is grounded."

### Query Suggestion Format

When suggesting queries, provide:

1. **The query** - a complete, detailed research question
2. **What it addresses** - which gap or uncertainty from the discussion this would help fill
