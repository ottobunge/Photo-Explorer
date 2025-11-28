<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { AlbumGrid, CreateAlbumModal } from '$features/albums';
	import type { Album } from '$features/albums/types';
	import { client } from '$lib/api/client';

	interface AlbumsResponse {
		albums: Album[];
	}

	let albums = $state<Album[]>([]);
	let loading = $state(false);
	let showCreateModal = $state(false);
	let currentPage = $state(1);
	let perPage = $state(20);
	let total = $state(0);
	let sortBy = $state<'name' | 'created_at' | 'photo_count'>('created_at');
	let sortOrder = $state<'asc' | 'desc'>('desc');

	const totalPages = $derived(Math.ceil(total / perPage));

	onMount(() => {
		const urlPage = $page.url.searchParams.get('page');
		const urlPerPage = $page.url.searchParams.get('per_page');
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
		if (urlSortBy === 'name' || urlSortBy === 'created_at' || urlSortBy === 'photo_count') {
			sortBy = urlSortBy;
		}
		if (urlSortOrder === 'asc' || urlSortOrder === 'desc') {
			sortOrder = urlSortOrder;
		}

		void loadAlbums();
	});

	function updateUrl(): void {
		const params = new URLSearchParams();

		if (currentPage > 1) {
			params.set('page', currentPage.toString());
		}
		if (perPage !== 20) {
			params.set('per_page', perPage.toString());
		}
		if (sortBy !== 'created_at') {
			params.set('sort_by', sortBy);
		}
		if (sortOrder !== 'desc') {
			params.set('sort_order', sortOrder);
		}

		const newUrl = params.toString() ? `?${params.toString()}` : '/albums';
		void goto(newUrl, { replaceState: true, keepFocus: true });
	}

	async function loadAlbums(): Promise<void> {
		loading = true;
		try {
			const queryParams = new URLSearchParams({
				page: currentPage.toString(),
				per_page: perPage.toString(),
				sort_by: sortBy,
				sort_order: sortOrder
			});
			const res = await client.get<AlbumsResponse>(`/albums?${queryParams.toString()}`);
			if (res.success) {
				albums = res.data.albums;
				total = res.meta?.total ?? albums.length;
			}
		} catch (err: unknown) {
			console.error('Failed to load albums:', err);
		} finally {
			loading = false;
		}
		updateUrl();
	}

	function goToPage(newPage: number): void {
		if (newPage >= 1 && newPage <= totalPages) {
			currentPage = newPage;
			void loadAlbums();
		}
	}

	function handleSortChange(): void {
		currentPage = 1;
		void loadAlbums();
	}

	function handleAlbumCreated(): void {
		showCreateModal = false;
		void loadAlbums();
	}

	function closeModal(): void {
		showCreateModal = false;
	}
</script>

<svelte:head>
	<title>Albums - Photo Explorer</title>
</svelte:head>

<div class="p-8">
	<header class="mb-8 flex items-center justify-between">
		<div>
			<h1 class="text-3xl font-bold text-gray-900">Albums</h1>
			<p class="mt-2 text-gray-600">Organize your photos into collections</p>
		</div>
		<button type="button" class="btn-primary" onclick={() => (showCreateModal = true)}>
			Create Album
		</button>
	</header>

	<!-- Sorting controls -->
	<div class="mb-6 flex items-center gap-4">
		<label class="flex items-center gap-2">
			<span class="text-sm text-gray-600">Sort by:</span>
			<select
				bind:value={sortBy}
				onchange={handleSortChange}
				class="rounded border border-gray-300 px-2 py-1 text-sm"
			>
				<option value="created_at">Date Created</option>
				<option value="name">Name</option>
				<option value="photo_count">Photo Count</option>
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

	{#if loading}
		<div class="text-center py-12 text-gray-500">Loading albums...</div>
	{:else}
		<AlbumGrid {albums} />

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
	{/if}

	{#if showCreateModal}
		<CreateAlbumModal onClose={closeModal} onCreated={handleAlbumCreated} />
	{/if}
</div>
