<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * Reusable card container component
	 * Provides consistent styling for card-based layouts
	 */
	interface Props {
		/** Additional CSS classes to apply */
		class?: string;
		/** Whether the card should have a border */
		bordered?: boolean;
		/** Whether the card should have padding */
		padded?: boolean;
		/** Whether the card should have hover effects */
		hoverable?: boolean;
		/** Content to render inside the card */
		children?: Snippet;
	}

	const {
		class: className = '',
		bordered = true,
		padded = true,
		hoverable = false,
		children
	}: Props = $props();
</script>

<div
	class="card {className}"
	class:bordered
	class:padded
	class:hoverable
>
	{@render children?.()}
</div>

<style>
	.card {
		background: var(--card-bg, #ffffff);
		border-radius: 12px;
		transition: all 0.2s ease;
	}

	.card.bordered {
		border: 1px solid var(--border-color, #e5e7eb);
	}

	.card.padded {
		padding: 1.5rem;
	}

	.card.hoverable:hover {
		box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
		transform: translateY(-2px);
	}
</style>
