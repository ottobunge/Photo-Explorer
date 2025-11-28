<script lang="ts">
	/**
	 * Empty state placeholder component
	 * Displays when there's no content to show (e.g., no photos, no connectors)
	 */
	import type { Snippet } from 'svelte';

	interface Props {
		/** Icon or emoji to display */
		icon?: string;
		/** Title text */
		title?: string;
		/** Description text */
		description?: string;
		/** Additional CSS classes */
		class?: string;
		/** Optional action button slot */
		action?: Snippet;
	}

	const {
		icon = '📭',
		title = 'No items found',
		description = '',
		class: className = '',
		action
	}: Props = $props();
</script>

<div class="empty-state {className}">
	{#if icon}
		<div class="empty-icon">{icon}</div>
	{/if}
	{#if title}
		<h3 class="empty-title">{title}</h3>
	{/if}
	{#if description}
		<p class="empty-description">{description}</p>
	{/if}
	{#if action}
		<div class="empty-action">
			{@render action()}
		</div>
	{/if}
</div>

<style>
	.empty-state {
		text-align: center;
		padding: 3rem 1.5rem;
		background: var(--bg-secondary, #f9fafb);
		border-radius: 12px;
		color: var(--text-muted, #6b7280);
	}

	.empty-icon {
		font-size: 3rem;
		margin-bottom: 1rem;
		opacity: 0.7;
	}

	.empty-title {
		font-size: 1.125rem;
		font-weight: 600;
		margin: 0 0 0.5rem;
		color: var(--text-primary, #1f2937);
	}

	.empty-description {
		margin: 0 0 1.5rem;
		font-size: 0.9375rem;
		color: var(--text-muted, #6b7280);
		max-width: 400px;
		margin-left: auto;
		margin-right: auto;
	}

	.empty-action {
		margin-top: 1.5rem;
	}
</style>
