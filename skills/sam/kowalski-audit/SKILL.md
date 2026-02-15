---
name: kowalski-audit
version: 1.0.0
description: |
  Evaluate any web project's animations, transitions, and interaction patterns
  against Emil Kowalski's design principles. Outputs a structured audit report
  with file:line references, severity-rated findings, and concrete fix suggestions.
user-invocable: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - Task
  - AskUserQuestion
---

# Kowalski Animation Audit

Evaluate a web project's animation and interaction quality against Emil Kowalski's principles. Produces a structured report with concrete findings, code references, and prioritized recommendations.

## Before You Start

Load the principles reference for this audit:

```
Read ~/.claude/skills/kowalski-audit/references/principles.md
```

Keep this reference available throughout the audit. Cite specific principles when reporting findings.

## Step 1: Project Reconnaissance

Understand what you're auditing before searching for animation code.

### 1a. Detect Tech Stack

Search for configuration files to identify the framework and tooling:

```
Glob: **/package.json, **/composer.json, **/Gemfile, **/Cargo.toml
```

From `package.json`, identify:
- **Framework**: React, Next.js, Svelte, Vue, Nuxt, Astro, vanilla JS
- **Animation libraries**: `framer-motion`, `motion`, `@react-spring/web`, `gsap`, `animejs`, `popmotion`, `@formkit/auto-animate`
- **UI libraries**: `@radix-ui/*`, `@headlessui/*`, `@mui/*`, `shadcn` (check for `components.json`), `@mantine/*`
- **CSS approach**: Tailwind (`tailwindcss`), CSS Modules, styled-components, emotion

### 1b. Detect Project Type

Scan for clues about what kind of project this is:

- Marketing/landing page: few routes, heavy on visuals, hero sections
- SaaS/dashboard: many routes, data tables, forms, settings pages
- Mobile-first app: viewport meta, touch handlers, bottom sheets
- Component library: Storybook config, many exported components

This matters because animation expectations differ by context (see Frequency Rule in principles).

### 1c. Report Context

Note your findings -- they'll frame the rest of the audit. Example:

> **Stack**: Next.js 14 + Tailwind + Framer Motion + Radix UI
> **Type**: SaaS dashboard with marketing landing page
> **Animation library**: Framer Motion (motion components detected)

---

## Step 2: Animation Code Discovery

Use **parallel Task agents** for large projects, or direct Glob/Grep for smaller ones. Search for all animation-related code across the project.

### 2a. CSS Animation Patterns

Search for these patterns across `.css`, `.scss`, `.module.css`, and inline in `.tsx`/`.jsx`/`.vue`/`.svelte` files:

```
Grep: transition\s*:
Grep: transition-property|transition-duration|transition-timing-function
Grep: @keyframes
Grep: animation\s*:
Grep: animation-name|animation-duration
Grep: transform\s*:
Grep: clip-path
Grep: will-change
```

### 2b. JavaScript Animation Patterns

```
Grep: motion\.|<motion\.|from\s*['"]framer-motion|from\s*['"]motion
Grep: useSpring|useTransform|useMotionValue|useAnimate|useAnimation
Grep: AnimatePresence
Grep: animate\(|\.animate\(
Grep: requestAnimationFrame
Grep: gsap\.|TweenMax|TweenLite|TimelineMax|TimelineLite
Grep: useSpring.*react-spring|from\s*['"]@react-spring
```

### 2c. Accessibility Patterns

```
Grep: prefers-reduced-motion
Grep: aria-hidden
```

### 2d. Conditional Rendering (Motion Gap Candidates)

```
Grep: \{.*&&\s*<      (JSX conditional render)
Grep: v-if|v-show     (Vue)
Grep: \{#if            (Svelte)
```

### 2e. Catalog Findings

Build an internal list of every animation-related code location with:
- File path and line number
- What type of animation (CSS transition, keyframe, Framer Motion, etc.)
- What it animates (which properties)
- Duration and easing values if present
- Context (what component/interaction is this for?)

---

## Step 3: Evaluate Against Principles

Work through each of the 10 audit categories below. For each, reference the principles.md file for specific thresholds, values, and rules.

### Category 1: Purpose & Frequency

**Question**: Is each animation justified? Does the animation weight match how often the interaction occurs?

Check:
- Are there heavy animations on high-frequency interactions (should be minimal/none)?
- Are keyboard-triggered actions animated (should never be)?
- Are there decorative animations with no UX purpose?
- Is the project type considered? (SaaS dashboard vs marketing page have different bars)

### Category 2: Easing

**Question**: Are easing choices intentional and appropriate?

Check:
- Is `ease-in` used on UI transitions? (red flag)
- Are only built-in CSS easings used with no custom `cubic-bezier()`? (missed opportunity)
- Is `ease-out` the default for enter/exit animations?
- Is `linear` used only for continuous motion (marquees, progress)?
- Are custom curves used for important animations?

### Category 3: Duration & Timing

**Question**: Are durations appropriate for each component type?

Check:
- Are UI animations under 300ms? (hard ceiling for most interactions)
- Is the sweet spot of 200-300ms used for general transitions?
- Are there animations over 500ms that aren't drawers, toasts, or marketing?
- Is there duration variation across component types? (same duration everywhere = not tuned)
- Button feedback: 150-160ms?
- Toast/notification: ~400ms?

### Category 4: Transform Patterns

**Question**: Are transforms used correctly?

Check:
- Any `scale(0)` or `scale: 0` in animations? (should start from 0.9+)
- Is `transform-origin` set on dropdowns/popovers? (default `center` is wrong)
- Do buttons have `:active` scale feedback (~0.97)?
- Are Radix/Base UI transform-origin CSS variables used if those libraries are present?

### Category 5: Performance

**Question**: Are only GPU-friendly properties animated?

Check:
- Any animations on `height`, `width`, `margin`, `padding`, `top`, `left`? (layout thrashing)
- Is `transform` and `opacity` used instead?
- CSS variable updates in tight loops with many DOM children?
- `requestAnimationFrame` used where CSS transitions or WAAPI would work?
- `clip-path` used for reveal animations? (good -- hardware-accelerated)

### Category 6: Interruptibility

**Question**: Can animations be interrupted mid-flight?

Check:
- Are `@keyframes` used for interactive state changes (hover, toggle, open/close)? (should be CSS transitions)
- Do Framer Motion animations handle interruption (default: yes, but check `AnimatePresence mode="wait"` which blocks)?
- Would rapid clicking produce smooth blending or queued/janky animations?

### Category 7: Gesture Patterns

*Skip if no drag/swipe/touch interactions exist.*

**Question**: Do gesture interactions feel physics-based and robust?

Check:
- Swipe dismissal: uses velocity threshold (not just distance)?
- Boundary drag: has damping/resistance?
- `setPointerCapture()` used during drags?
- Multi-touch handling: subsequent touches ignored?
- Scroll-to-drag protection: velocity timeout?

### Category 8: Micro-Interactions

**Question**: Are the small details polished?

Check:
- Button press: `scale(0.97)` on `:active` with ~150ms ease-out?
- Tooltip delay: first appearance delayed, subsequent instant?
- Tab visibility: timers paused when `document.hidden`?
- Hover gaps: pseudo-elements bridging gaps between interactive elements?
- Blur used during complex state transitions?

### Category 9: Accessibility

**Question**: Is animation accessible?

Check:
- `prefers-reduced-motion` media query present in the codebase?
- Is it applied globally OR per-component for significant animations?
- Decorative animated elements have `aria-hidden="true"`?
- Is there ANY reduced-motion consideration at all? (absence = critical finding)

### Category 10: Motion Gaps

**Question**: Are there conditional renders that snap in/out without animation?

Check:
- `{condition && <Component>}` without AnimatePresence or transition wrapper
- `v-if` without `<Transition>` (Vue)
- `{#if}` without `transition:` (Svelte)
- `display: none` toggling without opacity/transform transition
- Dynamic list items (`map()`) without enter/exit animation
- Route changes without page transitions
- Modal/dialog/dropdown open-close without transition

Focus on **visible, user-facing** elements. Not every conditional render needs animation -- only those where the snap is jarring or breaks the otherwise animated feel.

---

## Step 4: Generate Report

Output the audit report in the following format. Use **file:line** references for every finding. Be specific and actionable.

### Report Template

```markdown
# Animation Audit: [Project Name]

**Date**: YYYY-MM-DD
**Stack**: [framework + animation lib + CSS approach]
**Project Type**: [SaaS / marketing / mobile app / component library / etc.]
**Audited Against**: Emil Kowalski's animation & interaction design principles

---

## Summary

[2-3 sentence overall assessment. Is this project animated well, poorly, or not at all? What's the biggest strength and biggest gap?]

### Scores

| Category | Score | Notes |
|---|---|---|
| Purpose & Frequency | [pass / needs-work / fail] | [one-liner] |
| Easing | [pass / needs-work / fail] | [one-liner] |
| Duration & Timing | [pass / needs-work / fail] | [one-liner] |
| Transform Patterns | [pass / needs-work / fail] | [one-liner] |
| Performance | [pass / needs-work / fail] | [one-liner] |
| Interruptibility | [pass / needs-work / fail] | [one-liner] |
| Gesture Patterns | [pass / needs-work / fail / n/a] | [one-liner] |
| Micro-Interactions | [pass / needs-work / fail] | [one-liner] |
| Accessibility | [pass / needs-work / fail] | [one-liner] |
| Motion Gaps | [pass / needs-work / fail] | [one-liner] |

---

## What's Working

[List good patterns found. Each with file:line reference and why it's good.]

- **[pattern name]** (`path/to/file.tsx:42`) — [why this is good, which principle it follows]

---

## Issues

### Critical

[Issues that actively harm UX or accessibility. Must fix.]

#### [Issue title]
- **Location**: `path/to/file.tsx:42`
- **Problem**: [what's wrong]
- **Principle**: [which Emil principle this violates]
- **Fix**: [concrete suggestion, with code if helpful]

### Important

[Issues that noticeably degrade animation quality. Should fix.]

(same format as Critical)

### Minor

[Missed opportunities or polish items. Nice to fix.]

(same format as Critical)

---

## Motion Gaps

[Conditional renders or state changes that should animate but don't.]

| Location | Element | Current Behavior | Suggested Animation |
|---|---|---|---|
| `file:line` | [what element] | [snaps in/out] | [suggested approach] |

---

## Recommendations

[Prioritized list of improvements. Most impactful first.]

1. **[recommendation]** — [why, what it improves, effort estimate: low/medium/high]
2. ...

---

*Audited using Emil Kowalski's animation principles. Reference: emilkowal.ski, animations.dev*
```

### Severity Definitions

- **Critical**: Actively harms UX or violates accessibility requirements. Includes: missing `prefers-reduced-motion` entirely, animating layout properties causing visible jank, `ease-in` on primary UI transitions, animations on every keystroke.

- **Important**: Noticeably degrades animation quality or misses key principles. Includes: `scale(0)` animations, wrong `transform-origin` on dropdowns, UI animations over 500ms, no custom easing curves, keyframes used for interruptible state changes.

- **Minor**: Polish items and missed opportunities. Includes: no button press feedback, no tooltip delay pattern, same duration used everywhere, no blur bridging on complex transitions.

---

## Special Cases

### Project Has No Animations

If the project has essentially no animation code:

1. Skip categories 2-8 (no code to evaluate)
2. Score Purpose & Frequency as "n/a" with note
3. Score Accessibility as "pass" (no motion = no motion risk) unless there are jarring snaps
4. Focus the report entirely on **Motion Gaps** -- identify the top 5-10 places where animation would most improve the UX
5. Provide a "Getting Started" section with:
   - Recommended animation library for their stack
   - The 3 highest-impact animations to add first
   - Starter code examples following Emil's principles

### Very Large Project

For projects with 100+ components:

1. Use **Task agents** to parallelize Step 2 searches (one agent per search category)
2. Focus evaluation on user-facing routes/pages, not internal utilities
3. Sample rather than exhaustively audit -- note in the report that it's a sampled audit
4. Ask the user if they want to focus on specific areas

### Component Library

For component/design system projects:

1. Evaluate default animation props/configs
2. Check if the library exposes animation customization to consumers
3. Check if `prefers-reduced-motion` is handled at the library level
4. Focus on whether defaults follow Emil's principles
