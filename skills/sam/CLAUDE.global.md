# User Preferences

## Plans

Always save plans and implementation logs to the `plans/` folder at the project root using the naming convention `YYYY-MM-DD-<short-description>.md`.

Every plan file must start with a YAML front matter header:

---
date: YYYY-MM-DD
status: draft | in-progress | complete | abandoned
description: Short one-line summary of the plan
---

- When exiting plan mode, ask the user if they want to save the plan.
- When the user provides a plan directly, save it to `plans/` before starting work.
- After completing a multi-step implementation, append or write an implementation log to the same file and update the `status` field accordingly.

## Plan Comprehension Quiz

When exiting plan mode OR when loading a saved plan for implementation, quiz the user before executing — but only if the plan involves non-trivial design decisions. Skip the quiz for simple plans where you (the AI) didn't make significant architectural, methodological, or design choices (e.g., rename a variable, run a standard command, straightforward single-file edits).

### How it works

1. After saving the plan (or after loading an existing plan at the start of a new session), pause before implementing.
2. Identify 2-3 design decisions, methodological choices, or structural aspects of the plan that you consider important — places where you made a judgment call, chose one approach over another, or where understanding the "why" matters for the plan to succeed.
3. Ask the user 2-3 short questions about those aspects. Questions should be:
   - **Higher-order**: about *why*, not *what*. Test understanding of reasoning, tradeoffs, or consequences — not recall of implementation details or syntax.
   - **Plain language**: no jargon or textbook vocabulary. Ask about the plan in concrete terms.
   - **Answerable in 1-3 sentences**: not essay questions. A correct answer demonstrates the user understands the decision, not that they can recite the plan back.
   - **Grounded in the specific plan**: not generic CS/bio/stats trivia. Every question should reference something concrete in the plan.
4. If the user can't answer a question, adapt your response to how close they seem: if they're nearly there, reframe the question or give a small nudge; if they have no foundation for the concept, explain it directly — struggling without a foothold isn't learning. Then ask a brief follow-up to confirm understanding. Do not proceed with implementation until the user demonstrates they understand the key decisions.

### Example question patterns (adapt to the domain and plan)

- "Why did we choose [approach A] instead of [approach B] for this part?"
- "What's the riskiest assumption in this plan — the thing most likely to be wrong?"
- "If [specific component/step] fails or produces unexpected output, what breaks downstream?"
- "What statistical test or method does [step N] use, and what question does it answer?"
- "What biological/domain assumption are we relying on in [step N]?"
- "Which decision in this plan would be hardest to change later?"
- "What does [step N] need to be true about the input data to work correctly?"

### Skipping the quiz

The user can request to skip the quiz, but must articulate a concrete reason tied to a real external commitment (e.g., "I promised my lab this would be ready by tomorrow," "this is blocking a collaborator"). Accept the reason and proceed if it references a specific obligation or deadline. Do not accept vague reasons like "I'm tired" or "just skip it" — push back gently and offer to make the quiz shorter (1 question) rather than skipping entirely. The point is: if there's no real urgency, doing the quiz is always better, even a reduced version. If the user is genuinely in a rush, they'll have a real reason and it'll be obvious.

### Why this rule exists

The user is building higher-order judgment across domains (bioinformatics, data science, systems development) while using AI for execution. Cheap iteration removes the natural forcing function for understanding design decisions. This quiz re-introduces that forcing function — the goal is learning and calibration, not gatekeeping.

