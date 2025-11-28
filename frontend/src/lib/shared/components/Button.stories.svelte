<script module lang="ts">
	import { defineMeta } from '@storybook/addon-svelte-csf';
	import Button from './Button.svelte';

	const { Story } = defineMeta({
		title: 'Shared/Button',
		component: Button,
		tags: ['autodocs'],
		argTypes: {
			variant: {
				control: 'select',
				options: ['primary', 'secondary', 'ghost'],
				description: 'Visual style variant of the button'
			},
			size: {
				control: 'select',
				options: ['sm', 'md', 'lg'],
				description: 'Size of the button'
			},
			disabled: {
				control: 'boolean',
				description: 'Whether the button is disabled'
			},
			type: {
				control: 'select',
				options: ['button', 'submit', 'reset'],
				description: 'HTML button type attribute'
			}
		}
	});
</script>

<!--
@component
Button component provides consistent styling and behavior across all button interactions.

## Usage
```svelte
<Button variant="primary" size="md" onclick={handleClick}>
  Click me
</Button>
```
-->

<!-- Primary button is used for main actions -->
<Story name="Primary" args={{ variant: 'primary', size: 'md' }}>Primary Button</Story>

<!-- Secondary button is used for secondary actions -->
<Story name="Secondary" args={{ variant: 'secondary', size: 'md' }}>Secondary Button</Story>

<!-- Ghost button is used for tertiary actions with minimal visual weight -->
<Story name="Ghost" args={{ variant: 'ghost', size: 'md' }}>Ghost Button</Story>

<!-- Small size button -->
<Story name="Small" args={{ variant: 'primary', size: 'sm' }}>Small Button</Story>

<!-- Medium size button (default) -->
<Story name="Medium" args={{ variant: 'primary', size: 'md' }}>Medium Button</Story>

<!-- Large size button -->
<Story name="Large" args={{ variant: 'primary', size: 'lg' }}>Large Button</Story>

<!-- Disabled button state -->
<Story name="Disabled" args={{ variant: 'primary', size: 'md', disabled: true }}>
	Disabled Button
</Story>

<!-- All button variants side by side -->
<Story name="AllVariants" asChild>
	<div style="display: flex; gap: 1rem; align-items: center;">
		<Button variant="primary">Primary</Button>
		<Button variant="secondary">Secondary</Button>
		<Button variant="ghost">Ghost</Button>
	</div>
</Story>

<!-- All button sizes side by side -->
<Story name="AllSizes" asChild>
	<div style="display: flex; gap: 1rem; align-items: center;">
		<Button size="sm">Small</Button>
		<Button size="md">Medium</Button>
		<Button size="lg">Large</Button>
	</div>
</Story>
