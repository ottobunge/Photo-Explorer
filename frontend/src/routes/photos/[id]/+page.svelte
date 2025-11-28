<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { client, API_HOST } from '$lib/api/client';

	interface Photo {
		id: string;
		filename: string;
		original_path: string | null;
		thumbnail_url: string | null;
		mime_type: string | null;
		file_size: number | null;
		width: number | null;
		height: number | null;
		taken_at: string | null;
		description: string | null;
		scene_type: string | null;
		is_indoor: boolean | null;
		detected_objects: string[];
		processing_status: string;
		connector_type: string | null;
		created_at: string;
		updated_at: string | null;
	}

	let photo = $state<Photo | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	const photoId = $page.params.id;

	onMount(() => {
		void loadPhoto();
	});

	async function loadPhoto(): Promise<void> {
		loading = true;
		error = null;
		try {
			const res = await client.get<Photo>(`/photos/${photoId}`);
			if (res.success) {
				photo = res.data;
			} else {
				error = 'Failed to load photo';
			}
		} catch (err: unknown) {
			console.error('Failed to load photo:', err);
			error = err instanceof Error ? err.message : 'Failed to load photo';
		} finally {
			loading = false;
		}
	}

	function formatFileSize(bytes: number | null): string {
		if (bytes === null) {return 'Unknown';}
		const kb = bytes / 1024;
		if (kb < 1024) {return `${kb.toFixed(1)} KB`;}
		const mb = kb / 1024;
		return `${mb.toFixed(1)} MB`;
	}

	function formatDate(dateStr: string | null): string {
		if (!dateStr) {return 'Unknown';}
		const date = new Date(dateStr);
		return date.toLocaleString();
	}

	function getProcessingStatusBadge(status: string): string {
		switch (status) {
			case 'completed':
				return 'bg-green-100 text-green-800';
			case 'processing':
				return 'bg-blue-100 text-blue-800';
			case 'failed':
				return 'bg-red-100 text-red-800';
			default:
				return 'bg-gray-100 text-gray-800';
		}
	}
</script>

<svelte:head>
	<title>{photo ? photo.filename : 'Photo'} - Photo Explorer</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 p-8">
	{#if loading}
		<div class="text-center py-12">
			<div class="text-gray-500">Loading photo...</div>
		</div>
	{:else if error}
		<div class="max-w-2xl mx-auto">
			<div class="bg-red-50 border border-red-200 rounded-lg p-4">
				<p class="text-red-800">{error}</p>
				<button
					class="mt-4 text-red-600 hover:underline"
					onclick={() => goto('/search')}
				>
					← Back to photos
				</button>
			</div>
		</div>
	{:else if photo}
		<div class="max-w-6xl mx-auto">
			<!-- Header -->
			<div class="mb-6">
				<button
					class="text-blue-600 hover:underline mb-4 flex items-center gap-2"
					onclick={() => goto('/search')}
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
					</svg>
					Back to photos
				</button>
				<h1 class="text-3xl font-bold text-gray-900">{photo.filename}</h1>
				<div class="mt-2 flex items-center gap-2">
					<span class="px-2 py-1 rounded text-sm {getProcessingStatusBadge(photo.processing_status)}">
						{photo.processing_status}
					</span>
					{#if photo.connector_type}
						<span class="px-2 py-1 rounded text-sm bg-blue-50 text-blue-700">
							{photo.connector_type}
						</span>
					{/if}
				</div>
			</div>

			<div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
				<!-- Image Section -->
				<div class="bg-white rounded-lg shadow-lg overflow-hidden">
					{#if photo.thumbnail_url}
						<img
							src="{API_HOST}{photo.thumbnail_url}"
							alt={photo.description ?? photo.filename}
							class="w-full h-auto"
						/>
					{:else}
						<div class="aspect-square bg-gray-100 flex flex-col items-center justify-center p-8">
							<svg class="w-24 h-24 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
							</svg>
							<p class="text-gray-500 text-center">
								{#if photo.processing_status === 'pending' || photo.processing_status === 'processing'}
									Thumbnail is being generated...
								{:else}
									Thumbnail not available
								{/if}
							</p>
						</div>
					{/if}
				</div>

				<!-- Details Section -->
				<div class="space-y-6">
					<!-- AI Description -->
					{#if photo.description}
						<div class="bg-white rounded-lg shadow p-6">
							<h2 class="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
								<svg class="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
								</svg>
								AI Description
							</h2>
							<p class="text-gray-700 leading-relaxed">{photo.description}</p>
						</div>
					{/if}

					<!-- Scene Classification -->
					{#if (photo.scene_type !== null && photo.scene_type !== '') || photo.is_indoor !== null}
						<div class="bg-white rounded-lg shadow p-6">
							<h2 class="text-lg font-semibold text-gray-900 mb-3">Scene Analysis</h2>
							<div class="space-y-2">
								{#if photo.scene_type}
									<div class="flex items-center justify-between">
										<span class="text-gray-600">Scene Type:</span>
										<span class="font-medium text-gray-900">{photo.scene_type}</span>
									</div>
								{/if}
								{#if photo.is_indoor !== null}
									<div class="flex items-center justify-between">
										<span class="text-gray-600">Location:</span>
										<span class="font-medium text-gray-900">{photo.is_indoor ? 'Indoor' : 'Outdoor'}</span>
									</div>
								{/if}
							</div>
						</div>
					{/if}

					<!-- Detected Objects -->
					{#if photo.detected_objects.length > 0}
						<div class="bg-white rounded-lg shadow p-6">
							<h2 class="text-lg font-semibold text-gray-900 mb-3">Detected Objects</h2>
							<div class="flex flex-wrap gap-2">
								{#each photo.detected_objects as object}
									<span class="px-3 py-1 rounded-full text-sm bg-indigo-50 text-indigo-700">
										{object}
									</span>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Metadata -->
					<div class="bg-white rounded-lg shadow p-6">
						<h2 class="text-lg font-semibold text-gray-900 mb-3">Metadata</h2>
						<dl class="space-y-2">
							{#if photo.width !== null && photo.height !== null}
								<div class="flex justify-between">
									<dt class="text-gray-600">Dimensions:</dt>
									<dd class="font-medium text-gray-900">{photo.width} × {photo.height}</dd>
								</div>
							{/if}
							{#if photo.file_size}
								<div class="flex justify-between">
									<dt class="text-gray-600">File Size:</dt>
									<dd class="font-medium text-gray-900">{formatFileSize(photo.file_size)}</dd>
								</div>
							{/if}
							{#if photo.mime_type}
								<div class="flex justify-between">
									<dt class="text-gray-600">Type:</dt>
									<dd class="font-medium text-gray-900">{photo.mime_type}</dd>
								</div>
							{/if}
							{#if photo.taken_at}
								<div class="flex justify-between">
									<dt class="text-gray-600">Taken:</dt>
									<dd class="font-medium text-gray-900">{formatDate(photo.taken_at)}</dd>
								</div>
							{/if}
							<div class="flex justify-between">
								<dt class="text-gray-600">Added:</dt>
								<dd class="font-medium text-gray-900">{formatDate(photo.created_at)}</dd>
							</div>
							{#if photo.original_path}
								<div class="flex justify-between">
									<dt class="text-gray-600">Path:</dt>
									<dd class="font-medium text-gray-900 truncate max-w-xs" title={photo.original_path}>
										{photo.original_path}
									</dd>
								</div>
							{/if}
						</dl>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	dl {
		display: grid;
	}
</style>
