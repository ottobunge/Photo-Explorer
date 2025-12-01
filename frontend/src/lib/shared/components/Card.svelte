<script lang="ts">
	import { clsx } from 'clsx';
	import type { Snippet } from 'svelte';

	/**
	 * Reusable card container component
	 * Provides consistent styling for card-based layouts
	 */
	interface Props {
		/** Visual style variant */
		variant?: 'default' | 'elevated' | 'outlined' | 'filled';
		/** Padding size */
		padding?: 'none' | 'sm' | 'md' | 'lg';
		/** Additional CSS classes to apply */
		className?: string;
		/** Whether the card should have hover effects */
		hoverable?: boolean;
		/** Whether the card is clickable */
		clickable?: boolean;
		/** Whether the card is selected */
		selected?: boolean;
		/** Whether the card is disabled */
		disabled?: boolean;
		/** Whether the card is in loading state */
		loading?: boolean;
		/** Whether the card is in error state */
		error?: boolean;
		/** Error message to display */
		errorMessage?: string;
		/** Click handler */
		onclick?: (event: MouseEvent) => void;
		/** ARIA label */
		ariaLabel?: string;
		/** ARIA described by */
		ariaDescribedBy?: string;
		/** Header content */
		header?: Snippet;
		/** Main content */
		children?: Snippet;
		/** Footer content */
		footer?: Snippet;
		/** Actions content */
		actions?: Snippet;
	}

	const {
		variant = 'default',
		padding = 'md',
		className = '',
		hoverable = false,
		clickable = false,
		selected = false,
		disabled = false,
		loading = false,
		error = false,
		errorMessage = '',
		onclick,
		ariaLabel,
		ariaDescribedBy,
		header,
		children,
		footer,
		actions
	}: Props = $props();

	// Compute effective disabled state
	const isDisabled = $derived(disabled || loading);
	const isClickable = $derived(clickable && !isDisabled);

	// Handle click events
	function handleClick(event: MouseEvent): void {
		if (!isClickable) {
			return;
		}
		onclick?.(event);
	}

	// Handle keyboard interactions for accessibility
	function handleKeyDown(event: KeyboardEvent): void {
		if (isClickable && (event.key === 'Enter' || event.key === ' ')) {
			event.preventDefault();
			onclick?.(event as any as MouseEvent);
		}
	}

	// Build class names
	const variantClasses = {
		default: 'card-default bg-white border border-gray-200',
		elevated: 'card-elevated bg-white shadow-lg',
		outlined: 'card-outlined bg-transparent border-2 border-gray-300',
		filled: 'card-filled bg-gray-100'
	};

	const paddingClasses = {
		none: 'p-0',
		sm: 'p-sm p-3',
		md: 'p-md p-6',
		lg: 'p-lg p-8'
	};

	const cardClasses = $derived(
		clsx(
			'card rounded-lg transition-all duration-200',
			variantClasses[variant],
			paddingClasses[padding],
			{
				'hoverable hover:shadow-xl hover:scale-[1.02]': hoverable,
				'clickable cursor-pointer': isClickable,
				'selected ring-2 ring-primary-500': selected,
				'disabled opacity-50 cursor-not-allowed': isDisabled,
				'loading': loading,
				'error border-red-500': error
			},
			className
		)
	);
</script>

<div
	class={cardClasses}
	role={clickable ? 'button' : undefined}
	tabindex={isClickable ? 0 : undefined}
	aria-label={ariaLabel}
	aria-describedby={ariaDescribedBy}
	aria-selected={selected ? 'true' : undefined}
	aria-disabled={isDisabled ? 'true' : undefined}
	onclick={handleClick}
	onkeydown={handleKeyDown}
>
	{#if loading}
		<div class="loading-spinner flex items-center justify-center p-8">
			<span class="text-2xl animate-spin">⏳</span>
		</div>
	{:else if error && errorMessage}
		<div class="error-message text-red-600 p-4">
			{errorMessage}
		</div>
	{:else}
		{#if header}
			<div class="card-header mb-4">
				{@render header()}
			</div>
		{/if}

		{#if children}
			<div class="card-content">
				{@render children()}
			</div>
		{/if}

		{#if footer}
			<div class="card-footer mt-4 pt-4 border-t border-gray-200">
				{@render footer()}
			</div>
		{/if}

		{#if actions}
			<div class="card-actions mt-4 flex justify-end gap-2">
				{@render actions()}
			</div>
		{/if}
	{/if}
</div>

<style>
	.card {
		position: relative;
	}

	/* Animation for loading spinner */
	@keyframes spin {
		from {
			transform: rotate(0deg);
		}
		to {
			transform: rotate(360deg);
		}
	}

	.animate-spin {
		animation: spin 1s linear infinite;
	}
</style>