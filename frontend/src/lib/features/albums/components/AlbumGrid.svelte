<script lang="ts">
	import type { Album } from '../types';
	import AlbumCard from './AlbumCard.svelte';

	interface Props {
		albums: Album[];
	}

	const { albums = [] }: Props = $props();
</script>

<div data-testid="album-grid">
	{#if albums.length === 0}
		<div class="card p-12 text-center">
			<div class="mb-4 text-4xl">&#128193;</div>
			<p class="text-gray-500">No albums yet</p>
			<p class="mt-2 text-sm text-gray-400">Create an album to organize your photos</p>
		</div>
	{:else}
		<div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
			{#each albums as album (album.id)}
				<AlbumCard {album} />
			{/each}
		</div>
	{/if}
</div>
