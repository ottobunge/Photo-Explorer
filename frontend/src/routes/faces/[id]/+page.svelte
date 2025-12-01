<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { client, API_HOST } from '$lib/api/client';
	import { faceSelectionStore } from '$lib/features/faces/stores/face-selection.svelte';
	import { ClusterPicker } from '$lib/features/faces';
	import type { FaceClusterType } from '$lib/features/faces/types';

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

	let cluster = $state<ClusterData | null>(null);
	let faces = $state<Face[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let isEditing = $state(false);
	let editName = $state('');
	let saving = $state(false);
	let showClusterPicker = $state(false);
	let operationInProgress = $state(false);

	const clusterId = $derived($page.params.id);
	const editMode = $derived(faceSelectionStore.editMode);
	const selectedFaceIds = $derived(faceSelectionStore.selectedFaceIds);
	const selectedCount = $derived(faceSelectionStore.selectedFaceCount);
	const allSelected = $derived(faces.length > 0 && faces.every((f) => selectedFaceIds.has(f.id)));

	onMount(() => {
		void loadCluster();
	});

	async function loadCluster(): Promise<void> {
		loading = true;
		error = null;
		try {
			const res = await client.get<ClusterData>(`/faces/clusters/${clusterId}`);
			if (res.success) {
				cluster = res.data;
				editName = cluster.name ?? '';
			}

			// Load faces in this cluster
			const facesRes = await client.get<{ faces: Face[] }>(
				`/faces/clusters/${clusterId}/faces`
			);
			if (facesRes.success) {
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
			if (res.success) {
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

	function toggleEditMode(): void {
		faceSelectionStore.toggleEditMode();
	}

	function toggleSelectAll(): void {
		if (allSelected) {
			faceSelectionStore.clearFaceSelection();
		} else {
			faceSelectionStore.selectAllFaces(
				faces.map((f) => ({ id: f.id, photoId: f.photo_id, cropUrl: f.crop_url }))
			);
		}
	}

	function toggleFaceSelection(faceId: string): void {
		faceSelectionStore.toggleFace(faceId);
	}

	async function handleSplitSelected(): Promise<void> {
		if (selectedCount === 0) {return;}

		if (
			!confirm(
				`Split ${selectedCount} face${selectedCount > 1 ? 's' : ''} into ${selectedCount > 1 ? 'separate' : 'a new'} cluster${selectedCount > 1 ? 's' : ''}?`
			)
		) {
			return;
		}

		operationInProgress = true;
		try {
			await faceSelectionStore.splitSelectedFaces();
			await loadCluster();
		} catch (err) {
			console.error('Failed to split faces:', err);
			error = err instanceof Error ? err.message : 'Failed to split faces';
		} finally {
			operationInProgress = false;
		}
	}

	function handleMoveSelected(): void {
		if (selectedCount === 0) {return;}
		showClusterPicker = true;
	}

	async function handleClusterSelected(selectedCluster: FaceClusterType): Promise<void> {
		showClusterPicker = false;
		operationInProgress = true;

		try {
			await faceSelectionStore.moveSelectedFaces(selectedCluster.id);
			await loadCluster();
		} catch (err) {
			console.error('Failed to move faces:', err);
			error = err instanceof Error ? err.message : 'Failed to move faces';
		} finally {
			operationInProgress = false;
		}
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
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-lg font-semibold text-gray-900">
						All Faces ({cluster.face_count})
					</h2>

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

				{#if faces.length === 0}
					<p class="text-gray-500">No faces loaded yet.</p>
				{:else}
					<div class="grid grid-cols-4 gap-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10">
						{#each faces as face (face.id)}
							{#if editMode}
								<!-- Selectable face in edit mode -->
								<button
									type="button"
									onclick={() => { toggleFaceSelection(face.id); }}
									class="relative aspect-square rounded-lg overflow-hidden bg-gray-100 transition-all"
									class:ring-4={selectedFaceIds.has(face.id)}
									class:ring-blue-500={selectedFaceIds.has(face.id)}
									disabled={operationInProgress}
								>
									<img
										src="{API_HOST}{face.crop_url}"
										alt="Face"
										class="w-full h-full object-cover"
										loading="lazy"
									/>

									<!-- Checkbox overlay -->
									<div
										class="absolute top-2 right-2 w-6 h-6 rounded-full flex items-center justify-center transition-colors"
										class:bg-blue-500={selectedFaceIds.has(face.id)}
										class:bg-white={!selectedFaceIds.has(face.id)}
										class:border-2={!selectedFaceIds.has(face.id)}
										class:border-gray-300={!selectedFaceIds.has(face.id)}
									>
										{#if selectedFaceIds.has(face.id)}
											<svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
												<path
													fill-rule="evenodd"
													d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
													clip-rule="evenodd"
												/>
											</svg>
										{/if}
									</div>
								</button>
							{:else}
								<!-- Regular clickable face -->
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
							{/if}
						{/each}
					</div>
				{/if}
			</div>
		</div>
	{:else}
		<div class="text-center py-12 text-gray-500">Cluster not found</div>
	{/if}

	<!-- Floating Action Bar (shown when in edit mode and faces are selected) -->
	{#if editMode && selectedCount > 0}
		<div
			class="fixed bottom-8 left-1/2 -translate-x-1/2 z-40 bg-white rounded-full shadow-2xl border border-gray-200 px-6 py-4"
		>
			<div class="flex items-center gap-6">
				<!-- Selection count -->
				<div class="flex items-center gap-2">
					<span class="text-sm font-medium text-gray-900">
						{selectedCount} selected
					</span>
					<button
						type="button"
						onclick={toggleSelectAll}
						class="text-sm text-blue-600 hover:text-blue-700"
						disabled={operationInProgress}
					>
						{allSelected ? 'Deselect All' : 'Select All'}
					</button>
				</div>

				<div class="h-6 w-px bg-gray-300"></div>

				<!-- Actions -->
				<div class="flex items-center gap-3">
					<button
						type="button"
						onclick={() => void handleSplitSelected()}
						disabled={operationInProgress}
						class="px-4 py-2 text-sm bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50 transition-colors"
						title="Split selected faces into new clusters"
					>
						Split
					</button>

					<button
						type="button"
						onclick={handleMoveSelected}
						disabled={operationInProgress}
						class="px-4 py-2 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 transition-colors"
						title="Move selected faces to another cluster"
					>
						Move
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- Cluster Picker Modal -->
	{#if showClusterPicker && clusterId}
		<ClusterPicker
			title="Move Faces To..."
			excludeClusterIds={[clusterId]}
			onclose={() => (showClusterPicker = false)}
			onselect={handleClusterSelected}
		/>
	{/if}
</div>
