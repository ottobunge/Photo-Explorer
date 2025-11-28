<script module lang="ts">
	import { defineMeta } from '@storybook/addon-svelte-csf';
	import Modal from './Modal.svelte';
	import Button from './Button.svelte';

	const { Story } = defineMeta({
		title: 'Shared/Modal',
		component: Modal,
		tags: ['autodocs'],
		argTypes: {
			title: {
				control: 'text',
				description: 'Modal title'
			}
		}
	});
</script>

<script lang="ts">
	import { writable } from 'svelte/store';

	const isOpen1 = writable(false);
	const isOpen2 = writable(false);
	const isOpen3 = writable(false);
</script>

<!--
@component
Modal component displays content in a dialog overlay.

## Usage
```svelte
<Modal bind:open={isOpen} title="Edit Photo">
  <p>Modal content here</p>
  {#snippet footer()}
    <Button onclick={() => isOpen = false}>Close</Button>
  {/snippet}
</Modal>
```
-->

<!-- Default modal -->
<Story name="Default" asChild>
	<div>
		<Button onclick={() => isOpen1.set(true)}>Open Modal</Button>
		{#if $isOpen1}
			<Modal title="Default Modal" on:close={() => isOpen1.set(false)}>
				<p style="margin: 0; color: #6b7280;">
					This is a default modal with a title and some content.
				</p>
				{#snippet footer()}
					<div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
						<Button variant="secondary" onclick={() => isOpen1.set(false)}>Cancel</Button>
						<Button variant="primary" onclick={() => isOpen1.set(false)}>Confirm</Button>
					</div>
				{/snippet}
			</Modal>
		{/if}
	</div>
</Story>

<!-- Small modal -->
<Story name="Small" asChild>
	<div>
		<Button onclick={() => isOpen2.set(true)}>Open Small Modal</Button>
		{#if $isOpen2}
			<Modal title="Small Modal" on:close={() => isOpen2.set(false)}>
				<p style="margin: 0; color: #6b7280;">This is a small modal.</p>
				{#snippet footer()}
					<Button onclick={() => isOpen2.set(false)}>Close</Button>
				{/snippet}
			</Modal>
		{/if}
	</div>
</Story>

<!-- Large modal with form -->
<Story name="LargeWithForm" asChild>
	<div>
		<Button onclick={() => isOpen3.set(true)}>Open Large Modal</Button>
		{#if $isOpen3}
			<Modal title="Create New Album" on:close={() => isOpen3.set(false)}>
			<div style="display: flex; flex-direction: column; gap: 1rem;">
				<div>
					<label style="display: block; margin-bottom: 0.5rem; font-weight: 500;">Album Name</label>
					<input
						type="text"
						placeholder="Summer 2024"
						style="width: 100%; padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 6px;"
					/>
				</div>
				<div>
					<label style="display: block; margin-bottom: 0.5rem; font-weight: 500;">Description</label
					>
					<textarea
						placeholder="Vacation photos from our trip..."
						rows="4"
						style="width: 100%; padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 6px;"
					></textarea>
				</div>
			</div>
			{#snippet footer()}
				<div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
					<Button variant="secondary" onclick={() => isOpen3.set(false)}>Cancel</Button>
					<Button variant="primary" onclick={() => isOpen3.set(false)}>Create Album</Button>
				</div>
			{/snippet}
		</Modal>
		{/if}
	</div>
</Story>
