---
name: tailwind-ui-styling
version: 1.0.0
description: |
  Utility-first UI styling guidelines using Tailwind CSS, DaisyUI, and
  shadcn-inspired patterns. Enforces class-based styling, semantic color
  tokens, and consistent component composition. Framework-agnostic.
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Task
---

# UI Styling Guidelines

Follow these rules when writing UI code. These apply regardless of frontend framework.

## Core Principles

- **Utility-first**: Use Tailwind CSS utility classes for all styling. No scoped/module CSS for layout or color.
- **No inline styles**: Never use `style` attributes unless something is physically impossible with classes (e.g., dynamic `width` from a JS variable). If you must use an inline style, leave a brief comment explaining why.
- **Reuse class patterns**: Before writing a new combination of utilities, check if the same pattern already exists in the codebase. Copy it exactly.
- **Semantic tokens over raw values**: Use DaisyUI's semantic color names (`primary`, `base-300`, `error`) instead of Tailwind's raw palette (`blue-500`, `gray-200`, `red-600`).

## CSS Stack

- **Tailwind CSS** (v4+) for utilities
- **DaisyUI** (v5+) for component classes and semantic color/size tokens
- **@tailwindcss/typography** for prose/markdown content
- **Lucide** for icons (use the appropriate framework binding: `lucide-svelte`, `lucide-react`, etc.)

### Setup (app.css / global entry)

```css
@import 'tailwindcss';

@plugin "@tailwindcss/typography";
@plugin "daisyui" {
  themes: light --default, dark --prefersdark;
}
```

Keep the global `@layer base` block minimal. Only put true resets or attribute-based cursors there.

## Color System

Use DaisyUI semantic tokens everywhere. Never hard-code hex/rgb values.

| Purpose | Classes |
|---------|---------|
| Primary action | `bg-primary`, `text-primary`, `border-primary` |
| Primary surface | `bg-primary/5`, `bg-primary/10` |
| Default surface | `bg-base-100` |
| Elevated surface | `bg-base-200` |
| Subtle borders/dividers | `border-base-300` |
| Default text | `text-base-content` |
| Muted text | `text-base-content/60` |
| Success state | `text-success`, `bg-success`, `badge-success` |
| Warning state | `text-warning`, `bg-warning`, `badge-warning` |
| Error/danger state | `text-error`, `bg-error`, `badge-error` |
| Informational | `text-info`, `bg-info`, `badge-info` |

Use opacity modifiers (`/5`, `/10`, `/30`, `/40`, `/60`) for subtle tints rather than picking a different color.

## Component Classes (DaisyUI)

Prefer DaisyUI's component classes as the base, then extend with Tailwind utilities.

| Component | Base class | Variants |
|-----------|-----------|----------|
| Buttons | `btn` | `btn-primary`, `btn-secondary`, `btn-ghost`, `btn-error`, `btn-sm`, `btn-lg` |
| Cards | `card` | `card-body`, `card-compact` |
| Badges | `badge` | `badge-primary`, `badge-ghost`, `badge-error`, `badge-xs`, `badge-sm` |
| Inputs | `input` | `input-bordered`, `input-sm`, `input-error` |
| Modals | `modal`, `modal-box` | `modal-action` |
| Tooltips | `tooltip` | `tooltip-top`, `tooltip-bottom` |
| Dropdowns | `dropdown` | `dropdown-end`, `dropdown-content` |

## Layout Patterns

### Full-screen app shell

```html
<div class="flex h-screen overflow-hidden">
  <!-- sidebar -->
  <div class="flex-1 flex flex-col min-w-0">
    <main class="flex-1 overflow-auto p-4 md:p-6">
      <!-- content -->
    </main>
  </div>
</div>
```

### Flex row with centered items

```html
<div class="flex items-center gap-2">
```

### Flex column with spacing

```html
<div class="flex flex-col gap-3">
```

### Truncated text in flex containers

Always add `min-w-0` to the flex parent and `truncate` to the text element:

```html
<div class="flex-1 min-w-0">
  <span class="truncate">Long text here</span>
</div>
```

### Responsive padding

```html
<div class="p-4 md:p-6">
```

## Typography

- **Sizes**: `text-xs`, `text-sm`, `text-base`, `text-lg`, `text-xl`
- **Weight**: `font-medium` for labels/headings, `font-semibold` for emphasis
- **Line clamping**: `line-clamp-1`, `line-clamp-2` for multi-line truncation
- **Tabular numbers**: `tabular-nums` for numeric columns so digits align
- **Prose content**: Wrap rendered markdown/HTML in `prose` class

## Spacing Conventions

Stick to a consistent subset of the Tailwind spacing scale:

| Use case | Values |
|----------|--------|
| Tight inner padding | `p-2`, `px-2 py-1` |
| Standard card/section padding | `p-3`, `p-4` |
| Page-level padding | `p-4 md:p-6` |
| Gap between items in a list | `gap-1`, `gap-1.5`, `gap-2` |
| Gap between sections | `gap-3`, `gap-4`, `gap-6` |
| Margin for separation | `mt-2`, `mb-1`, `ml-auto` |

Avoid arbitrary spacing values (`p-[13px]`) unless matching a strict design spec.

## Component Styling Patterns

### Variant maps

Define variant-to-class mappings as lookup objects, not long ternary chains:

```typescript
const variantClass: Record<string, string> = {
  primary: 'btn-primary',
  secondary: 'btn-secondary',
  ghost: 'btn-ghost',
  danger: 'btn-error',
};

const sizeClass: Record<string, string> = {
  sm: 'btn-sm',
  md: '',
  lg: 'btn-lg',
};
```

Then compose:

```html
<button class="btn {variantClass[variant]} {sizeClass[size]} {className}">
```

### Conditional classes

Use ternary expressions for binary states:

```html
<div class="card border {selected ? 'bg-primary/5 border-primary/40' : 'bg-base-100 border-base-300'} transition-colors">
```

### Interactive states

Always pair hover/focus effects with `transition-colors` or `transition-shadow`:

```html
<div class="hover:shadow-md transition-shadow cursor-pointer">
<a class="hover:bg-base-300 transition-colors rounded-lg px-3 py-2">
```

### Compact vs. default density

Use a boolean prop to toggle padding:

```html
<div class="card-body {compact ? 'p-3' : 'p-4'}">
```

### Status/priority color maps

```typescript
const priorityColors: Record<string, string> = {
  urgent: 'text-error',
  high: 'text-warning',
  medium: 'text-base-content/40',
  low: 'text-base-content/30',
};
```

## Borders and Shadows

- Default card/container: `border border-base-300 shadow-sm`
- Hover elevation: `hover:shadow-md transition-shadow`
- Selected state: `border-primary/40 bg-primary/5`
- Dashed/suggested: `border-dashed border-primary/40`
- Dividers: `border-t border-base-300` or `border-b border-base-300`
- Rounded corners: `rounded-lg` for cards/containers, `rounded-full` for pills/avatars

## Responsive Design

- Mobile-first: write the base style for small screens, add `md:` for tablet+
- Hide/show: `hidden md:flex`, `md:hidden`
- Responsive padding: `p-4 md:p-6`, `pb-20 md:pb-6` (extra bottom padding on mobile for floating navs)

## Dark Mode

Handled automatically by DaisyUI themes. Do not write manual `dark:` variants. Set the theme via `data-theme` attribute on `<html>`:

```javascript
document.documentElement.setAttribute('data-theme', theme);
```

Store preference in `localStorage`.

## What to Avoid

- **Raw color classes** (`text-blue-500`, `bg-gray-100`) -- use semantic tokens
- **Inline styles** for anything achievable with utilities
- **Scoped/module CSS** for layout, colors, or spacing
- **`@apply`** -- compose classes in markup instead
- **Arbitrary values** (`w-[347px]`) unless matching a design spec
- **Custom CSS classes** when a Tailwind utility or DaisyUI class exists
- **Duplicating class patterns** -- extract to a component if the same cluster of classes appears 3+ times
