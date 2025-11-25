<script lang="ts">
	let showFilters = false;
	let startDate = '';
	let endDate = '';
	let hasFaces = false;
	let isIndoor: boolean | null = null;
</script>

<div data-testid="search-filters">
	<button
		type="button"
		class="btn-ghost text-sm"
		on:click={() => (showFilters = !showFilters)}
		data-testid="filter-toggle"
	>
		{showFilters ? '▼' : '▶'} Filters
	</button>

	{#if showFilters}
		<div class="mt-4 grid grid-cols-1 gap-4 rounded-lg border border-gray-200 bg-white p-4 md:grid-cols-4">
			<div>
				<label for="date-from" class="mb-1 block text-sm font-medium text-gray-700">From Date</label>
				<input
					id="date-from"
					type="date"
					bind:value={startDate}
					class="input"
					data-testid="date-from"
				/>
			</div>

			<div>
				<label for="date-to" class="mb-1 block text-sm font-medium text-gray-700">To Date</label>
				<input
					id="date-to"
					type="date"
					bind:value={endDate}
					class="input"
					data-testid="date-to"
				/>
			</div>

			<div>
				<label for="location" class="mb-1 block text-sm font-medium text-gray-700">Location</label>
				<select id="location" bind:value={isIndoor} class="input">
					<option value={null}>Any</option>
					<option value={false}>Outdoor</option>
					<option value={true}>Indoor</option>
				</select>
			</div>

			<div class="flex items-end">
				<label class="flex items-center gap-2">
					<input type="checkbox" bind:checked={hasFaces} class="rounded" />
					<span class="text-sm text-gray-700">Has faces</span>
				</label>
			</div>
		</div>
	{/if}
</div>
