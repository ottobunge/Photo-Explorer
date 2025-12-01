<script lang="ts">
	import { clsx } from 'clsx';
	import type { Snippet } from 'svelte';

	interface Props {
		variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
		size?: 'sm' | 'md' | 'lg';
		disabled?: boolean;
		loading?: boolean;
		fullWidth?: boolean;
		className?: string;
		type?: 'button' | 'submit' | 'reset';
		onclick?: (event: MouseEvent) => void;
		icon?: string;
		iconPosition?: 'left' | 'right';
		ariaLabel?: string;
		ariaDescribedBy?: string;
		children?: Snippet | string;
	}

	const {
		variant = 'primary',
		size = 'md',
		disabled = false,
		loading = false,
		fullWidth = false,
		className = '',
		type = 'button',
		onclick,
		icon,
		iconPosition = 'left',
		ariaLabel,
		ariaDescribedBy,
		children
	}: Props = $props();

	// Compute whether button should be disabled
	const isDisabled = $derived(disabled || loading);

	// Handle click events - prevent when disabled or loading
	function handleClick(event: MouseEvent): void {
		if (isDisabled) {
			event.preventDefault();
			event.stopPropagation();
			return;
		}
		onclick?.(event);
	}

	// Handle keyboard interactions for better accessibility
	function handleKeyDown(event: KeyboardEvent): void {
		if ((event.key === 'Enter' || event.key === ' ') && !isDisabled) {
			event.preventDefault();
			onclick?.(event as any as MouseEvent);
		}
	}

	const baseClasses =
		'inline-flex items-center justify-center font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 rounded-lg';

	const variantClasses = {
		primary: 'btn-primary bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500',
		secondary: 'btn-secondary border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 focus:ring-primary-500',
		ghost: 'btn-ghost text-gray-600 hover:bg-gray-100 hover:text-gray-900',
		danger: 'btn-danger bg-red-600 text-white hover:bg-red-700 focus:ring-red-500'
	};

	const sizeClasses = {
		sm: 'btn-sm px-3 py-1.5 text-sm',
		md: 'btn-md px-4 py-2',
		lg: 'btn-lg px-6 py-3 text-lg'
	};

	const buttonClasses = $derived(
		clsx(
			baseClasses,
			variantClasses[variant],
			sizeClasses[size],
			{
				'disabled': isDisabled,
				'loading': loading,
				'w-full': fullWidth,
				'opacity-50 cursor-not-allowed': isDisabled
			},
			className
		)
	);
</script>

<button
	{type}
	disabled={isDisabled}
	class={buttonClasses}
	onclick={handleClick}
	onkeydown={handleKeyDown}
	aria-disabled={isDisabled ? 'true' : undefined}
	aria-busy={loading ? 'true' : undefined}
	aria-label={ariaLabel}
	aria-describedby={ariaDescribedBy}
>
	{#if loading}
		<span class="loading-spinner mr-2">⏳</span>
		<span>Loading...</span>
	{:else}
		{#if icon && iconPosition === 'left'}
			<span class="btn-icon mr-2">{icon}</span>
		{/if}

		{#if typeof children === 'string'}
			{children}
		{:else if children}
			{@render children()}
		{/if}

		{#if icon && iconPosition === 'right'}
			<span class="btn-icon ml-2">{icon}</span>
		{/if}
	{/if}
</button>
