<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { client, API_HOST } from '$lib/api/client';

	interface RepresentativeFace {
		id: string;
		crop_url: string;
	}

	interface FaceCluster {
		id: string;
		name: string | null;
		face_count: number;
		photo_count: number;
		representative_face: RepresentativeFace | null;
	}

	interface ClustersResponse {
		clusters: FaceCluster[];
	}

	let clusters = $state<FaceCluster[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let showNamedOnly = $state(false);
	let showUnnamedOnly = $state(false);
	let currentPage = $state(1);
	let perPage = $state(30);
	let total = $state(0);
	let sortBy = $state<'face_count' | 'photo_count' | 'name'>('face_count');
	let sortOrder = $state<'asc' | 'desc'>('desc');

	const totalPages = $derived(Math.ceil(total / perPage));

	// Sort clusters client-side (API doesn't support sorting yet)
	const sortedClusters = $derived.by(() => {
		const sorted = [...clusters];
		sorted.sort((a, b) => {
			let comparison = 0;
			if (sortBy === 'face_count') {
				comparison = a.face_count - b.face_count;
			} else if (sortBy === 'photo_count') {
				comparison = a.photo_count - b.photo_count;
			} else if (sortBy === 'name') {
				const nameA = a.name ?? '';
				const nameB = b.name ?? '';
				comparison = nameA.localeCompare(nameB);
			}
			return sortOrder === 'desc' ? -comparison : comparison;
		});
		return sorted;
	});

	onMount(() => {
		const urlPage = $page.url.searchParams.get('page');
		const urlPerPage = $page.url.searchParams.get('per_page');
		const urlNamed = $page.url.searchParams.get('named');
		const urlUnnamed = $page.url.searchParams.get('unnamed');
		const urlSortBy = $page.url.searchParams.get('sort_by');
		const urlSortOrder = $page.url.searchParams.get('sort_order');

		if (urlPage !== null) {
			const parsed = parseInt(urlPage, 10);
			if (!isNaN(parsed) && parsed >= 1) {
				currentPage = parsed;
			}
		}
		if (urlPerPage !== null) {
			const parsed = parseInt(urlPerPage, 10);
			if (!isNaN(parsed) && parsed >= 1 && parsed <= 100) {
				perPage = parsed;
			}
		}
		if (urlNamed === 'true') {
			showNamedOnly = true;
		}
		if (urlUnnamed === 'true') {
			showUnnamedOnly = true;
		}
		if (urlSortBy === 'face_count' || urlSortBy === 'photo_count' || urlSortBy === 'name') {
			sortBy = urlSortBy;
		}
		if (urlSortOrder === 'asc' || urlSortOrder === 'desc') {
			sortOrder = urlSortOrder;
		}

		void loadClusters();
	});

	function updateUrl(): void {
		const params = new URLSearchParams();

		if (currentPage > 1) {
			params.set('page', currentPage.toString());
		}
		if (perPage !== 30) {
			params.set('per_page', perPage.toString());
		}
		if (showNamedOnly) {
			params.set('named', 'true');
		}
		if (showUnnamedOnly) {
			params.set('unnamed', 'true');
		}
		if (sortBy !== 'face_count') {
			params.set('sort_by', sortBy);
		}
		if (sortOrder !== 'desc') {
			params.set('sort_order', sortOrder);
		}

		const newUrl = params.toString() ? `?${params.toString()}` : '/faces';
		void goto(newUrl, { replaceState: true, keepFocus: true });
	}

	async function loadClusters(): Promise<void> {
		loading = true;
		error = null;
		try {
			const queryParams = new URLSearchParams({
				page: currentPage.toString(),
				per_page: perPage.toString()
			});
			if (showNamedOnly) {
				queryParams.set('named_only', 'true');
			}
			if (showUnnamedOnly) {
				queryParams.set('unnamed_only', 'true');
			}
			const res = await client.get<ClustersResponse>(
				`/faces/clusters?${queryParams.toString()}`
			);
			if (res.success && res.data) {
				clusters = res.data.clusters;
				total = res.meta?.total ?? clusters.length;
			}
		} catch (err: unknown) {
			console.error('Failed to load face clusters:', err);
			error = err instanceof Error ? err.message : 'Failed to load clusters';
		} finally {
			loading = false;
		}
		updateUrl();
	}

	function goToPage(newPage: number): void {
		if (newPage >= 1 && newPage <= totalPages) {
			currentPage = newPage;
			void loadClusters();
		}
	}

	function handleFilterChange(): void {
		// Ensure mutually exclusive filters
		if (showNamedOnly && showUnnamedOnly) {
			showUnnamedOnly = false;
		}
		currentPage = 1;
		void loadClusters();
	}

	function handleSortChange(): void {
		// Sorting is done client-side, just update URL
		updateUrl();
	}

	function navigateToCluster(clusterId: string): void {
		void goto(`/faces/${clusterId}`);
	}
</script>

<svelte:head>
	<title>Face Explorer - Photo Explorer</title>
</svelte:head>

<div class="p-8">
	<header class="mb-8">
		<h1 class="text-3xl font-bold text-gray-900">Face Explorer</h1>
		<p class="mt-2 text-gray-600">Tag and organize faces in your photos</p>
	</header>

	<!-- Filters and Sorting -->
	<div class="mb-6 flex flex-wrap items-center gap-4">
		<label class="flex items-center gap-2">
			<input
				type="checkbox"
				bind:checked={showNamedOnly}
				onchange={handleFilterChange}
				class="rounded"
			/>
			<span class="text-sm text-gray-600">Named only</span>
		</label>
		<label class="flex items-center gap-2">
			<input
				type="checkbox"
				bind:checked={showUnnamedOnly}
				onchange={handleFilterChange}
				class="rounded"
			/>
			<span class="text-sm text-gray-600">Unnamed only</span>
		</label>

		<div class="h-6 w-px bg-gray-300"></div>

		<label class="flex items-center gap-2">
			<span class="text-sm text-gray-600">Sort by:</span>
			<select
				bind:value={sortBy}
				onchange={handleSortChange}
				class="rounded border border-gray-300 px-2 py-1 text-sm"
			>
				<option value="face_count">Face Count</option>
				<option value="photo_count">Photo Count</option>
				<option value="name">Name</option>
			</select>
		</label>
		<label class="flex items-center gap-2">
			<span class="text-sm text-gray-600">Order:</span>
			<select
				bind:value={sortOrder}
				onchange={handleSortChange}
				class="rounded border border-gray-300 px-2 py-1 text-sm"
			>
				<option value="desc">Descending</option>
				<option value="asc">Ascending</option>
			</select>
		</label>
	</div>

	{#if error}
		<div class="mb-4 p-4 bg-red-50 text-red-700 rounded-lg">{error}</div>
	{/if}

	{#if loading}
		<div class="text-center py-12 text-gray-500">Loading face clusters...</div>
	{:else if sortedClusters.length === 0}
		<div class="card p-12 text-center">
			<div class="mb-4 text-4xl">&#128101;</div>
			<p class="text-gray-500">No face clusters yet</p>
			<p class="mt-2 text-sm text-gray-400">
				Upload photos with faces to start grouping. Face detection runs automatically when photos
				are processed.
			</p>
		</div>
	{:else}
		<div class="mb-4 text-sm text-gray-500">
			Showing {sortedClusters.length} of {total} clusters
		</div>

		<div class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
			{#each sortedClusters as cluster (cluster.id)}
				<button
					onclick={() => navigateToCluster(cluster.id)}
					class="group block rounded-lg border border-gray-200 bg-white p-3 transition-shadow hover:shadow-md text-left w-full"
				>
					<div
						class="mx-auto mb-2 aspect-square w-24 overflow-hidden rounded-full bg-gray-100"
					>
						{#if cluster.representative_face}
							<img
								src="{API_HOST}{cluster.representative_face.crop_url}"
								alt={cluster.name ?? 'Unknown person'}
								class="h-full w-full object-cover"
								loading="lazy"
							/>
						{:else}
							<div class="flex h-full items-center justify-center text-2xl text-gray-300">
								&#128100;
							</div>
						{/if}
					</div>
					<div class="text-center">
						<p class="font-medium text-gray-900 group-hover:text-blue-600">
							{cluster.name ?? 'Unknown'}
						</p>
						<p class="text-sm text-gray-500">{cluster.face_count} faces</p>
						<p class="text-xs text-gray-400">{cluster.photo_count} photos</p>
					</div>
				</button>
			{/each}
		</div>

		<!-- Pagination -->
		{#if totalPages > 1}
			<div class="mt-8 flex items-center justify-center gap-2">
				<button
					class="px-3 py-1 rounded border border-gray-300 text-sm disabled:opacity-50"
					disabled={currentPage === 1}
					onclick={() => goToPage(currentPage - 1)}
				>
					Previous
				</button>

				<span class="text-sm text-gray-600">
					Page {currentPage} of {totalPages}
				</span>

				<button
					class="px-3 py-1 rounded border border-gray-300 text-sm disabled:opacity-50"
					disabled={currentPage === totalPages}
					onclick={() => goToPage(currentPage + 1)}
				>
					Next
				</button>
			</div>
		{/if}
	{/if}
</div>
