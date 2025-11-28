<script lang="ts">
	interface Props {
		size?: 'sm' | 'md' | 'lg';
	}

	const { size = 'md' }: Props = $props();

	const sizes = {
		sm: 'h-4 w-4',
		md: 'h-6 w-6',
		lg: 'h-8 w-8'
	};
</script>

<div class="flex items-center justify-center" data-testid="loading-spinner">
	<div
		class="animate-spin rounded-full border-2 border-gray-300 border-t-primary-600 {sizes[size]}"
	></div>
</div>
