# Photo Explorer Design System

A comprehensive design system with centralized tokens for colors, spacing, typography, and other design primitives. This ensures consistency across the application and makes theming easier.

## Table of Contents

- [Installation](#installation)
- [Tokens](#tokens)
  - [Colors](#colors)
  - [Spacing](#spacing)
  - [Typography](#typography)
  - [Borders](#borders)
  - [Shadows](#shadows)
  - [Transitions](#transitions)
  - [Z-Index](#z-index)
  - [Breakpoints](#breakpoints)
- [Utilities](#utilities)
- [Usage Examples](#usage-examples)
- [Tailwind Integration](#tailwind-integration)
- [Migration Guide](#migration-guide)

## Installation

The design system is already available in the project. Import tokens and utilities from `$lib/design`:

```typescript
import { colors, spacing, typography } from '$lib/design';
import { getColor, buildButtonStyles } from '$lib/design';
```

## Tokens

### Colors

The design system includes a comprehensive color palette with primary, semantic, and neutral colors.

#### Primary Colors

```typescript
import { colors } from '$lib/design';

colors.primary[600]; // '#0284c7' - Main brand color
colors.primary[700]; // '#0369a1' - Hover state
```

#### Semantic Colors

```typescript
colors.success[500]; // '#10b981' - Success green
colors.error[500]; // '#ef4444' - Error red
colors.warning[500]; // '#f59e0b' - Warning amber
colors.info[500]; // '#3b82f6' - Info blue
```

#### Neutral Grays

```typescript
colors.gray[50]; // '#f9fafb' - Lightest gray
colors.gray[500]; // '#6b7280' - Medium gray
colors.gray[900]; // '#111827' - Darkest gray
```

#### Semantic UI Colors

Pre-defined colors for common use cases:

```typescript
colors.background.primary; // '#ffffff'
colors.background.secondary; // '#f9fafb'
colors.text.primary; // '#111827'
colors.text.muted; // '#6b7280'
colors.border.default; // '#e5e7eb'
```

### Spacing

Consistent spacing scale based on 4px increments:

```typescript
import { spacing } from '$lib/design';

spacing.xs; // '0.25rem' (4px)
spacing.sm; // '0.5rem' (8px)
spacing.md; // '0.75rem' (12px)
spacing.lg; // '1rem' (16px)
spacing.xl; // '1.5rem' (24px)
spacing['2xl']; // '2rem' (32px)
spacing['3xl']; // '3rem' (48px)
```

### Typography

Font families, sizes, weights, and line heights:

```typescript
import { typography } from '$lib/design';

// Font families
typography.fontFamily.sans;
typography.fontFamily.mono;

// Font sizes
typography.fontSize.xs; // '0.75rem' (12px)
typography.fontSize.base; // '1rem' (16px)
typography.fontSize.xl; // '1.25rem' (20px)

// Font weights
typography.fontWeight.normal; // '400'
typography.fontWeight.semibold; // '600'
typography.fontWeight.bold; // '700'

// Line heights
typography.lineHeight.tight; // '1.25'
typography.lineHeight.normal; // '1.5'
```

### Borders

Border radius and width tokens:

```typescript
import { borders } from '$lib/design';

borders.radius.sm; // '0.1875rem' (3px)
borders.radius.md; // '0.25rem' (4px)
borders.radius.lg; // '0.375rem' (6px)
borders.radius.xl; // '0.5rem' (8px)
borders.radius.full; // '9999px'

borders.width.thin; // '1px'
borders.width.medium; // '2px'
```

### Shadows

Box shadow tokens for elevation:

```typescript
import { shadows } from '$lib/design';

shadows.sm; // Small shadow
shadows.md; // Medium shadow
shadows.lg; // Large shadow
shadows.xl; // Extra large shadow
```

### Transitions

Duration, easing, and property tokens:

```typescript
import { transitions } from '$lib/design';

transitions.duration.fast; // '150ms'
transitions.duration.normal; // '200ms'
transitions.duration.slow; // '300ms'

transitions.easing.linear; // 'linear'
transitions.easing.inOut; // 'cubic-bezier(0.4, 0, 0.2, 1)'

transitions.property.colors; // 'background-color, border-color, color, fill, stroke'
```

### Z-Index

Consistent z-index scale for layering:

```typescript
import { zIndex } from '$lib/design';

zIndex.dropdown; // 1000
zIndex.modal; // 1050
zIndex.tooltip; // 1070
```

### Breakpoints

Responsive breakpoints:

```typescript
import { breakpoints } from '$lib/design';

breakpoints.sm; // '40rem' (640px)
breakpoints.md; // '48rem' (768px)
breakpoints.lg; // '64rem' (1024px)
```

## Utilities

### Color Utilities

```typescript
import { getColor, hexToRgba, getColorWithAlpha } from '$lib/design';

// Get a color value
getColor('primary', 600); // '#0284c7'

// Convert hex to RGBA
hexToRgba('#3b82f6', 0.5); // 'rgba(59, 130, 246, 0.5)'

// Get color with alpha
getColorWithAlpha('primary', 600, 0.5); // 'rgba(2, 132, 199, 0.5)'
```

### Spacing Utilities

```typescript
import { getSpacing, getSpacingMultiple, calcSpacing } from '$lib/design';

// Get spacing value
getSpacing('md'); // '0.75rem'

// Get multiple spacing values (for padding/margin)
getSpacingMultiple(['sm', 'lg']); // '0.5rem 1rem'

// Calculate spacing with multiplier
calcSpacing('md', 2); // '1.5rem'
```

### Typography Utilities

```typescript
import { getTypographyStyle } from '$lib/design';

// Get complete typography style
getTypographyStyle('lg', 'semibold', 'normal');
// { fontSize: '1.125rem', fontWeight: '600', lineHeight: '1.5' }
```

### Transition Utilities

```typescript
import { createTransition } from '$lib/design';

// Create transition string
createTransition('colors', 'normal', 'inOut');
// 'background-color, border-color, color, fill, stroke 200ms cubic-bezier(0.4, 0, 0.2, 1)'
```

### CSS Custom Properties

Generate CSS variables from tokens:

```typescript
import { generateCssVariables, getCssVar } from '$lib/design';

// Generate all CSS variables
const cssVars = generateCssVariables();

// Apply to document root
Object.entries(cssVars).forEach(([key, value]) => {
	document.documentElement.style.setProperty(key, value);
});

// Use in styles
getCssVar('color', 'primary', '600'); // 'var(--color-primary-600)'
```

### Component Style Builders

Pre-built style objects for common components:

```typescript
import { buildButtonStyles, buildCardStyles } from '$lib/design';

// Build button styles
const buttonStyles = buildButtonStyles('primary', 'md');
// { backgroundColor: '#0284c7', color: '#ffffff', padding: '0.5rem 1rem', ... }

// Build card styles
const cardStyles = buildCardStyles();
// { padding: '1rem', borderRadius: '0.75rem', boxShadow: '...', ... }
```

## Usage Examples

### In Svelte Components (CSS-in-JS)

```svelte
<script lang="ts">
	import { colors, spacing, typography } from '$lib/design';
</script>

<button style="background: {colors.primary[600]}; padding: {spacing.md}">
	Click me
</button>

<style>
	button {
		background: var(--color-primary-600);
		padding: var(--spacing-md);
		border-radius: var(--border-radius-lg);
	}
</style>
```

### In TypeScript

```typescript
import { colors, spacing, buildButtonStyles } from '$lib/design';

// Use tokens directly
const buttonColor = colors.primary[600];
const buttonPadding = spacing.md;

// Use style builders
const styles = buildButtonStyles('primary', 'md');
```

### In CSS with Custom Properties

First, generate and apply CSS variables (in `app.css` or root layout):

```typescript
import { generateCssVariables } from '$lib/design';

const cssVars = generateCssVariables();
Object.entries(cssVars).forEach(([key, value]) => {
	document.documentElement.style.setProperty(key, value);
});
```

Then use in CSS:

```css
.button {
	background-color: var(--color-primary-600);
	padding: var(--spacing-md);
	border-radius: var(--border-radius-lg);
	transition: var(--transition-colors) var(--transition-duration-normal);
}

.button:hover {
	background-color: var(--color-primary-700);
}
```

## Tailwind Integration

The design system tokens can be integrated with Tailwind CSS for a unified approach.

### Update `tailwind.config.js`

```javascript
import { colors, spacing, typography, borders, shadows } from './src/lib/design/tokens';

export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				primary: colors.primary,
				success: colors.success,
				error: colors.error,
				warning: colors.warning,
				info: colors.info,
				gray: colors.gray
			},
			spacing: spacing,
			fontSize: typography.fontSize,
			fontWeight: typography.fontWeight,
			lineHeight: typography.lineHeight,
			borderRadius: borders.radius,
			boxShadow: shadows
		}
	},
	plugins: []
};
```

### Use Tailwind Classes

```svelte
<button class="bg-primary-600 hover:bg-primary-700 px-md py-sm rounded-lg">
	Click me
</button>
```

## Migration Guide

### Phase 1: Adopt for New Components

Start using design tokens for all new components:

```svelte
<!-- Old approach -->
<button style="background: #3b82f6; padding: 8px 16px; border-radius: 6px;">
	Click me
</button>

<!-- New approach -->
<script>
	import { colors, spacing, borders } from '$lib/design';
</script>

<button style="background: {colors.primary[600]}; padding: {spacing.sm} {spacing.lg}; border-radius: {borders.radius.lg};">
	Click me
</button>
```

### Phase 2: Gradually Migrate Existing Components

Identify components with hardcoded values and replace them with tokens:

```svelte
<!-- Before -->
<div style="background: #f9fafb; padding: 16px; border-radius: 8px;">
	Content
</div>

<!-- After -->
<script>
	import { colors, spacing, borders } from '$lib/design';
</script>

<div style="background: {colors.background.secondary}; padding: {spacing.lg}; border-radius: {borders.radius.xl};">
	Content
</div>
```

### Phase 3: Update Global Styles

Replace hardcoded values in `app.css` with CSS custom properties:

```css
/* Before */
.card {
	background: #ffffff;
	border: 1px solid #e5e7eb;
	border-radius: 8px;
	padding: 16px;
}

/* After */
.card {
	background: var(--color-background-card);
	border: var(--border-width-thin) solid var(--color-border-default);
	border-radius: var(--border-radius-xl);
	padding: var(--spacing-lg);
}
```

### Phase 4: Refactor Component Styles

Extract inline styles to component-specific style blocks using tokens:

```svelte
<script>
	import { colors } from '$lib/design';
</script>

<div class="card">
	Content
</div>

<style>
	.card {
		background: var(--color-background-card);
		border: var(--border-width-thin) solid var(--color-border-default);
		border-radius: var(--border-radius-xl);
		padding: var(--spacing-lg);
	}
</style>
```

## Best Practices

1. **Always use tokens**: Never hardcode colors, spacing, or other design values.
2. **Use semantic colors**: Prefer `colors.text.primary` over `colors.gray[900]` for better intent.
3. **Consistent spacing**: Use the spacing scale for all margins and padding.
4. **Type safety**: Leverage TypeScript types for token validation.
5. **Component builders**: Use pre-built style builders for common components.

## Type Safety

The design system is fully typed with TypeScript:

```typescript
import type { ColorToken, SpacingToken, FontSizeToken } from '$lib/design';

// Type-safe token usage
const color: ColorToken = 'primary';
const spacing: SpacingToken = 'md';
const fontSize: FontSizeToken = 'lg';
```

## Future Enhancements

- Dark mode support with color scheme switching
- Theme provider for runtime theme changes
- Additional component style builders
- Accessibility utilities (focus rings, contrast checking)
- Animation presets

## Contributing

When adding new design tokens:

1. Add to appropriate section in `tokens.ts`
2. Update type exports
3. Add utility functions in `utils.ts` if needed
4. Document in this README
5. Update Tailwind config if applicable

## Resources

- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Design Tokens Specification](https://www.w3.org/community/design-tokens/)
- [CSS Custom Properties](https://developer.mozilla.org/en-US/docs/Web/CSS/--*)
