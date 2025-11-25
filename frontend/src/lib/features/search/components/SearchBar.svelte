<script lang="ts">
	interface Props {
		query: string;
		loading?: boolean;
		placeholder?: string;
		onSearch?: () => void;
	}

	let {
		query = $bindable(''),
		loading = false,
		placeholder = 'Search photos... (e.g., "sunset at the beach")',
		onSearch
	}: Props = $props();

	function handleSubmit(): void {
		if (query.trim()) {
			onSearch?.();
		}
	}

	function handleKeydown(e: KeyboardEvent): void {
		if (e.key === 'Enter') {
			handleSubmit();
		}
	}
</script>

<div class="flex gap-2" data-testid="search-bar">
	<div class="relative flex-1">
		<input
			type="text"
			bind:value={query}
			{placeholder}
			class="input pl-10"
			onkeydown={handleKeydown}
			disabled={loading}
			data-testid="search-input"
		/>
		<span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">&#128269;</span>
	</div>
	<button
		type="button"
		class="btn-primary"
		onclick={handleSubmit}
		disabled={loading || !query.trim()}
		data-testid="search-button"
	>
		{loading ? 'Searching...' : 'Search'}
	</button>
</div>
