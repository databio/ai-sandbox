# Emil Kowalski Animation Principles -- Audit Reference

Quick-lookup reference organized by audit category. All values, thresholds, and rules derived from Emil Kowalski's published work, blog posts, open-source libraries (Sonner, Vaul), and his course Animations on the Web.

---

## 1. Purpose & Frequency

### The Fundamental Question

> "The goal is not to animate for animation's sake, it's to build great user interfaces."

Animation is justified only when it serves a purpose: explaining functionality, providing feedback, preventing confusion, or occasional delight.

### Frequency Rule

| Interaction Frequency | Animation Approach |
|---|---|
| Rare (monthly) | Delightful morphing animations welcome |
| Occasional (daily) | Subtle, fast animations (180-250ms) |
| Frequent (100s/day) | No animation or instant transitions |
| Keyboard-initiated | **Never animate** |

### Context Table

| Context | Recommendation |
|---|---|
| Keyboard shortcuts | No animation |
| High-frequency tool | Minimal or none |
| Daily-use feature | Fast, subtle (180-250ms) |
| Onboarding / first-time | Delightful animations welcome |
| Marketing / landing page | Full creative expression |
| Banking / serious UI | Minimal, functional motion |
| Playful brand | Bouncy, elastic easing appropriate |

**Red flags:** animations on every keystroke, animated responses to rapid-fire actions, decorative animation with no UX purpose.

---

## 2. Easing

### Core Principle

> "Easing is the most important part of any animation."

### When to Use Each Type

| Easing | Use For | Avoid For |
|---|---|---|
| **ease-out** | Enter/exit animations, user-initiated interactions (dropdowns, modals, toasts), marketing intros | -- |
| **ease-in-out** | Elements moving/morphing while remaining on screen, timeline animations | Enter/exit animations |
| **ease** | Hover effects, color/opacity transitions, elegant subtle motion | Primary UI transitions |
| **ease-in** | **AVOID for UI work** -- makes interfaces feel sluggish | Everything in UI |
| **linear** | Marquees, hold-to-delete progress, 3D rotations, visualizing time passage | UI transitions |

### Custom Curves -- Always Preferred

Built-in CSS easing curves are "usually not strong enough." Custom curves feel more energetic.

**Known Emil curves:**
- Vaul drawer: `cubic-bezier(0.32, 0.72, 0, 1)` (iOS sheet feel, sourced from Ionic)
- Clip-path reveal: `cubic-bezier(0.77, 0, 0.175, 1)`

**Red flags:** `ease-in` on UI transitions, only built-in easings used (no custom `cubic-bezier`), `linear` on UI state changes.

**Good signs:** custom `cubic-bezier()` values, `ease-out` as default, `ease` for hover states.

---

## 3. Duration & Timing

### Core Rule

> "UI animations should generally stay under 300ms."

### Duration Reference

| Component / Use Case | Duration | Easing |
|---|---|---|
| **General UI ceiling** | < 300ms | -- |
| **Sweet spot** | 200-300ms | -- |
| Responsive-feeling UI | 180ms | ease-out |
| Button active scale | 150-160ms | ease-out |
| Tooltip (subsequent) | 0ms | instant |
| Toast transform (Sonner) | 400ms | ease |
| Drawer transition (Vaul) | 500ms | cubic-bezier(0.32, 0.72, 0, 1) |
| Hold-to-delete overlay | 2000ms | linear |
| Hold-to-delete release | 200ms | ease-out |
| Scroll velocity timeout | 100ms | -- |
| Toast auto-dismiss | 4000ms | -- |
| **Absolute max for UI** | < 1000ms | (unless marketing/illustrative) |

### Principles

- Pressing/holding: slow enough for user confirmation
- Release transitions: prioritize snappiness
- Remove animation entirely for 10+/day interactions
- First tooltip: delay + animation; subsequent: instant

**Red flags:** UI animations > 500ms, no variation in duration across component types, same duration for everything.

---

## 4. Transform Patterns

### Scaling Rules

- **Never animate from `scale(0)`** -- looks unnatural, as if materializing from nothing
- Start from **`scale(0.9)` or higher** (e.g., 0.93) combined with opacity
- Button active state: **`scale(0.97)`** -- 3% reduction for tactile feedback
- Stacked toast scale reduction: `0.05 * index`

### Transform Origin

- CSS default (`center`) is **almost always wrong** for dropdowns/popovers
- Dropdowns: `transform-origin: top center` or `bottom center` based on position
- Radix UI: `--radix-dropdown-menu-content-transform-origin`
- Radix popover: `--radix-popover-content-transform-origin`
- Base UI: `--transform-origin`
- **Origin-aware animations** = animate from the element's physical trigger location

### Translation

- `translateY(100%)` -- percentage relative to element's own dimensions (not parent)
- Sonner uses `translateY()` with percentages for variable-height toasts

**Red flags:** `scale(0)` in any animation, default `transform-origin: center` on dropdowns/popovers, no button press feedback.

**Good signs:** scale starting >= 0.9, origin-aware dropdowns, `scale(0.97)` on button `:active`.

---

## 5. Performance

### Hardware Acceleration Rules

**Only animate:**
- `transform` (translate, scale, rotate)
- `opacity`
- `clip-path` (hardware-accelerated, no layout recalc)

**Never animate (triggers layout):**
- `padding`, `margin`
- `width`, `height`
- `top`, `left`, `right`, `bottom`
- `border-width`, `font-size`

### Additional Rules

- CSS transitions and WAAPI stay smooth regardless of main thread load
- `requestAnimationFrame` is NOT hardware-accelerated
- Direct `element.style.transform` over CSS variable updates for drag/scroll (CSS variables cause expensive recalc across all children)
- Framer Motion shared layout animations can drop frames under load -- prefer CSS for critical animations
- Target: 60fps minimum

**Red flags:** animating `height`/`width`/`margin`/`padding`, CSS variable updates in tight loops with many children, `requestAnimationFrame` for animations that could use CSS/WAAPI.

---

## 6. Interruptibility

### Core Rule

> "Animations should be cancellable mid-transition, allowing smooth state changes when users interrupt actions."

### CSS Transitions vs Keyframes

- **CSS transitions**: can be interrupted and retargeted mid-flight
- **CSS keyframe animations**: cannot be interrupted -- new state triggers jump to final position
- **Framer Motion**: supports interruption natively

### What to Check

- State-change animations (hover, active, open/close) should use CSS transitions, not keyframes
- Rapid clicking/interaction should produce smooth blending, not queued animations
- Toast/notification stacking should retarget smoothly when new items arrive

**Red flags:** `@keyframes` used for interactive state changes (hover, toggle, open/close), animations that queue up on rapid interaction.

**Good signs:** CSS `transition` on interactive elements, Framer Motion for complex orchestration, smooth behavior on rapid click testing.

---

## 7. Gesture Patterns

*Applicable when project has drag, swipe, or touch interactions.*

### Velocity-Based Dismissal

```javascript
const velocity = Math.abs(swipeAmount) / timeTaken;
if (velocity > 0.11) { dismiss(); }
```
- Use velocity (not just distance) -- allows quick flicks to dismiss
- Threshold: `0.11` (Vaul's tuned value)

### Damping

- "The more you drag, the less the drawer will move" past boundaries
- Things slow down before stopping (physics-based resistance)

### Pointer Capture

- `setPointerCapture()` during drags -- tracking continues beyond element boundaries

### Scroll-to-Drag Protection

- 100ms velocity timeout after reaching scroll top prevents accidental drawer closure from scroll momentum

### Multi-Touch

- Ignore subsequent touches after initial one until release -- prevents position jumping

### Snap Points

- Momentum-based: allow skipping snap points on forceful flicks
- `closeThreshold`: 0-1 fraction determining when to close

**Red flags:** distance-only dismissal thresholds, no damping on boundary drag, no pointer capture, drag breaks when pointer leaves element.

---

## 8. Micro-Interactions

### Button Press Feedback

```css
button:active {
  transform: scale(0.97);
  transition: transform 150ms ease-out;
}
```

### Tooltip Delay Pattern

1. First tooltip: show with delay + animation (prevents accidental activation)
2. Subsequent tooltips (while group is active): instant display, 0ms transition
3. Use `data-instant` attribute to target subsequent state

### Blur Bridging

- `filter: blur(2px)` masks imperfections during state transitions
- Bridges visual gaps between old and new content

### Background Scaling (Drawer)

- `scaleBackground` prop animates body wrapper
- Border radius scales proportionally (40% drag = 60% max radius)

### Invisible Quality Details

- `document.hidden` -- pause timers when tab inactive
- `:after` pseudo-elements bridge hover gaps between stacked elements
- Visual Viewport API for keyboard handling: `visualViewportHeight - OFFSET`

**Red flags:** no button press feedback, tooltips with same delay every time, no consideration for tab visibility.

**Good signs:** scale on `:active`, tooltip delay pattern with instant subsequent, blur used during complex transitions.

---

## 9. Accessibility

### Non-Negotiable Requirements

- **`prefers-reduced-motion`** media query must be respected
- Implement reduced or no animations for vestibular motion disorders
- This is mandatory, not optional

### Implementation

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

Or per-component:
```css
@media (prefers-reduced-motion: reduce) {
  .animated-element {
    animation: none;
    transition: none;
  }
}
```

### Decorative Elements

- `aria-hidden="true"` on purely decorative animated overlays (e.g., hold-to-delete progress overlay)

**Red flags:** no `prefers-reduced-motion` anywhere in codebase, animated decorative elements without `aria-hidden`, motion-heavy UI with no reduced-motion alternative.

---

## 10. Motion Gaps

### What Are Motion Gaps?

Elements that appear/disappear via conditional rendering (`{show && <Component />}`) without any enter/exit animation. They "snap" in and out, breaking the otherwise animated feel of the interface.

### Common Locations

- Conditional renders: `{isOpen && <Dropdown />}`
- Route transitions with no animation
- List item additions/removals
- Toast/notification appearances without AnimatePresence or equivalent
- Modal/dialog open/close without transition
- Tooltip show/hide

### What to Look For

- `{condition && <JSX>}` or ternary renders without wrapping animation (AnimatePresence, Transition, CSSTransition)
- CSS `display: none` toggling without transition
- `visibility: hidden` toggling without opacity fade
- Dynamic list rendering (`map()`) without enter/exit animations on items

### The Fix Pattern

Wrap conditional renders in animation containers:
- React + Framer Motion: `<AnimatePresence>{show && <motion.div>}</AnimatePresence>`
- Vue: `<Transition>` component
- Svelte: `transition:` directive
- CSS-only: animate opacity/transform, use `visibility` with transition delay

**Red flags:** conditional renders of UI elements with no animation wrapper, `display: none` toggling, list items that pop in/out.

---

## Spring Animation Reference

### Recommended Config

```javascript
const springConfig = { stiffness: 300, damping: 30 };
```

### When to Use Springs

- Mouse/cursor-following decorative animations
- Interactive elements with natural physics feel
- Interpolating value changes

### When NOT to Use Springs

- Functional components needing predictable timing
- High-frequency interactions

---

## Clip-Path Reference

### Why Clip-Path

- Hardware-accelerated
- No layout recalculation
- No extra DOM elements needed

### Patterns

**Image reveal (bottom-to-top):**
```css
.reveal {
  clip-path: inset(0 0 100% 0);
  animation: reveal 1s forwards cubic-bezier(0.77, 0, 0.175, 1);
}
@keyframes reveal {
  to { clip-path: inset(0 0 0 0); }
}
```

**Tab transitions:** duplicate tab list, clip overlay to reveal active tab only.

**Hold-to-delete:** `inset(0px 100% 0px 0px)` → `inset(0px 0px 0px 0px)`.
