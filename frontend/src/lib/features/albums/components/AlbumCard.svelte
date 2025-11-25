<script lang="ts">
	import type { Album } from '../types';

	interface Props {
		album: Album;
	}

	const { album }: Props = $props();
</script>

<a
	href="/albums/{album.id}"
	class="card group overflow-hidden transition-shadow hover:shadow-md"
	data-testid="album-card"
>
	<div class="aspect-video bg-gray-100">
		{#if album.coverPhotoUrl}
			<img
				src={album.coverPhotoUrl}
				alt={album.name}
				class="h-full w-full object-cover transition-transform group-hover:scale-105"
				loading="lazy"
			/>
		{:else}
			<div class="flex h-full items-center justify-center text-4xl text-gray-300">&#128193;</div>
		{/if}
	</div>
	<div class="p-4">
		<h3 class="font-medium text-gray-900 group-hover:text-primary-600">{album.name}</h3>
		<p class="mt-1 text-sm text-gray-500">{album.photoCount} photos</p>
	</div>
</a>
