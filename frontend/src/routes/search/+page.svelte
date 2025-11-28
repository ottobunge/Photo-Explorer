<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { SearchBar } from '$features/search';
	import SimilarityThresholdSlider from '$lib/features/search/components/SimilarityThresholdSlider.svelte';
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

	// UI-only state (loading, data, filter options)
	let photos = $state<Photo[]>([]);
	let loading = $state(false);
	let total = $state(0);
	let connectors = $state<Connector[]>([]);
	let albums = $state<Album[]>([]);
	let abortController: AbortController | null = null;

	// Local search input state (syncs to URL on submit)
	let searchInput = $state('');

	// URL as single source of truth - derive all bookmarkable state from URL
	const query = $derived($page.url.searchParams.get('q') ?? '');

	// Sync search input with URL query when it changes (e.g., browser back/forward)
	$effect(() => {
		searchInput = query;
	});
	const currentPage = $derived.by(() => {
		const urlPage = $page.url.searchParams.get('page');
		if (urlPage !== null) {
			const parsed = parseInt(urlPage, 10);
			if (!isNaN(parsed) && parsed >= 1) {
				return parsed;
			}
		}
		return 1;
	});
	const perPage = $derived.by(() => {
		const urlPerPage = $page.url.searchParams.get('per_page');
		if (urlPerPage !== null) {
			const parsed = parseInt(urlPerPage, 10);
			if (!isNaN(parsed) && parsed >= 1 && parsed <= 100) {
				return parsed;
			}
		}
		return 24;
	});
	const selectedConnectorId = $derived($page.url.searchParams.get('connector_id'));
	const selectedAlbumId = $derived($page.url.searchParams.get('album_id'));
	const similarityThreshold = $derived.by(() => {
		const urlSimilarity = $page.url.searchParams.get('similarity_threshold');
		if (urlSimilarity !== null) {
			const parsed = parseFloat(urlSimilarity);
			if (!isNaN(parsed) && parsed >= 0.0 && parsed <= 1.0) {
				return parsed;
			}
		}
		return 0.18; // Default
	});
	const isSearchMode = $derived(query.trim().length > 0);

	const totalPages = $derived(Math.ceil(total / perPage));

	// Load filter options on mount
	$effect(() => {
		void loadFilterOptions();
	});

	async function loadFilterOptions(): Promise<void> {
		try {
			const [connectorsRes, albumsRes] = await Promise.all([
				client.get<ConnectorsResponse>('/connectors'),
				client.get<AlbumsResponse>('/albums')
			]);
			if (connectorsRes.success) {
				connectors = connectorsRes.data.connectors;
			}
			if (albumsRes.success) {
				albums = albumsRes.data.albums;
			}
		} catch (err: unknown) {
			console.error('Failed to load filter options:', err);
		}
	}

	// React to URL changes and fetch data
	$effect(() => {
		// Track dependencies to trigger re-fetch when URL params change
		// These variables establish reactive dependencies without direct use
		void query;
		void currentPage;
		void selectedConnectorId;
		void selectedAlbumId;
		void similarityThreshold;

		if (isSearchMode && query.trim()) {
			void fetchSearchResults();
		} else {
			void fetchPhotos();
		}
	});

	function updateUrl(params: {
		query?: string;
		page?: number;
		perPage?: number;
		connectorId?: string | null;
		albumId?: string | null;
		similarityThreshold?: number;
	}): void {
		const urlParams = new URLSearchParams();

		const finalQuery = params.query ?? query;
		const finalPage = params.page ?? currentPage;
		const finalPerPage = params.perPage ?? perPage;
		const finalConnectorId = params.connectorId ?? selectedConnectorId;
		const finalAlbumId = params.albumId ?? selectedAlbumId;
		const finalThreshold = params.similarityThreshold ?? similarityThreshold;

		if (finalQuery.trim()) {
			urlParams.set('q', finalQuery);
		}
		if (finalPage > 1) {
			urlParams.set('page', finalPage.toString());
		}
		if (finalPerPage !== 24) {
			urlParams.set('per_page', finalPerPage.toString());
		}
		if (finalConnectorId) {
			urlParams.set('connector_id', finalConnectorId);
		}
		if (finalAlbumId) {
			urlParams.set('album_id', finalAlbumId);
		}
		// Always include similarity threshold in URL (for shareability)
		urlParams.set('similarity_threshold', finalThreshold.toString());

		const newUrl = urlParams.toString() ? `?${urlParams.toString()}` : '/search';
		void goto(newUrl, { replaceState: true, keepFocus: true });
	}

	async function fetchPhotos(): Promise<void> {
		loading = true;
		try {
			let url = `/photos?page=${currentPage.toString()}&per_page=${perPage.toString()}`;
			if (selectedConnectorId) {
				url += `&connector_id=${encodeURIComponent(selectedConnectorId)}`;
			}
			if (selectedAlbumId) {
				url += `&album_id=${encodeURIComponent(selectedAlbumId)}`;
			}
			const res = await client.get<PhotosResponse>(url);
			if (res.success) {
				photos = res.data.photos;
				total = res.meta?.total ?? 0;
			}
		} catch (err: unknown) {
			console.error('Failed to load photos:', err);
		} finally {
			loading = false;
		}
	}

	async function fetchSearchResults(): Promise<void> {
		// Cancel previous request if it exists
		if (abortController !== null) {
			abortController.abort();
		}

		// Create new abort controller for this request
		abortController = new AbortController();
		const signal = abortController.signal;

		loading = true;
		try {
			const offset = (currentPage - 1) * perPage;
			let url = `/search?q=${encodeURIComponent(query)}&limit=${perPage.toString()}&offset=${offset.toString()}`;
			if (selectedConnectorId) {
				url += `&connector_id=${encodeURIComponent(selectedConnectorId)}`;
			}
			if (selectedAlbumId) {
				url += `&album_id=${encodeURIComponent(selectedAlbumId)}`;
			}
			// Only include similarity_threshold if > 0.0 (to avoid filtering when showing all results)
			if (similarityThreshold > 0.0) {
				url += `&similarity_threshold=${similarityThreshold.toString()}`;
			}
			const res = await client.get<SearchResponse>(url, { signal });

			// Check if request was aborted
			if (signal.aborted) {
				return;
			}

			if (res.success) {
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
			// Ignore abort errors
			if (err instanceof Error && err.name === 'AbortError') {
				return;
			}
			console.error('Search failed:', err);
		} finally {
			loading = false;
		}
	}

	function goToPage(newPage: number): void {
		if (newPage >= 1 && newPage <= totalPages) {
			updateUrl({ page: newPage });
		}
	}

	function onSearchSubmit(newQuery: string): void {
		updateUrl({ query: newQuery, page: 1 });
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
		<!-- Local input state for SearchBar, syncs to URL on submit -->
		<SearchBar
			bind:query={searchInput}
			onSearch={() => { onSearchSubmit(searchInput); }}
			{loading}
		/>
	</div>

	<!-- Similarity Threshold Slider - Always visible -->
	<div class="mb-6">
		<SimilarityThresholdSlider
			value={similarityThreshold}
			onchange={(value: number) => {
				updateUrl({ similarityThreshold: value, page: 1 });
			}}
		/>
	</div>

	<!-- Scope Filters -->
	<div class="mb-6 flex flex-wrap gap-4">
		<div class="flex items-center gap-2">
			<label for="connector-filter" class="text-sm font-medium text-gray-700">Source:</label>
			<select
				id="connector-filter"
				class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
				value={selectedConnectorId ?? ''}
				onchange={(e: Event) => {
					const target = e.currentTarget as HTMLSelectElement;
					const value = target.value || null;
					updateUrl({ connectorId: value, page: 1 });
				}}
			>
				<option value="">All Sources</option>
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
				value={selectedAlbumId ?? ''}
				onchange={(e: Event) => {
					const target = e.currentTarget as HTMLSelectElement;
					const value = target.value || null;
					updateUrl({ albumId: value, page: 1 });
				}}
			>
				<option value="">All Albums</option>
				{#each albums as album (album.id)}
					<option value={album.id}>{album.name}</option>
				{/each}
			</select>
		</div>

		{#if selectedConnectorId !== null || selectedAlbumId !== null}
			<button
				class="text-sm text-blue-600 hover:underline"
				onclick={() => {
					updateUrl({ connectorId: null, albumId: null, page: 1 });
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
				<a href="/photos/{photo.id}" class="photo-card group cursor-pointer block" data-testid="photo-card">
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
					onclick={() => { goToPage(currentPage - 1); }}
				>
					Previous
				</button>

				{#each getPaginationPages() as pageNum (pageNum)}
					<button
						class="px-3 py-1 rounded text-sm {currentPage === pageNum
							? 'bg-blue-500 text-white'
							: 'border border-gray-300'}"
						onclick={() => { goToPage(pageNum); }}
					>
						{pageNum}
					</button>
				{/each}

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
</div>

<style>
	.photo-card {
		transition: transform 0.2s;
	}
	.photo-card:hover {
		transform: scale(1.02);
	}
</style>
