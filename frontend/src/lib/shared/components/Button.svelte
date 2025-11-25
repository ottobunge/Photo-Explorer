<script lang="ts">
	import { clsx } from 'clsx';

	export let variant: 'primary' | 'secondary' | 'ghost' = 'primary';
	export let size: 'sm' | 'md' | 'lg' = 'md';
	export let disabled = false;
	export let type: 'button' | 'submit' | 'reset' = 'button';

	const baseClasses =
		'inline-flex items-center justify-center font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 rounded-lg';

	const variants = {
		primary: 'bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500',
		secondary: 'border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 focus:ring-primary-500',
		ghost: 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
	};

	const sizes = {
		sm: 'px-3 py-1.5 text-sm',
		md: 'px-4 py-2',
		lg: 'px-6 py-3 text-lg'
	};
</script>

<button
	{type}
	{disabled}
	class={clsx(baseClasses, variants[variant], sizes[size])}
	on:click
>
	<slot />
</button>
