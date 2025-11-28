<script lang="ts">
	import { API_HOST } from '$lib/api/client';
	import { faceSelectionStore } from '../stores/face-selection.svelte';
	import type { FaceClusterType } from '../types';

	interface Props {
		clusters: FaceClusterType[];
		onClose: () => void;
		onMerged: (targetCluster: FaceClusterType) => void;
	}

	const { clusters, onClose, onMerged }: Props = $props();

	let selectedTargetId = $state(clusters.length > 0 && clusters[0] !== undefined ? clusters[0].id : '');
	let loading = $state(false);
	let error = $state('');

	// Calculate totals using $derived
	const totalFaces = $derived(clusters.reduce((sum, c) => sum + c.faceCount, 0));
	const totalPhotos = $derived(clusters.reduce((sum, c) => sum + c.photoCount, 0));
	const targetCluster = $derived(clusters.find((c) => c.id === selectedTargetId));
	const sourceCount = $derived(clusters.length - 1);

	async function handleMerge(): Promise<void> {
		if (!selectedTargetId) {
			error = 'Please select a target cluster';
			return;
		}

		loading = true;
		error = '';

		try {
			const result = await faceSelectionStore.mergeSelectedClusters(selectedTargetId);
			onMerged(result);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to merge clusters';
			loading = false;
		}
	}

	function handleBackdropClick(e: MouseEvent): void {
		if (e.target === e.currentTarget) {
			onClose();
		}
	}

	function handleKeydown(e: KeyboardEvent): void {
		if (e.key === 'Escape') {
			onClose();
		}
	}

	function getCropUrl(cluster: FaceClusterType): string {
		if (!cluster.representativeFace) {return '';}
		return `${API_HOST}${cluster.representativeFace.cropUrl}`;
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div
	class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
	onclick={handleBackdropClick}
	onkeydown={(e: KeyboardEvent) => {
		if (e.key === 'Enter') {
			handleBackdropClick(e as unknown as MouseEvent);
		}
	}}
	role="button"
	tabindex="-1"
>
	<div class="card relative w-full max-w-2xl max-h-[80vh] flex flex-col p-6">
		<!-- Header -->
		<div class="mb-4">
			<h2 id="cluster-merge-modal-title" class="text-xl font-bold text-gray-900 mb-2">Merge {clusters.length} Clusters</h2>
			<p class="text-sm text-gray-600">
				Select which person these clusters should be merged into. The other clusters will be
				deleted.
			</p>
		</div>

		<!-- Close button -->
		<button
			type="button"
			class="absolute right-4 top-4 text-gray-400 hover:text-gray-600"
			onclick={onClose}
			aria-label="Close modal"
		>
			×
		</button>

		<!-- Content -->
		<div class="flex-1 overflow-y-auto">
			<!-- Summary -->
			<div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
				<p class="text-sm text-blue-900">
					<strong>Total:</strong>
					{totalFaces} {totalFaces === 1 ? 'face' : 'faces'} across
					{totalPhotos} {totalPhotos === 1 ? 'photo' : 'photos'}
				</p>
			</div>

			<!-- Target selection -->
			<div class="mb-4">
				<p class="block text-sm font-medium text-gray-700 mb-2">
					Select merge target (keep this person):
				</p>

				<div class="space-y-2">
					{#each clusters as cluster (cluster.id)}
						<label
							class="flex items-center gap-4 p-3 rounded-lg border cursor-pointer transition-colors"
							class:bg-blue-50={selectedTargetId === cluster.id}
							class:border-blue-500={selectedTargetId === cluster.id}
							class:border-gray-200={selectedTargetId !== cluster.id}
							class:hover:bg-gray-50={selectedTargetId !== cluster.id}
						>
							<input
								type="radio"
								name="target"
								value={cluster.id}
								bind:group={selectedTargetId}
								class="text-blue-600 focus:ring-blue-500"
								disabled={loading}
							/>

							<!-- Representative face -->
							<div class="flex-shrink-0">
								{#if cluster.representativeFace}
									<img
										src={getCropUrl(cluster)}
										alt={cluster.name ?? 'Unknown person'}
										class="h-16 w-16 rounded-full object-cover"
									/>
								{:else}
									<div
										class="h-16 w-16 rounded-full bg-gray-200 flex items-center justify-center"
									>
										<span class="text-gray-400 text-xl">?</span>
									</div>
								{/if}
							</div>

							<!-- Cluster info -->
							<div class="flex-1 min-w-0">
								<p class="font-medium text-gray-900 truncate">
									{cluster.name ?? 'Unknown'}
								</p>
								<p class="text-sm text-gray-500">
									{cluster.faceCount} {cluster.faceCount === 1 ? 'face' : 'faces'} ·
									{cluster.photoCount} {cluster.photoCount === 1 ? 'photo' : 'photos'}
								</p>
							</div>
						</label>
					{/each}
				</div>
			</div>

			<!-- Warning -->
			{#if targetCluster}
				<div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
					<div class="flex gap-2">
						<svg
							class="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5"
							fill="currentColor"
							viewBox="0 0 20 20"
						>
							<path
								fill-rule="evenodd"
								d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
								clip-rule="evenodd"
							/>
						</svg>
						<div>
							<p class="text-sm font-medium text-yellow-900">This action cannot be undone</p>
							<p class="text-sm text-yellow-700 mt-1">
								{sourceCount}
								{sourceCount === 1 ? 'cluster' : 'clusters'} will be merged into
								<strong>{targetCluster.name ?? 'Unknown'}</strong>
								and deleted.
							</p>
						</div>
					</div>
				</div>
			{/if}

			{#if error}
				<div class="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
					<p class="text-sm text-red-600">{error}</p>
				</div>
			{/if}
		</div>

		<!-- Footer -->
		<div class="mt-4 pt-4 border-t border-gray-200 flex justify-end gap-3">
			<button
				type="button"
				class="btn-secondary"
				onclick={onClose}
				disabled={loading}
			>
				Cancel
			</button>
			<button type="button" class="btn-primary" onclick={handleMerge} disabled={loading}>
				{loading ? 'Merging...' : 'Merge Clusters'}
			</button>
		</div>
	</div>
</div>
