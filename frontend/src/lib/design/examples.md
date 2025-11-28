# Design System Examples

Practical examples of using the design system tokens in various scenarios.

## Basic Button Component

```svelte
<script lang="ts">
	import { colors, spacing, borders, transitions } from '$lib/design';

	interface Props {
		variant?: 'primary' | 'secondary' | 'ghost';
		size?: 'sm' | 'md' | 'lg';
	}

	const { variant = 'primary', size = 'md' }: Props = $props();
</script>

<button class="btn btn-{variant} btn-{size}">
	<slot />
</button>

<style>
	.btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		font-weight: 500;
		transition: all 200ms ease-in-out;
		border-radius: var(--border-radius-lg);
	}

	.btn-sm {
		padding: var(--spacing-xs) var(--spacing-md);
		font-size: var(--font-size-sm);
	}

	.btn-md {
		padding: var(--spacing-sm) var(--spacing-lg);
		font-size: var(--font-size-base);
	}

	.btn-lg {
		padding: var(--spacing-md) var(--spacing-xl);
		font-size: var(--font-size-lg);
	}

	.btn-primary {
		background-color: var(--color-primary-600);
		color: var(--color-text-inverse);
		border: none;
	}

	.btn-primary:hover {
		background-color: var(--color-primary-700);
	}

	.btn-secondary {
		background-color: var(--color-background-primary);
		color: var(--color-text-secondary);
		border: var(--border-width-thin) solid var(--color-border-default);
	}

	.btn-secondary:hover {
		background-color: var(--color-background-secondary);
	}

	.btn-ghost {
		background-color: transparent;
		color: var(--color-text-secondary);
		border: none;
	}

	.btn-ghost:hover {
		background-color: var(--color-background-secondary);
	}
</style>
```

## Card Component with Tokens

```svelte
<script lang="ts">
	import { buildCardStyles } from '$lib/design';

	const cardStyles = buildCardStyles();
</script>

<div class="card">
	<slot />
</div>

<style>
	.card {
		background: var(--color-background-card);
		border: var(--border-width-thin) solid var(--color-border-default);
		border-radius: var(--border-radius-2xl);
		padding: var(--spacing-lg);
		box-shadow: var(--shadow-sm);
		transition: box-shadow var(--transition-duration-normal) var(--transition-easing-inOut);
	}

	.card:hover {
		box-shadow: var(--shadow-md);
	}
</style>
```

## Form Input with Design Tokens

```svelte
<script lang="ts">
	import { colors, spacing, borders } from '$lib/design';

	interface Props {
		value: string;
		placeholder?: string;
		error?: string;
	}

	const { value = '', placeholder = '', error = '' }: Props = $props();
</script>

<div class="input-wrapper">
	<input
		type="text"
		{value}
		{placeholder}
		class="input"
		class:error={!!error}
	/>
	{#if error}
		<span class="error-message">{error}</span>
	{/if}
</div>

<style>
	.input-wrapper {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xs);
	}

	.input {
		width: 100%;
		padding: var(--spacing-sm) var(--spacing-lg);
		border: var(--border-width-thin) solid var(--color-border-default);
		border-radius: var(--border-radius-lg);
		font-size: var(--font-size-base);
		color: var(--color-text-primary);
		background: var(--color-background-primary);
		transition: all var(--transition-duration-normal) var(--transition-easing-inOut);
	}

	.input:focus {
		outline: none;
		border-color: var(--color-primary-500);
		box-shadow: 0 0 0 3px var(--color-primary-100);
	}

	.input.error {
		border-color: var(--color-error-500);
	}

	.input.error:focus {
		box-shadow: 0 0 0 3px var(--color-error-100);
	}

	.error-message {
		font-size: var(--font-size-sm);
		color: var(--color-error-600);
	}
</style>
```

## Badge Component

```svelte
<script lang="ts">
	import { colors, spacing, borders, typography } from '$lib/design';

	interface Props {
		variant?: 'success' | 'error' | 'warning' | 'info' | 'neutral';
	}

	const { variant = 'neutral' }: Props = $props();
</script>

<span class="badge badge-{variant}">
	<slot />
</span>

<style>
	.badge {
		display: inline-flex;
		align-items: center;
		padding: var(--spacing-xs) var(--spacing-sm);
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		border-radius: var(--border-radius-full);
	}

	.badge-success {
		background-color: var(--color-success-100);
		color: var(--color-success-700);
	}

	.badge-error {
		background-color: var(--color-error-100);
		color: var(--color-error-700);
	}

	.badge-warning {
		background-color: var(--color-warning-100);
		color: var(--color-warning-700);
	}

	.badge-info {
		background-color: var(--color-info-100);
		color: var(--color-info-700);
	}

	.badge-neutral {
		background-color: var(--color-gray-100);
		color: var(--color-gray-700);
	}
</style>
```

## Responsive Layout with Breakpoints

```svelte
<script lang="ts">
	import { spacing, breakpoints } from '$lib/design';
</script>

<div class="grid">
	<div class="grid-item">Item 1</div>
	<div class="grid-item">Item 2</div>
	<div class="grid-item">Item 3</div>
	<div class="grid-item">Item 4</div>
</div>

<style>
	.grid {
		display: grid;
		gap: var(--spacing-lg);
		grid-template-columns: 1fr;
		padding: var(--spacing-lg);
	}

	/* Tablet */
	@media (min-width: 48rem) {
		.grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	/* Desktop */
	@media (min-width: 64rem) {
		.grid {
			grid-template-columns: repeat(4, 1fr);
			gap: var(--spacing-xl);
		}
	}

	.grid-item {
		background: var(--color-background-card);
		padding: var(--spacing-lg);
		border-radius: var(--border-radius-xl);
		border: var(--border-width-thin) solid var(--color-border-default);
	}
</style>
```

## Modal with Z-Index

```svelte
<script lang="ts">
	import { colors, spacing, borders, shadows, zIndex } from '$lib/design';

	interface Props {
		open: boolean;
		onclose: () => void;
	}

	const { open, onclose }: Props = $props();
</script>

{#if open}
	<div class="modal-backdrop" onclick={onclose}>
		<div class="modal" onclick={(e) => e.stopPropagation()}>
			<button class="close-btn" onclick={onclose}>×</button>
			<slot />
		</div>
	</div>
{/if}

<style>
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background-color: rgba(0, 0, 0, 0.5);
		backdrop-filter: blur(4px);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: var(--z-index-modal);
		padding: var(--spacing-lg);
	}

	.modal {
		background: var(--color-background-modal);
		border-radius: var(--border-radius-xl);
		box-shadow: var(--shadow-2xl);
		max-width: 32rem;
		width: 100%;
		padding: var(--spacing-xl);
		position: relative;
		animation: slideUp 0.3s ease-out;
	}

	.close-btn {
		position: absolute;
		top: var(--spacing-md);
		right: var(--spacing-md);
		background: transparent;
		border: none;
		font-size: var(--font-size-2xl);
		color: var(--color-text-muted);
		cursor: pointer;
		padding: var(--spacing-xs);
		line-height: 1;
		transition: color var(--transition-duration-fast);
	}

	.close-btn:hover {
		color: var(--color-text-primary);
	}

	@keyframes slideUp {
		from {
			opacity: 0;
			transform: translateY(20px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
```

## Using TypeScript Utilities

```typescript
import {
	getColor,
	getSpacing,
	createTransition,
	buildButtonStyles,
	hexToRgba
} from '$lib/design';

// Get specific color
const primaryColor = getColor('primary', 600); // '#0284c7'

// Get spacing
const padding = getSpacing('md'); // '0.75rem'

// Create transition
const transition = createTransition('colors', 'normal', 'inOut');
// 'background-color, border-color, color, fill, stroke 200ms cubic-bezier(0.4, 0, 0.2, 1)'

// Build button styles
const buttonStyles = buildButtonStyles('primary', 'md');
// Apply to element dynamically

// Create transparent color
const transparentPrimary = hexToRgba('#0284c7', 0.1); // 'rgba(2, 132, 199, 0.1)'
```

## Tailwind Classes with Tokens

Since Tailwind is configured to use our design tokens, you can use them directly:

```svelte
<button class="bg-primary-600 hover:bg-primary-700 text-white px-lg py-sm rounded-lg shadow-md">
	Click me
</button>

<div class="p-xl bg-gray-50 rounded-2xl border border-gray-200">
	<h2 class="text-xl font-semibold text-gray-900 mb-md">Card Title</h2>
	<p class="text-base text-gray-600 leading-normal">Card content</p>
</div>

<span class="inline-flex items-center gap-xs px-sm py-xxs bg-success-100 text-success-700 rounded-full text-xs font-medium">
	Success
</span>
```

## Dark Mode Support (Future Enhancement)

When dark mode is implemented, tokens can be easily switched:

```svelte
<script lang="ts">
	import { colors } from '$lib/design';

	// In a theme store
	$effect(() => {
		if (darkMode) {
			document.documentElement.style.setProperty('--color-background-primary', colors.gray[900]);
			document.documentElement.style.setProperty('--color-text-primary', colors.gray[50]);
			// ... more dark mode colors
		} else {
			document.documentElement.style.setProperty('--color-background-primary', colors.background.primary);
			document.documentElement.style.setProperty('--color-text-primary', colors.text.primary);
			// ... more light mode colors
		}
	});
</script>
```

## Animation with Transitions

```svelte
<script lang="ts">
	import { transitions } from '$lib/design';

	let isVisible = $state(false);
</script>

<button onclick={() => isVisible = !isVisible}>Toggle</button>

{#if isVisible}
	<div class="fade-in">
		Content with fade-in animation
	</div>
{/if}

<style>
	.fade-in {
		animation: fadeIn var(--transition-duration-normal) var(--transition-easing-inOut);
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
```

## Consistent Spacing Grid

```svelte
<div class="container">
	<h1 class="heading">Photo Explorer</h1>
	<p class="description">A modern photo management application</p>
	<button class="cta">Get Started</button>
</div>

<style>
	.container {
		padding: var(--spacing-2xl);
		max-width: 1200px;
		margin: 0 auto;
	}

	.heading {
		font-size: var(--font-size-4xl);
		font-weight: var(--font-weight-bold);
		color: var(--color-text-primary);
		margin-bottom: var(--spacing-md);
	}

	.description {
		font-size: var(--font-size-lg);
		color: var(--color-text-secondary);
		margin-bottom: var(--spacing-xl);
	}

	.cta {
		background: var(--color-primary-600);
		color: var(--color-text-inverse);
		padding: var(--spacing-md) var(--spacing-2xl);
		border-radius: var(--border-radius-lg);
		font-size: var(--font-size-base);
		font-weight: var(--font-weight-semibold);
		border: none;
		cursor: pointer;
		transition: background var(--transition-duration-normal);
	}

	.cta:hover {
		background: var(--color-primary-700);
	}
</style>
```

These examples demonstrate how to use the design system effectively across different components and scenarios, ensuring consistency and maintainability throughout the application.
