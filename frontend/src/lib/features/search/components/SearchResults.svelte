<script lang="ts">
	import type { SearchResult } from '../types';

	export let results: SearchResult[] = [];
	export let loading = false;
</script>

<div data-testid="search-results">
	{#if loading}
		<div class="py-12 text-center text-gray-500">
			<div class="mb-4 text-4xl">🔍</div>
			<p>Searching...</p>
		</div>
	{:else if results.length === 0}
		<div class="card p-12 text-center" data-testid="no-results">
			<div class="mb-4 text-4xl">📷</div>
			<p class="text-gray-500">No matching photos found</p>
			<p class="mt-2 text-sm text-gray-400">Try a different search term</p>
		</div>
	{:else}
		<div class="photo-grid">
			{#each results as result (result.photo.id)}
				<a
					href="/photos/{result.photo.id}"
					class="group relative aspect-square overflow-hidden rounded-lg bg-gray-100"
					data-testid="photo-card"
				>
					<img
						src={result.photo.thumbnailUrl}
						alt={result.photo.description || result.photo.filename}
						class="h-full w-full object-cover transition-transform group-hover:scale-105"
						loading="lazy"
					/>
					<div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent p-3">
						<p class="truncate text-sm text-white">{result.photo.filename}</p>
						<p class="text-xs text-white/70">Score: {(result.score * 100).toFixed(0)}%</p>
					</div>
				</a>
			{/each}
		</div>
	{/if}
</div>
