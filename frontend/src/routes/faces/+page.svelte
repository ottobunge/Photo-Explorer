<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { client, API_HOST } from '$lib/api/client';
	import FaceTabs from '$lib/features/faces/components/FaceTabs.svelte';
	import { FaceGraph, faceGraphStore, ClusterMergeModal, faceSelectionStore } from '$lib/features/faces';
	import type { FaceClusterType } from '$lib/features/faces';

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

	type TabType = 'list' | 'graph';

	// Derive activeTab from URL - single source of truth (fixes race condition)
	const activeTab = $derived<TabType>(
		$page.url.searchParams.get('view') === 'graph' ? 'graph' : 'list'
	);

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
	let showMergeModal = $state(false);
	let operationInProgress = $state(false);

	const totalPages = $derived(Math.ceil(total / perPage));

	// Access store state reactively
	// Use $derived to track store state changes
	const editMode = $derived(faceSelectionStore.editMode);
	const selectedClusterIds = $derived(faceSelectionStore.selectedClusterIds);
	const selectedClusterCount = $derived(faceSelectionStore.selectedClusterCount);
	const canMerge = $derived(selectedClusterCount >= 2);

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

	// Get selected clusters from the current page
	const selectedClusters = $derived.by<FaceClusterType[]>(() => {
		return sortedClusters
			.filter((c) => selectedClusterIds.has(c.id))
			.map((c) => {
				const cluster: FaceClusterType = {
					id: c.id,
					faceCount: c.face_count,
					photoCount: c.photo_count
				};
				if (c.name !== null) {
					cluster.name = c.name;
				}
				if (c.representative_face) {
					cluster.representativeFace = {
						id: c.representative_face.id,
						cropUrl: c.representative_face.crop_url
					};
				}
				return cluster;
			});
	});

	// Load graph data when switching to graph tab
	$effect(() => {
		if (activeTab === 'graph') {
			void faceGraphStore.loadGraph();
		}
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

	function toggleEditMode(): void {
		faceSelectionStore.toggleEditMode();
	}

	function toggleClusterSelection(clusterId: string): void {
		faceSelectionStore.toggleCluster(clusterId);
	}

	function handleMergeClick(): void {
		if (!canMerge) {return;}
		showMergeModal = true;
	}

	async function handleMerged(): Promise<void> {
		showMergeModal = false;
		operationInProgress = true;
		try {
			await loadClusters();
		} catch (err) {
			console.error('Failed to reload clusters:', err);
			error = err instanceof Error ? err.message : 'Failed to reload clusters';
		} finally {
			operationInProgress = false;
		}
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

	<!-- Tab Navigation -->
	<FaceTabs {activeTab} />

	<!-- List View -->
	{#if activeTab === 'list'}
	<!-- Filters and Sorting -->
	<div class="mb-6 flex flex-wrap items-center gap-4 justify-between">
		<div class="flex flex-wrap items-center gap-4">
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

		<!-- Edit Mode Toggle -->
		<button
			onclick={toggleEditMode}
			class="px-4 py-2 rounded-lg transition-colors"
			class:bg-blue-500={editMode}
			class:text-white={editMode}
			class:hover:bg-blue-600={editMode}
			class:border={!editMode}
			class:border-gray-300={!editMode}
			class:hover:bg-gray-50={!editMode}
		>
			{editMode ? 'Done' : 'Edit'}
		</button>
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
					onclick={() => { editMode ? toggleClusterSelection(cluster.id) : navigateToCluster(cluster.id); }}
					disabled={operationInProgress}
					class="group relative block rounded-lg border bg-white p-3 transition-all text-left w-full"
					class:border-gray-200={!selectedClusterIds.has(cluster.id)}
					class:hover:shadow-md={!editMode}
					class:border-4={selectedClusterIds.has(cluster.id)}
					class:border-blue-500={selectedClusterIds.has(cluster.id)}
					class:bg-blue-50={selectedClusterIds.has(cluster.id)}
				>
					<!-- Checkbox overlay in edit mode -->
					{#if editMode}
						<div
							class="absolute top-2 right-2 w-6 h-6 rounded-full flex items-center justify-center z-10 transition-colors"
							class:bg-blue-500={selectedClusterIds.has(cluster.id)}
							class:bg-white={!selectedClusterIds.has(cluster.id)}
							class:border-2={!selectedClusterIds.has(cluster.id)}
							class:border-gray-300={!selectedClusterIds.has(cluster.id)}
						>
							{#if selectedClusterIds.has(cluster.id)}
								<svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
									<path
										fill-rule="evenodd"
										d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
										clip-rule="evenodd"
									/>
								</svg>
							{/if}
						</div>
					{/if}

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
					onclick={() => { goToPage(currentPage - 1); }}
				>
					Previous
				</button>

				<span class="text-sm text-gray-600">
					Page {currentPage} of {totalPages}
				</span>

				<button
					class="px-3 py-1 rounded border border-gray-300 text-sm disabled:opacity-50"
					disabled={currentPage === totalPages}
					onclick={() => { goToPage(currentPage + 1); }}
				>
					Next
				</button>
			</div>
		{/if}

		<!-- Floating Action Bar (shown when in edit mode and clusters are selected) -->
		{#if editMode && selectedClusterCount > 0}
			<div
				class="fixed bottom-8 left-1/2 -translate-x-1/2 z-40 bg-white rounded-full shadow-2xl border border-gray-200 px-6 py-4"
			>
				<div class="flex items-center gap-6">
					<!-- Selection count -->
					<div class="flex items-center gap-2">
						<span class="text-sm font-medium text-gray-900">
							{selectedClusterCount} selected
						</span>
					</div>

					<div class="h-6 w-px bg-gray-300"></div>

					<!-- Actions -->
					<div class="flex items-center gap-3">
						<button
							type="button"
							onclick={handleMergeClick}
							disabled={!canMerge || operationInProgress}
							class="px-4 py-2 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
							title={canMerge ? 'Merge selected clusters' : 'Select at least 2 clusters to merge'}
						>
							Merge
						</button>
					</div>
				</div>
			</div>
		{/if}

		<!-- Cluster Merge Modal -->
		{#if showMergeModal}
			<ClusterMergeModal
				clusters={selectedClusters}
				on:close={() => (showMergeModal = false)}
				on:merged={handleMerged}
			/>
		{/if}
	{/if}
	{:else}
		<!-- Graph View -->
		<div role="tabpanel" id="graph-panel" aria-labelledby="graph-tab">
			<FaceGraph />
		</div>
	{/if}
</div>
