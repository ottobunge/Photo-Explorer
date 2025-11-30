<script lang="ts">
	import type { WatchedFolder } from '../types';
	import FolderCard from './FolderCard.svelte';

	interface Props {
		folders?: WatchedFolder[];
	}

	const { folders = [] }: Props = $props();
</script>

<div data-testid="folder-list">
	{#if folders.length === 0}
		<div class="card p-12 text-center">
			<div class="mb-4 text-4xl">📂</div>
			<p class="text-gray-500">No watched folders</p>
			<p class="mt-2 text-sm text-gray-400">Add a folder to automatically import photos</p>
		</div>
	{:else}
		<div class="space-y-4">
			{#each folders as folder (folder.id)}
				<FolderCard {folder} />
			{/each}
		</div>
	{/if}
</div>
