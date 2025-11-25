<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { client, API_HOST } from '$lib/api/client';
	import { settingsStore } from '$lib/features/settings';
	import type { PickerSession } from '$lib/features/settings/types';

	interface Connector {
		id: string;
		type: 'google_photos' | 'local' | 'upload';
		name: string;
		enabled: boolean;
		status: string;
		config: Record<string, unknown>;
		last_sync: string | null;
		error_message: string | null;
	}

	interface Photo {
		id: string;
		filename: string;
		thumbnail_url: string | null;
		taken_at: string | null;
		processing_status: string;
		created_at: string;
	}

	interface PhotosResponse {
		photos: Photo[];
	}

	let connector = $state<Connector | null>(null);
	let photos = $state<Photo[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let currentPage = $state(1);
	let perPage = $state(30);
	let total = $state(0);
	let selectedPhotos = $state<Set<string>>(new Set());
	let selectMode = $state(false);

	// Action states
	let syncing = $state(false);
	let reprocessing = $state(false);
	let reprocessMessage = $state<string | null>(null);
	let reprocessMessageTimeout: ReturnType<typeof setTimeout> | null = null;

	// Google Photos picker state
	let pickerSession: PickerSession | null = null;
	let pickerWindow: Window | null = null;
	let pickerPolling = false;
	let pickerStatus = $state<'idle' | 'selecting' | 'importing' | 'done' | 'error'>('idle');
	let pickerMessage = $state<string | null>(null);
	let pickerResetTimeout: ReturnType<typeof setTimeout> | null = null;

	const connectorId = $derived($page.params.id);
	const totalPages = $derived(Math.ceil(total / perPage));

	// Cleanup on destroy
	onDestroy(() => {
		if (reprocessMessageTimeout !== null) {
			clearTimeout(reprocessMessageTimeout);
		}
		if (pickerResetTimeout !== null) {
			clearTimeout(pickerResetTimeout);
		}
		if (pickerWindow && !pickerWindow.closed) {
			pickerWindow.close();
		}
		pickerWindow = null;
		pickerPolling = false;
	});

	onMount(() => {
		void loadData();
	});

	async function loadData(): Promise<void> {
		loading = true;
		error = null;
		try {
			// Load connector info
			const connectorRes = await client.get<Connector>(`/connectors/${connectorId}`);
			if (connectorRes.success && connectorRes.data) {
				connector = connectorRes.data;
			}

			// Load photos
			await loadPhotos();
		} catch (err: unknown) {
			console.error('Failed to load connector:', err);
			error = err instanceof Error ? err.message : 'Failed to load connector';
		} finally {
			loading = false;
		}
	}

	async function loadPhotos(): Promise<void> {
		try {
			const res = await client.get<PhotosResponse>(
				`/connectors/${connectorId}/photos?page=${currentPage}&per_page=${perPage}`
			);
			if (res.success && res.data) {
				photos = res.data.photos;
				total = res.meta?.total ?? photos.length;
			}
		} catch (err: unknown) {
			console.error('Failed to load photos:', err);
		}
	}

	function goToPage(newPage: number): void {
		if (newPage >= 1 && newPage <= totalPages) {
			currentPage = newPage;
			void loadPhotos();
		}
	}

	function toggleSelectMode(): void {
		selectMode = !selectMode;
		if (!selectMode) {
			selectedPhotos = new Set();
		}
	}

	function togglePhotoSelection(photoId: string): void {
		const newSelected = new Set(selectedPhotos);
		if (newSelected.has(photoId)) {
			newSelected.delete(photoId);
		} else {
			newSelected.add(photoId);
		}
		selectedPhotos = newSelected;
	}

	function selectAll(): void {
		selectedPhotos = new Set(photos.map((p) => p.id));
	}

	function deselectAll(): void {
		selectedPhotos = new Set();
	}

	function getConnectorIcon(type: string): string {
		switch (type) {
			case 'google_photos':
				return '\u{1F4F7}';
			case 'local':
				return '\u{1F4C1}';
			case 'upload':
				return '\u{1F4E4}';
			default:
				return '\u{1F517}';
		}
	}

	function goBack(): void {
		void goto('/connectors');
	}

	function viewPhoto(photoId: string): void {
		void goto(`/photos/${photoId}`);
	}

	async function handleSync(): Promise<void> {
		if (!connectorId) return;

		syncing = true;
		try {
			await settingsStore.triggerSync(connectorId);
			// Reload to show updated status
			await loadData();
		} catch (err) {
			console.error('Sync failed:', err);
		} finally {
			syncing = false;
		}
	}

	async function handleReprocess(): Promise<void> {
		if (!connectorId) return;

		reprocessing = true;
		reprocessMessage = 'Starting reprocess...';
		try {
			const result = await settingsStore.reprocessConnector(connectorId);
			reprocessMessage = result.message;
			// Clear message after 5 seconds
			if (reprocessMessageTimeout !== null) {
				clearTimeout(reprocessMessageTimeout);
			}
			reprocessMessageTimeout = setTimeout(() => {
				reprocessMessage = null;
				reprocessMessageTimeout = null;
			}, 5000);
		} catch (err) {
			reprocessMessage = err instanceof Error ? err.message : 'Reprocess failed';
		} finally {
			reprocessing = false;
		}
	}

	async function handleImportPhotos(): Promise<void> {
		if (connector?.type !== 'google_photos' || !connectorId) return;

		pickerStatus = 'selecting';
		pickerMessage = 'Opening photo picker... After selecting photos, click the "ADD" button to import them.';

		try {
			// Create picker session
			pickerSession = await settingsStore.createPickerSession(connectorId);

			// Open picker in popup
			const width = 900;
			const height = 700;
			const left = window.screenX + (window.outerWidth - width) / 2;
			const top = window.screenY + (window.outerHeight - height) / 2;

			pickerWindow = window.open(
				pickerSession.pickerUri,
				'GooglePhotosPicker',
				`width=${width},height=${height},left=${left},top=${top},menubar=no,toolbar=no,location=no,status=no`
			);

			if (!pickerWindow) {
				throw new Error('Failed to open picker window. Please allow popups.');
			}

			// Start polling for status
			pickerPolling = true;
			pollPickerStatus();
		} catch (err) {
			pickerStatus = 'error';
			pickerMessage = err instanceof Error ? err.message : 'Failed to open photo picker';
			console.error('Import photos error:', err);
		}
	}

	async function pollPickerStatus(): Promise<void> {
		if (!pickerSession || !pickerPolling || !connectorId) return;

		try {
			const status = await settingsStore.getPickerSessionStatus(
				connectorId,
				pickerSession.sessionId
			);

			if (status.mediaItemsSet) {
				pickerStatus = 'importing';
				pickerMessage = 'Importing selected photos...';
				pickerPolling = false;

				// Close picker window
				if (pickerWindow && !pickerWindow.closed) {
					pickerWindow.close();
				}

				// Trigger import
				const result = await settingsStore.importPickerPhotos(
					connectorId,
					pickerSession.sessionId
				);

				pickerStatus = 'done';
				pickerMessage = `Import started! ${result.message || 'Processing photos...'}`;

				// Reset after 5 seconds and reload photos
				if (pickerResetTimeout !== null) {
					clearTimeout(pickerResetTimeout);
				}
				pickerResetTimeout = setTimeout(() => {
					pickerStatus = 'idle';
					pickerMessage = null;
					pickerSession = null;
					pickerResetTimeout = null;
					// Reload photos
					void loadPhotos();
				}, 5000);
			} else if (pickerWindow && pickerWindow.closed) {
				// Window was closed without selection
				pickerStatus = 'error';
				pickerMessage = 'Photo selection cancelled. Make sure to click the "ADD" button in the picker before closing the window.';
				pickerPolling = false;

				// Reset after 3 seconds
				if (pickerResetTimeout !== null) {
					clearTimeout(pickerResetTimeout);
				}
				pickerResetTimeout = setTimeout(() => {
					pickerStatus = 'idle';
					pickerMessage = null;
					pickerSession = null;
					pickerResetTimeout = null;
				}, 3000);
			} else {
				// Still selecting, poll again in 2 seconds
				setTimeout(() => {
					if (pickerPolling) {
						void pollPickerStatus();
					}
				}, 2000);
			}
		} catch (err) {
			console.error('Picker polling error:', err);
			pickerStatus = 'error';
			pickerMessage = 'Failed to check picker status';
			pickerPolling = false;
		}
	}
</script>

<svelte:head>
	<title>{connector?.name ?? 'Connector'} - Photo Explorer</title>
</svelte:head>

<div class="p-8">
	<!-- Back button -->
	<button onclick={goBack} class="mb-4 flex items-center gap-2 text-gray-600 hover:text-gray-900">
		<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
		</svg>
		Back to Connectors
	</button>

	{#if loading}
		<div class="py-12 text-center text-gray-500">Loading...</div>
	{:else if error}
		<div class="py-12 text-center text-red-500">{error}</div>
	{:else if connector}
		<!-- Connector Header -->
		<div class="mb-8 flex items-center gap-4">
			<div class="text-4xl">{getConnectorIcon(connector.type)}</div>
			<div class="flex-1">
				<h1 class="text-3xl font-bold text-gray-900">{connector.name}</h1>
				<p class="text-gray-500">{total} photos</p>
			</div>

			<!-- Connector Actions -->
			<div class="flex gap-2">
				{#if connector.type !== 'upload'}
					<button
						onclick={handleSync}
						disabled={syncing}
						class="rounded-lg border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-50"
					>
						{syncing ? 'Syncing...' : 'Sync'}
					</button>
				{/if}

				<button
					onclick={handleReprocess}
					disabled={reprocessing}
					class="rounded-lg border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-50"
				>
					{reprocessing ? 'Reprocessing...' : 'Reprocess'}
				</button>

				{#if connector.type === 'google_photos'}
					<button
						onclick={handleImportPhotos}
						disabled={pickerStatus !== 'idle'}
						class="rounded-lg bg-blue-500 px-4 py-2 text-sm text-white hover:bg-blue-600 disabled:opacity-50"
					>
						{#if pickerStatus === 'selecting'}
							Selecting...
						{:else if pickerStatus === 'importing'}
							Importing...
						{:else}
							Import Photos
						{/if}
					</button>
				{/if}
			</div>
		</div>

		<!-- Status Messages -->
		{#if reprocessMessage}
			<div class="mb-4 rounded-lg bg-blue-50 p-3 text-sm text-blue-700">
				{reprocessMessage}
			</div>
		{/if}

		{#if pickerMessage}
			<div
				class="mb-4 rounded-lg p-3 text-sm"
				class:bg-blue-50={pickerStatus === 'selecting' || pickerStatus === 'importing'}
				class:text-blue-700={pickerStatus === 'selecting' || pickerStatus === 'importing'}
				class:bg-green-50={pickerStatus === 'done'}
				class:text-green-700={pickerStatus === 'done'}
				class:bg-red-50={pickerStatus === 'error'}
				class:text-red-700={pickerStatus === 'error'}
			>
				{pickerMessage}
			</div>
		{/if}

		<!-- Actions Bar -->
		<div class="mb-6 flex items-center gap-4">
			<button
				onclick={toggleSelectMode}
				class="rounded-lg border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50"
				class:bg-blue-50={selectMode}
				class:border-blue-300={selectMode}
			>
				{selectMode ? 'Cancel Selection' : 'Select Photos'}
			</button>

			{#if selectMode}
				<button onclick={selectAll} class="text-sm text-blue-600 hover:underline">
					Select All
				</button>
				<button onclick={deselectAll} class="text-sm text-gray-600 hover:underline">
					Deselect All
				</button>
				<span class="text-sm text-gray-500">{selectedPhotos.size} selected</span>

				{#if selectedPhotos.size > 0}
					<button
						class="rounded-lg bg-blue-500 px-4 py-2 text-sm text-white hover:bg-blue-600"
					>
						Add to Album
					</button>
					<button
						class="rounded-lg border border-red-300 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
					>
						Remove from Index
					</button>
				{/if}
			{/if}
		</div>

		<!-- Photo Grid -->
		{#if photos.length === 0}
			<div class="py-12 text-center text-gray-500">
				<p>No photos in this connector yet</p>
			</div>
		{:else}
			<div class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
				{#each photos as photo (photo.id)}
					<div class="group relative">
						{#if selectMode}
							<button
								onclick={() => togglePhotoSelection(photo.id)}
								class="absolute left-2 top-2 z-10 flex h-6 w-6 items-center justify-center rounded border-2 bg-white"
								class:border-blue-500={selectedPhotos.has(photo.id)}
								class:bg-blue-500={selectedPhotos.has(photo.id)}
								class:border-gray-300={!selectedPhotos.has(photo.id)}
							>
								{#if selectedPhotos.has(photo.id)}
									<svg class="h-4 w-4 text-white" fill="currentColor" viewBox="0 0 20 20">
										<path
											fill-rule="evenodd"
											d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
											clip-rule="evenodd"
										/>
									</svg>
								{/if}
							</button>
						{/if}

						<button
							onclick={() => (selectMode ? togglePhotoSelection(photo.id) : viewPhoto(photo.id))}
							class="aspect-square w-full overflow-hidden rounded-lg bg-gray-100"
						>
							{#if photo.thumbnail_url}
								<img
									src="{API_HOST}{photo.thumbnail_url}"
									alt={photo.filename}
									class="h-full w-full object-cover transition-transform group-hover:scale-105"
									loading="lazy"
								/>
							{:else}
								<div class="flex h-full items-center justify-center text-gray-300">
									<svg class="h-12 w-12" fill="currentColor" viewBox="0 0 24 24">
										<path
											d="M4 5h16a2 2 0 012 2v10a2 2 0 01-2 2H4a2 2 0 01-2-2V7a2 2 0 012-2zm0 2v10h16V7H4zm8 2a3 3 0 110 6 3 3 0 010-6z"
										/>
									</svg>
								</div>
							{/if}
						</button>
					</div>
				{/each}
			</div>

			<!-- Pagination -->
			{#if totalPages > 1}
				<div class="mt-8 flex items-center justify-center gap-2">
					<button
						class="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
						disabled={currentPage === 1}
						onclick={() => goToPage(currentPage - 1)}
					>
						Previous
					</button>
					<span class="text-sm text-gray-600">
						Page {currentPage} of {totalPages}
					</span>
					<button
						class="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
						disabled={currentPage === totalPages}
						onclick={() => goToPage(currentPage + 1)}
					>
						Next
					</button>
				</div>
			{/if}
		{/if}
	{:else}
		<div class="py-12 text-center text-gray-500">Connector not found</div>
	{/if}
</div>
