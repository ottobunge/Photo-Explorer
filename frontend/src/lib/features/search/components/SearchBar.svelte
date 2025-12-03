<script lang="ts">
	interface Props {
		query?: string;
		loading?: boolean;
		disabled?: boolean;
		placeholder?: string;
		debounceMs?: number;
		maxLength?: number;
		suggestions?: string[];
		showSuggestions?: boolean;
		onSearch?: (query: string) => void;
		onClear?: () => void;
		onSuggestionSelect?: (suggestion: string) => void;
	}

	const {
		query,
		loading = false,
		disabled = false,
		placeholder = 'Search photos... (e.g., "sunset at the beach")',
		debounceMs = 300,
		maxLength = 100,
		suggestions = [],
		showSuggestions = false,
		onSearch,
		onClear,
		onSuggestionSelect
	}: Props = $props();

	let debounceTimer: number | undefined = undefined;
	let selectedSuggestionIndex = $state(-1);
	let localShowSuggestions = $state(showSuggestions);
	let inputElement: HTMLInputElement | null = null;

	// Ensure we start with the correct showSuggestions value
	$effect.pre(() => {
		localShowSuggestions = showSuggestions;
	});
	// Local copy for binding - we'll sync with query via effects
	// Enforce max length on initialization
	const initialQuery = query ?? '';
	let localQuery = $state(maxLength && initialQuery.length > maxLength ? initialQuery.substring(0, maxLength) : initialQuery);

	// Sync external query changes to local state
	$effect(() => {
		const newQuery = query ?? '';
		const truncatedQuery = maxLength && newQuery.length > maxLength ? newQuery.substring(0, maxLength) : newQuery;
		localQuery = truncatedQuery;
	});

	// Calculate whether to show the clear button
	const showClearButton = $derived(localQuery.length > 0);

	// Calculate if input should be disabled
	const isDisabled = $derived(disabled || loading);

	// Handle input changes with debouncing
	function handleInput(e: Event): void {
		const target = e.target as HTMLInputElement;
		let newValue = target.value;

		// Enforce max length
		if (maxLength && newValue.length > maxLength) {
			target.value = newValue.substring(0, maxLength);
			newValue = target.value;
		}

		// Update local query - will sync to bindable via effect
		localQuery = newValue;
		selectedSuggestionIndex = -1;

		// Clear existing debounce timer
		if (debounceTimer !== undefined) {
			clearTimeout(debounceTimer);
		}

		// Set new debounce timer
		debounceTimer = window.setTimeout(() => {
			if (onSearch) {
				onSearch(newValue);
			}
		}, debounceMs);
	}

	function handleFormSubmit(e: Event): void {
		e.preventDefault();

		// Cancel any pending debounce
		if (debounceTimer !== undefined) {
			clearTimeout(debounceTimer);
			debounceTimer = undefined;
		}

		// Call onSearch immediately
		if (onSearch) {
			onSearch(query);
		}
	}

	function handleClear(): void {
		localQuery = '';
		selectedSuggestionIndex = -1;
		onClear?.();
	}

	function handleKeydown(e: KeyboardEvent): void {
		if (!localShowSuggestions || suggestions.length === 0) {
			return;
		}

		switch (e.key) {
			case 'ArrowDown':
				e.preventDefault();
				selectedSuggestionIndex = Math.min(selectedSuggestionIndex + 1, suggestions.length - 1);
				break;

			case 'ArrowUp':
				e.preventDefault();
				selectedSuggestionIndex = Math.max(selectedSuggestionIndex - 1, -1);
				break;

			case 'Enter':
				if (selectedSuggestionIndex >= 0) {
					e.preventDefault();
					const selected = suggestions[selectedSuggestionIndex];
					if (selected) {
						handleSuggestionClick(selected);
					}
				}
				break;

			case 'Escape':
				localShowSuggestions = false;
				break;
		}
	}

	function handleSuggestionClick(suggestion: string): void {
		localQuery = suggestion;
		localShowSuggestions = false;
		selectedSuggestionIndex = -1;
		onSuggestionSelect?.(suggestion);
		if (onSearch) {
			onSearch(suggestion);
		}
	}

	// Cleanup on unmount
	$effect(() => {
		return () => {
			if (debounceTimer !== undefined) {
				clearTimeout(debounceTimer);
			}
		};
	});
</script>

<div class="relative" data-testid="search-bar">
	<form onsubmit={handleFormSubmit} class="flex gap-2">
		<div class="relative flex-1">
			<input
				type="search"
				bind:value={localQuery}
				bind:this={inputElement}
				{placeholder}
				maxlength={maxLength}
				class="input pl-10 pr-10"
				onkeydown={handleKeydown}
				oninput={handleInput}
				disabled={isDisabled}
				role="searchbox"
				aria-label="Search photos"
				aria-autocomplete="list"
				aria-controls={suggestions.length > 0 ? 'search-suggestions' : undefined}
			/>
			<span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
				&#128269;
			</span>

			{#if showClearButton}
				<button
					type="button"
					class="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-200 rounded text-gray-600"
					onclick={handleClear}
					disabled={isDisabled}
					aria-label="Clear search"
				>
					✕
				</button>
			{/if}
		</div>

		<button
			type="submit"
			class="btn-primary"
			disabled={isDisabled}
			aria-busy={loading}
		>
			<span class={loading ? 'inline' : 'hidden'}>
				<span class="loading-spinner inline-block mr-2"></span>
			</span>
			{loading ? 'Searching' : 'Search'}
		</button>
	</form>

	<div
		class="absolute top-full mt-1 w-full bg-white border border-gray-200 rounded shadow-lg z-10 {!localShowSuggestions ? 'hidden' : ''}"
		data-testid="search-suggestions"
		role="listbox"
		id="search-suggestions"
	>
		{#each suggestions as suggestion, index (suggestion)}
			<button
				type="button"
				class="w-full text-left px-4 py-2 hover:bg-gray-100 {selectedSuggestionIndex === index ? 'bg-gray-100' : ''}"
				onclick={() => handleSuggestionClick(suggestion)}
				role="option"
				aria-selected={selectedSuggestionIndex === index ? 'true' : 'false'}
			>
				{suggestion}
			</button>
		{/each}
	</div>

	{#if loading}
		<div aria-live="polite" aria-atomic="true" class="sr-only">
			Searching for photos...
		</div>
	{/if}
</div>

<style>
	.loading-spinner {
		display: inline-block;
		width: 16px;
		height: 16px;
		border: 2px solid #f3f3f3;
		border-top: 2px solid #3498db;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		0% {
			transform: rotate(0deg);
		}
		100% {
			transform: rotate(360deg);
		}
	}

	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border-width: 0;
	}
</style>
