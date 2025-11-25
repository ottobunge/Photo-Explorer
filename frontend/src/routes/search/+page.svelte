<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { SearchBar } from '$features/search';
	import { client, API_HOST } from '$lib/api/client';

	interface Photo {
		id: string;
		filename: string;
		thumbnail_url: string | null;
		connector_type: string;
		width: number | null;
		height: number | null;
		taken_at: string | null;
		created_at: string;
		score?: number;
	}

	interface PhotosResponse {
		photos: Photo[];
	}

	interface SearchResultItem {
		photo: Photo;
		score: number;
	}

	interface SearchResponse {
		results: SearchResultItem[];
	}

	interface Connector {
		id: string;
		type: string;
		name: string;
	}

	interface ConnectorsResponse {
		connectors: Connector[];
	}

	interface Album {
		id: string;
		name: string;
	}

	interface AlbumsResponse {
		albums: Album[];
	}

	let query = $state('');
	let photos = $state<Photo[]>([]);
	let loading = $state(false);
	let currentPage = $state(1);
	let perPage = $state(24);
	let total = $state(0);
	let isSearchMode = $state(false);

	// Scope filters
	let connectors = $state<Connector[]>([]);
	let albums = $state<Album[]>([]);
	let selectedConnectorId = $state<string | null>(null);
	let selectedAlbumId = $state<string | null>(null);

	const totalPages = $derived(Math.ceil(total / perPage));

	// Initialize from URL params
	onMount(() => {
		const urlQuery = $page.url.searchParams.get('q');
		const urlPage = $page.url.searchParams.get('page');
		const urlPerPage = $page.url.searchParams.get('per_page');
		const urlConnector = $page.url.searchParams.get('connector_id');
		const urlAlbum = $page.url.searchParams.get('album_id');

		if (urlQuery !== null) {
			query = urlQuery;
			isSearchMode = true;
		}
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
		if (urlConnector !== null) {
			selectedConnectorId = urlConnector;
		}
		if (urlAlbum !== null) {
			selectedAlbumId = urlAlbum;
		}

		// Load filter options
		void loadFilterOptions();

		if (isSearchMode && query.trim()) {
			void handleSearch();
		} else {
			void loadPhotos();
		}
	});

	async function loadFilterOptions(): Promise<void> {
		try {
			const [connectorsRes, albumsRes] = await Promise.all([
				client.get<ConnectorsResponse>('/connectors'),
				client.get<AlbumsResponse>('/albums')
			]);
			if (connectorsRes.success && connectorsRes.data) {
				connectors = connectorsRes.data.connectors;
			}
			if (albumsRes.success && albumsRes.data) {
				albums = albumsRes.data.albums;
			}
		} catch (err: unknown) {
			console.error('Failed to load filter options:', err);
		}
	}

	function updateUrl(): void {
		const params = new URLSearchParams();

		if (query.trim()) {
			params.set('q', query);
		}
		if (currentPage > 1) {
			params.set('page', currentPage.toString());
		}
		if (perPage !== 24) {
			params.set('per_page', perPage.toString());
		}
		if (selectedConnectorId) {
			params.set('connector_id', selectedConnectorId);
		}
		if (selectedAlbumId) {
			params.set('album_id', selectedAlbumId);
		}

		const newUrl = params.toString() ? `?${params.toString()}` : '/search';
		void goto(newUrl, { replaceState: true, keepFocus: true });
	}

	async function loadPhotos(): Promise<void> {
		loading = true;
		isSearchMode = false;
		try {
			let url = `/photos?page=${currentPage.toString()}&per_page=${perPage.toString()}`;
			if (selectedConnectorId) {
				url += `&connector_id=${encodeURIComponent(selectedConnectorId)}`;
			}
			if (selectedAlbumId) {
				url += `&album_id=${encodeURIComponent(selectedAlbumId)}`;
			}
			const res = await client.get<PhotosResponse>(url);
			if (res.success && res.data) {
				photos = res.data.photos;
				total = res.meta?.total ?? 0;
			}
		} catch (err: unknown) {
			console.error('Failed to load photos:', err);
		} finally {
			loading = false;
		}
		updateUrl();
	}

	async function handleSearch(): Promise<void> {
		if (!query.trim()) {
			currentPage = 1;
			await loadPhotos();
			return;
		}
		loading = true;
		isSearchMode = true;
		try {
			const offset = (currentPage - 1) * perPage;
			let url = `/search?q=${encodeURIComponent(query)}&limit=${perPage.toString()}&offset=${offset.toString()}`;
			if (selectedConnectorId) {
				url += `&connector_id=${encodeURIComponent(selectedConnectorId)}`;
			}
			if (selectedAlbumId) {
				url += `&album_id=${encodeURIComponent(selectedAlbumId)}`;
			}
			const res = await client.get<SearchResponse>(url);
			if (res.success && res.data) {
				photos = res.data.results.map((r: SearchResultItem) => ({
					id: r.photo.id,
					filename: r.photo.filename,
					thumbnail_url: r.photo.thumbnail_url,
					connector_type: r.photo.connector_type,
					width: r.photo.width,
					height: r.photo.height,
					taken_at: r.photo.taken_at,
					created_at: r.photo.taken_at ?? '',
					score: r.score
				}));
				total = res.meta?.total ?? photos.length;
			}
		} catch (err: unknown) {
			console.error('Search failed:', err);
		} finally {
			loading = false;
		}
		updateUrl();
	}

	function goToPage(newPage: number): void {
		if (newPage >= 1 && newPage <= totalPages) {
			currentPage = newPage;
			if (isSearchMode) {
				void handleSearch();
			} else {
				void loadPhotos();
			}
		}
	}

	function onSearchSubmit(): void {
		currentPage = 1;
		void handleSearch();
	}

	function getPaginationPages(): number[] {
		const pages: number[] = [];
		const maxVisible = 7;

		if (totalPages <= maxVisible) {
			for (let i = 1; i <= totalPages; i++) {
				pages.push(i);
			}
		} else if (currentPage <= 4) {
			for (let i = 1; i <= maxVisible; i++) {
				pages.push(i);
			}
		} else if (currentPage >= totalPages - 3) {
			for (let i = totalPages - maxVisible + 1; i <= totalPages; i++) {
				pages.push(i);
			}
		} else {
			for (let i = currentPage - 3; i <= currentPage + 3; i++) {
				pages.push(i);
			}
		}

		return pages;
	}
</script>

<svelte:head>
	<title>Search Photos - Photo Explorer</title>
</svelte:head>

<div class="p-8">
	<header class="mb-8">
		<h1 class="text-3xl font-bold text-gray-900">Photos</h1>
		<p class="mt-2 text-gray-600">Browse and search your photos</p>
	</header>

	<div class="mb-6">
		<SearchBar bind:query onSearch={onSearchSubmit} {loading} />
	</div>

	<!-- Scope Filters -->
	<div class="mb-6 flex flex-wrap gap-4">
		<div class="flex items-center gap-2">
			<label for="connector-filter" class="text-sm font-medium text-gray-700">Source:</label>
			<select
				id="connector-filter"
				class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
				bind:value={selectedConnectorId}
				onchange={() => {
					currentPage = 1;
					if (isSearchMode && query.trim()) {
						void handleSearch();
					} else {
						void loadPhotos();
					}
				}}
			>
				<option value={null}>All Sources</option>
				{#each connectors as connector (connector.id)}
					<option value={connector.id}>{connector.name}</option>
				{/each}
			</select>
		</div>

		<div class="flex items-center gap-2">
			<label for="album-filter" class="text-sm font-medium text-gray-700">Album:</label>
			<select
				id="album-filter"
				class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
				bind:value={selectedAlbumId}
				onchange={() => {
					currentPage = 1;
					if (isSearchMode && query.trim()) {
						void handleSearch();
					} else {
						void loadPhotos();
					}
				}}
			>
				<option value={null}>All Albums</option>
				{#each albums as album (album.id)}
					<option value={album.id}>{album.name}</option>
				{/each}
			</select>
		</div>

		{#if selectedConnectorId || selectedAlbumId}
			<button
				class="text-sm text-blue-600 hover:underline"
				onclick={() => {
					selectedConnectorId = null;
					selectedAlbumId = null;
					currentPage = 1;
					if (isSearchMode && query.trim()) {
						void handleSearch();
					} else {
						void loadPhotos();
					}
				}}
			>
				Clear filters
			</button>
		{/if}
	</div>

	<!-- Photo Grid -->
	{#if loading && photos.length === 0}
		<div class="text-center py-12 text-gray-500">Loading photos...</div>
	{:else if photos.length === 0}
		<div class="text-center py-12 text-gray-500">
			<p>No photos yet. Import some photos from Google Photos or upload them.</p>
		</div>
	{:else}
		<div class="mb-4 text-sm text-gray-500">
			Showing {(currentPage - 1) * perPage + 1}-{Math.min(currentPage * perPage, total)} of {total}
			photos
			{#if isSearchMode && query.trim()}
				matching "{query}"
			{/if}
		</div>

		<div class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
			{#each photos as photo (photo.id)}
				<a href="/photos/{photo.id}" class="photo-card group cursor-pointer block">
					{#if photo.thumbnail_url}
						<img
							src="{API_HOST}{photo.thumbnail_url}"
							alt={photo.filename}
							class="aspect-square w-full rounded-lg object-cover"
							loading="lazy"
						/>
					{:else}
						<div
							class="aspect-square w-full rounded-lg bg-gray-100 flex items-center justify-center"
						>
							<svg
								class="w-8 h-8 text-gray-400"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
								/>
							</svg>
						</div>
					{/if}
					<p class="mt-1 truncate text-xs text-gray-500">{photo.filename}</p>
					{#if photo.score !== undefined}
						<p class="text-xs text-blue-500">Score: {photo.score.toFixed(2)}</p>
					{/if}
				</a>
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

				{#each getPaginationPages() as pageNum (pageNum)}
					<button
						class="px-3 py-1 rounded text-sm {currentPage === pageNum
							? 'bg-blue-500 text-white'
							: 'border border-gray-300'}"
						onclick={() => goToPage(pageNum)}
					>
						{pageNum}
					</button>
				{/each}

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

<style>
	.photo-card {
		transition: transform 0.2s;
	}
	.photo-card:hover {
		transform: scale(1.02);
	}
</style>
