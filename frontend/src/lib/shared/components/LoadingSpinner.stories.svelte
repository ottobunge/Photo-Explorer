<script module lang="ts">
	import { defineMeta } from '@storybook/addon-svelte-csf';
	import LoadingSpinner from './LoadingSpinner.svelte';

	const { Story } = defineMeta({
		title: 'Shared/LoadingSpinner',
		component: LoadingSpinner,
		tags: ['autodocs'],
		argTypes: {
			size: {
				control: 'select',
				options: ['sm', 'md', 'lg'],
				description: 'Size of the spinner'
			}
		}
	});
</script>

<!--
@component
LoadingSpinner component displays a loading indicator.

## Usage
```svelte
<LoadingSpinner size="md" />
```
-->

<!-- Small spinner -->
<Story name="Small" args={{ size: 'sm' }} />

<!-- Medium spinner (default) -->
<Story name="Medium" args={{ size: 'md' }} />

<!-- Large spinner -->
<Story name="Large" args={{ size: 'lg' }} />

<!-- All sizes side by side -->
<Story name="AllSizes" asChild>
	<div style="display: flex; gap: 2rem; align-items: center;">
		<div style="text-align: center;">
			<LoadingSpinner size="sm" />
			<p style="margin-top: 0.5rem; font-size: 0.875rem; color: #6b7280;">Small</p>
		</div>
		<div style="text-align: center;">
			<LoadingSpinner size="md" />
			<p style="margin-top: 0.5rem; font-size: 0.875rem; color: #6b7280;">Medium</p>
		</div>
		<div style="text-align: center;">
			<LoadingSpinner size="lg" />
			<p style="margin-top: 0.5rem; font-size: 0.875rem; color: #6b7280;">Large</p>
		</div>
	</div>
</Story>

<!-- Loading card -->
<Story name="LoadingCard" asChild>
	<div
		style="padding: 2rem; border: 1px solid #e5e7eb; border-radius: 12px; text-align: center; background: white;"
	>
		<LoadingSpinner size="lg" />
		<p style="margin-top: 1rem; color: #6b7280;">Loading your photos...</p>
	</div>
</Story>
