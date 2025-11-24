<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { client, API_HOST } from '$lib/api/client';

	interface Face {
		id: string;
		photo_id: string;
		crop_url: string;
	}

	interface ClusterData {
		id: string;
		name: string | null;
		face_count: number;
		photo_count: number;
		representative_face: {
			id: string;
			crop_url: string;
		} | null;
		faces?: Face[];
	}

	interface ClusterResponse {
		cluster: ClusterData;
		faces: Face[];
	}

	let cluster = $state<ClusterData | null>(null);
	let faces = $state<Face[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let isEditing = $state(false);
	let editName = $state('');
	let saving = $state(false);

	const clusterId = $derived($page.params.id);

	onMount(() => {
		void loadCluster();
	});

	async function loadCluster(): Promise<void> {
		loading = true;
		error = null;
		try {
			const res = await client.get<ClusterData>(`/faces/clusters/${clusterId}`);
			if (res.success && res.data) {
				cluster = res.data;
				editName = cluster.name ?? '';
			}

			// Load faces in this cluster
			const facesRes = await client.get<{ faces: Face[] }>(
				`/faces/clusters/${clusterId}/faces`
			);
			if (facesRes.success && facesRes.data) {
				faces = facesRes.data.faces;
			}
		} catch (err: unknown) {
			console.error('Failed to load cluster:', err);
			error = err instanceof Error ? err.message : 'Failed to load cluster';
		} finally {
			loading = false;
		}
	}

	function startEditing(): void {
		editName = cluster?.name ?? '';
		isEditing = true;
	}

	function cancelEditing(): void {
		isEditing = false;
		editName = cluster?.name ?? '';
	}

	async function saveName(): Promise<void> {
		if (!editName.trim()) {
			return;
		}
		saving = true;
		try {
			const res = await client.patch<ClusterData>(`/faces/clusters/${clusterId}`, {
				name: editName.trim()
			});
			if (res.success && res.data) {
				cluster = res.data;
				isEditing = false;
			}
		} catch (err: unknown) {
			console.error('Failed to save name:', err);
			error = err instanceof Error ? err.message : 'Failed to save name';
		} finally {
			saving = false;
		}
	}

	function handleKeydown(e: KeyboardEvent): void {
		if (e.key === 'Enter') {
			void saveName();
		} else if (e.key === 'Escape') {
			cancelEditing();
		}
	}

	function goBack(): void {
		void goto('/faces');
	}
</script>

<svelte:head>
	<title>{cluster?.name ?? 'Face Cluster'} - Photo Explorer</title>
</svelte:head>

<div class="p-8">
	<!-- Back button -->
	<button onclick={goBack} class="mb-4 flex items-center gap-2 text-gray-600 hover:text-gray-900">
		<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
		</svg>
		Back to Face Explorer
	</button>

	{#if loading}
		<div class="text-center py-12 text-gray-500">Loading cluster...</div>
	{:else if error}
		<div class="text-center py-12 text-red-500">{error}</div>
	{:else if cluster}
		<div class="max-w-4xl">
			<!-- Cluster Header -->
			<div class="flex items-start gap-6 mb-8">
				<!-- Representative Face -->
				<div class="flex-shrink-0">
					{#if cluster.representative_face}
						<img
							src="{API_HOST}{cluster.representative_face.crop_url}"
							alt={cluster.name ?? 'Unknown person'}
							class="w-32 h-32 rounded-full object-cover border-4 border-white shadow-lg"
						/>
					{:else}
						<div
							class="w-32 h-32 rounded-full bg-gray-200 flex items-center justify-center text-4xl"
						>
							&#128100;
						</div>
					{/if}
				</div>

				<!-- Cluster Info -->
				<div class="flex-1">
					{#if isEditing}
						<div class="flex items-center gap-2 mb-2">
							<input
								type="text"
								bind:value={editName}
								onkeydown={handleKeydown}
								class="text-2xl font-bold border border-gray-300 rounded px-2 py-1 w-64"
								placeholder="Enter name..."
								disabled={saving}
							/>
							<button
								onclick={() => void saveName()}
								disabled={saving || !editName.trim()}
								class="px-3 py-1 bg-blue-500 text-white rounded text-sm disabled:opacity-50"
							>
								{saving ? 'Saving...' : 'Save'}
							</button>
							<button
								onclick={cancelEditing}
								disabled={saving}
								class="px-3 py-1 border border-gray-300 rounded text-sm"
							>
								Cancel
							</button>
						</div>
					{:else}
						<div class="flex items-center gap-3 mb-2">
							<h1 class="text-2xl font-bold text-gray-900">
								{cluster.name ?? 'Unknown Person'}
							</h1>
							<button
								onclick={startEditing}
								class="text-gray-400 hover:text-gray-600"
								title="Edit name"
							>
								<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
									/>
								</svg>
							</button>
						</div>
					{/if}

					<div class="flex gap-4 text-sm text-gray-500">
						<span>{cluster.face_count} face{cluster.face_count !== 1 ? 's' : ''}</span>
						<span>{cluster.photo_count} photo{cluster.photo_count !== 1 ? 's' : ''}</span>
					</div>

					{#if !cluster.name}
						<p class="mt-3 text-sm text-gray-500">
							This person hasn't been named yet. Click the edit button to add a name.
						</p>
					{/if}
				</div>
			</div>

			<!-- Quick Tag Section -->
			<div class="mb-8 p-4 bg-blue-50 rounded-lg">
				<h3 class="text-sm font-medium text-blue-800 mb-2">Quick Tag</h3>
				<div class="flex items-center gap-2">
					<input
						type="text"
						bind:value={editName}
						placeholder="Type a name and press Enter..."
						onkeydown={(e) => {
							if (e.key === 'Enter' && editName.trim()) {
								void saveName();
							}
						}}
						class="flex-1 px-3 py-2 border border-blue-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
						disabled={saving}
					/>
					<button
						onclick={() => void saveName()}
						disabled={saving || !editName.trim()}
						class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
					>
						{saving ? 'Saving...' : 'Tag Person'}
					</button>
				</div>
			</div>

			<!-- All Faces in Cluster -->
			<div>
				<h2 class="text-lg font-semibold text-gray-900 mb-4">
					All Faces ({cluster.face_count})
				</h2>

				{#if faces.length === 0}
					<p class="text-gray-500">No faces loaded yet.</p>
				{:else}
					<div class="grid grid-cols-4 gap-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10">
						{#each faces as face (face.id)}
							<a
								href="/photos/{face.photo_id}"
								class="group block aspect-square rounded-lg overflow-hidden bg-gray-100 hover:ring-2 hover:ring-blue-500"
								title="View photo"
							>
								<img
									src="{API_HOST}{face.crop_url}"
									alt="Face"
									class="w-full h-full object-cover"
									loading="lazy"
								/>
							</a>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	{:else}
		<div class="text-center py-12 text-gray-500">Cluster not found</div>
	{/if}
</div>
