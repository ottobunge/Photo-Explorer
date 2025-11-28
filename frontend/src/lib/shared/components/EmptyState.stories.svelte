<script module lang="ts">
	import { defineMeta } from '@storybook/addon-svelte-csf';
	import EmptyState from './EmptyState.svelte';
	import Button from './Button.svelte';

	const { Story } = defineMeta({
		title: 'Shared/EmptyState',
		component: EmptyState,
		tags: ['autodocs'],
		argTypes: {
			icon: {
				control: 'text',
				description: 'Icon or emoji to display'
			},
			title: {
				control: 'text',
				description: 'Title text'
			},
			description: {
				control: 'text',
				description: 'Description text'
			},
			class: {
				control: 'text',
				description: 'Additional CSS classes'
			}
		}
	});
</script>

<!--
@component
EmptyState component displays a placeholder when there's no content to show.

## Usage
```svelte
<EmptyState
  icon="📷"
  title="No photos yet"
  description="Upload your first photo to get started"
>
  {#snippet action()}
    <Button>Upload Photo</Button>
  {/snippet}
</EmptyState>
```
-->

<!-- Default empty state -->
<Story name="Default" args={{ icon: '📭', title: 'No items found', description: '' }} />

<!-- No photos state -->
<Story
	name="NoPhotos"
	args={{
		icon: '📷',
		title: 'No photos yet',
		description: 'Upload your first photo to get started with your collection.'
	}}
/>

<!-- No search results state -->
<Story
	name="NoSearchResults"
	args={{
		icon: '🔍',
		title: 'No results found',
		description: 'Try adjusting your search terms or filters.'
	}}
/>

<!-- No albums state -->
<Story
	name="NoAlbums"
	args={{
		icon: '📚',
		title: 'No albums yet',
		description: 'Create your first album to organize your photos.'
	}}
/>

<!-- With action button -->
<Story
	name="WithAction"
	args={{
		icon: '📷',
		title: 'No photos yet',
		description: 'Upload your first photo to get started.'
	}}
	asChild
>
	<EmptyState icon="📷" title="No photos yet" description="Upload your first photo to get started.">
		{#snippet action()}
			<Button variant="primary">Upload Photo</Button>
		{/snippet}
	</EmptyState>
</Story>

<!-- Error state -->
<Story
	name="Error"
	args={{
		icon: '❌',
		title: 'Something went wrong',
		description: 'An error occurred while loading your content. Please try again.'
	}}
	asChild
>
	<EmptyState
		icon="❌"
		title="Something went wrong"
		description="An error occurred while loading your content. Please try again."
	>
		{#snippet action()}
			<Button variant="secondary">Retry</Button>
		{/snippet}
	</EmptyState>
</Story>
