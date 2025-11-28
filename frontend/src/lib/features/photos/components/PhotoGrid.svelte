<script lang="ts">
	import { API_HOST } from '$lib/api/client';
	import type { Photo } from '../types';

	interface Props {
		photos: Photo[];
		loading?: boolean;
		emptyMessage?: string;
		showScore?: boolean;
		columns?: 2 | 3 | 4 | 5 | 6;
		onPhotoClick?: (photo: Photo) => void;
	}

	const {
		photos = [],
		loading = false,
		emptyMessage = 'No photos available',
		showScore = false,
		columns = 6,
		onPhotoClick
	}: Props = $props();

	// Map column counts to Tailwind grid classes
	const gridClasses: Record<number, string> = {
		2: 'grid-cols-2',
		3: 'grid-cols-2 sm:grid-cols-3',
		4: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4',
		5: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5',
		6: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6'
	};

	const gridClass = $derived(gridClasses[columns] ?? gridClasses[6]);

	function handlePhotoClick(photo: Photo, event: MouseEvent): void {
		if (onPhotoClick) {
			event.preventDefault();
			onPhotoClick(photo);
		}
	}

	function handleKeyDown(photo: Photo, event: KeyboardEvent): void {
		if ((event.key === 'Enter' || event.key === ' ') && onPhotoClick) {
			event.preventDefault();
			onPhotoClick(photo);
		}
	}

	function getThumbnailUrl(photo: Photo): string | null {
		if (!photo.thumbnail_url) {
			return null;
		}
		return photo.thumbnail_url.startsWith('http')
			? photo.thumbnail_url
			: `${API_HOST}${photo.thumbnail_url}`;
	}
</script>

<div data-testid="photo-grid" role="region" aria-label="Photo gallery">
	{#if loading && photos.length === 0}
		<div class="text-center py-12 text-gray-500" data-testid="loading-state" role="status" aria-live="polite">
			<div class="mb-4 text-4xl" aria-hidden="true">⏳</div>
			<p>Loading photos...</p>
		</div>
	{:else if photos.length === 0}
		<div class="card p-12 text-center" data-testid="empty-state" role="status">
			<div class="mb-4 text-4xl" aria-hidden="true">📷</div>
			<p class="text-gray-500">{emptyMessage}</p>
		</div>
	{:else}
		<div class="grid {gridClass} gap-4" data-testid="photo-grid-content">
			{#each photos as photo (photo.id)}
				{@const thumbnailUrl = getThumbnailUrl(photo)}
				{@const hasClickHandler = onPhotoClick !== undefined}
				{@const linkHref = hasClickHandler ? '#' : `/photos/${photo.id}`}

				<a
					href={linkHref}
					class="photo-card group cursor-pointer block"
					data-testid="photo-card"
					data-photo-id={photo.id}
					aria-label={`View photo: ${photo.filename}`}
					role={hasClickHandler ? 'button' : 'link'}
					tabindex="0"
					onclick={(e) => handlePhotoClick(photo, e)}
					onkeydown={(e) => handleKeyDown(photo, e)}
				>
					{#if thumbnailUrl}
						<img
							src={thumbnailUrl}
							alt={photo.filename}
							class="aspect-square w-full rounded-lg object-cover transition-transform group-hover:scale-105 group-focus:scale-105"
							loading="lazy"
						/>
					{:else}
						<div
							class="aspect-square w-full rounded-lg bg-gray-100 flex items-center justify-center"
							data-testid="photo-placeholder"
							role="img"
							aria-label="Photo placeholder - no thumbnail available"
						>
							<svg
								class="w-8 h-8 text-gray-400"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
								aria-hidden="true"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
								/>
							</svg>
						</div>
					{/if}
					<p class="mt-1 truncate text-xs text-gray-500" title={photo.filename}>{photo.filename}</p>
					{#if showScore && photo.score !== undefined}
						<p class="text-xs text-blue-500" data-testid="photo-score">
							Score: {photo.score.toFixed(2)}
						</p>
					{/if}
				</a>
			{/each}
		</div>
	{/if}
</div>

<style>
	.photo-card {
		transition: transform 0.2s ease-in-out;
	}

	.photo-card:hover,
	.photo-card:focus {
		outline: 2px solid transparent;
		outline-offset: 2px;
	}

	.photo-card:focus-visible {
		outline: 2px solid #3b82f6;
		outline-offset: 2px;
		border-radius: 0.5rem;
	}
</style>
