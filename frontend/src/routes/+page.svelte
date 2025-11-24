<script lang="ts">
	import { onMount } from 'svelte';
	import { client, API_HOST } from '$lib/api/client';

	interface Photo {
		id: string;
		filename: string;
		thumbnail_url: string | null;
		connector_type: string;
		taken_at: string | null;
		created_at: string;
	}

	interface Stats {
		photos: number;
		albums: number;
		people: number;
		connectors: number;
	}

	interface PhotosResponse {
		photos: Photo[];
	}

	interface ConnectorsResponse {
		connectors: Array<{ id: string; type: string; name: string }>;
	}

	interface AlbumsResponse {
		albums: Array<{ id: string; name: string }>;
	}

	interface FaceCluster {
		id: string;
		name: string | null;
		face_count: number;
	}

	interface ClustersResponse {
		clusters: FaceCluster[];
	}

	let stats: Stats = { photos: 0, albums: 0, people: 0, connectors: 0 };
	let recentPhotos: Photo[] = [];
	let loading = true;

	onMount(async () => {
		try {
			// Fetch photos
			const photosRes = await client.get<PhotosResponse>('/photos?per_page=12');
			if (photosRes.success && photosRes.data) {
				recentPhotos = photosRes.data.photos;
				stats.photos = photosRes.meta?.total ?? 0;
			}

			// Fetch connectors count
			const connectorsRes = await client.get<ConnectorsResponse>('/connectors');
			if (connectorsRes.success && connectorsRes.data) {
				stats.connectors = connectorsRes.data.connectors.length;
			}

			// Fetch albums count
			try {
				const albumsRes = await client.get<AlbumsResponse>('/albums');
				if (albumsRes.success && albumsRes.data) {
					stats.albums = albumsRes.data.albums.length;
				}
			} catch {
				// Albums endpoint might not exist yet
			}

			// Fetch people count
			try {
				const facesRes = await client.get<ClustersResponse>('/faces/clusters');
				if (facesRes.success && facesRes.data) {
					stats.people = facesRes.data.clusters.filter((c) => c.name !== null).length;
				}
			} catch {
				// Faces endpoint might not exist yet
			}
		} catch (err: unknown) {
			console.error('Failed to load dashboard:', err);
		} finally {
			loading = false;
		}
	});
</script>

<svelte:head>
	<title>Photo Explorer - Dashboard</title>
</svelte:head>

<div class="p-8">
	<header class="mb-8">
		<h1 class="text-3xl font-bold text-gray-900">Dashboard</h1>
		<p class="mt-2 text-gray-600">Welcome to Photo Explorer</p>
	</header>

	<!-- Stats Grid -->
	<div class="mb-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
		<div class="card p-6">
			<div class="text-sm font-medium text-gray-500">Total Photos</div>
			<div class="mt-2 text-3xl font-bold text-gray-900">{loading ? '...' : stats.photos}</div>
		</div>
		<div class="card p-6">
			<div class="text-sm font-medium text-gray-500">Albums</div>
			<div class="mt-2 text-3xl font-bold text-gray-900">{loading ? '...' : stats.albums}</div>
		</div>
		<div class="card p-6">
			<div class="text-sm font-medium text-gray-500">Named People</div>
			<div class="mt-2 text-3xl font-bold text-gray-900">{loading ? '...' : stats.people}</div>
		</div>
		<div class="card p-6">
			<div class="text-sm font-medium text-gray-500">Connectors</div>
			<div class="mt-2 text-3xl font-bold text-gray-900">{loading ? '...' : stats.connectors}</div>
		</div>
	</div>

	<!-- Quick Actions -->
	<section class="mb-8">
		<h2 class="mb-4 text-xl font-semibold text-gray-900">Quick Actions</h2>
		<div class="flex gap-4">
			<a href="/upload" class="btn-primary"> Upload Photos </a>
			<a href="/settings" class="btn-secondary"> Settings </a>
		</div>
	</section>

	<!-- Recent Photos -->
	<section>
		<h2 class="mb-4 text-xl font-semibold text-gray-900">Recent Photos</h2>
		{#if loading}
			<div class="card p-8 text-center text-gray-500">
				<p>Loading...</p>
			</div>
		{:else if recentPhotos.length === 0}
			<div class="card p-8 text-center text-gray-500">
				<p>No photos yet. Upload some photos or connect Google Photos to get started!</p>
			</div>
		{:else}
			<div class="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-6">
				{#each recentPhotos as photo (photo.id)}
					<div class="photo-card">
						{#if photo.thumbnail_url}
							<img
								src="{API_HOST}{photo.thumbnail_url}"
								alt={photo.filename}
								class="aspect-square w-full rounded-lg object-cover"
								loading="lazy"
							/>
						{:else}
							<div class="aspect-square w-full rounded-lg bg-gray-100 flex items-center justify-center">
								<span class="text-gray-400 text-3xl">
									{#if photo.connector_type === 'google_photos'}
										<svg class="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
											<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
										</svg>
									{:else}
										<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
										</svg>
									{/if}
								</span>
							</div>
						{/if}
						<p class="mt-1 truncate text-xs text-gray-500">{photo.filename}</p>
					</div>
				{/each}
			</div>
		{/if}
	</section>
</div>

<style>
	.photo-card {
		transition: transform 0.2s;
	}
	.photo-card:hover {
		transform: scale(1.02);
	}
</style>
