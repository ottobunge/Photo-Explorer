<script lang="ts">
	/**
	 * Image component with error handling and fallback placeholder
	 * Automatically handles loading errors and displays a fallback
	 */
	interface Props {
		/** Image source URL */
		src: string;
		/** Alt text for accessibility */
		alt: string;
		/** Fallback image URL or placeholder emoji */
		fallback?: string;
		/** Additional CSS classes */
		class?: string;
		/** Whether to use lazy loading */
		lazy?: boolean;
		/** Callback when image fails to load */
		onError?: (error: Event) => void;
	}

	const {
		src,
		alt,
		fallback = '🖼️',
		class: className = '',
		lazy = true,
		onError
	}: Props = $props();

	let hasError = $state(false);
	let isLoading = $state(true);

	function handleError(event: Event): void {
		hasError = true;
		isLoading = false;
		console.error('Failed to load image:', src);
		if (onError) {
			onError(event);
		}
	}

	function handleLoad(): void {
		isLoading = false;
	}

	// Reset error state when src changes
	$effect(() => {
		if (src) {
			hasError = false;
			isLoading = true;
		}
	});
</script>

{#if hasError}
	<div class="image-fallback {className}">
		{#if fallback.startsWith('http') || fallback.startsWith('/')}
			<img
				src={fallback}
				alt={alt}
				class="fallback-image"
			/>
		{:else}
			<span class="fallback-emoji">{fallback}</span>
		{/if}
	</div>
{:else}
	<img
		{src}
		{alt}
		class="{className}"
		class:loading={isLoading}
		loading={lazy ? 'lazy' : 'eager'}
		onerror={handleError}
		onload={handleLoad}
	/>
{/if}

<style>
	.image-fallback {
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--bg-secondary, #f3f4f6);
		color: var(--text-muted, #9ca3af);
		border-radius: 4px;
		width: 100%;
		height: 100%;
		min-height: 100px;
	}

	.fallback-emoji {
		font-size: 3rem;
		opacity: 0.5;
	}

	.fallback-image {
		max-width: 100%;
		max-height: 100%;
		object-fit: contain;
		opacity: 0.7;
	}

	img.loading {
		opacity: 0.7;
		filter: blur(2px);
		transition: opacity 0.3s ease, filter 0.3s ease;
	}
</style>
