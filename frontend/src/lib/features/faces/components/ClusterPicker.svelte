<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { API_HOST } from '$lib/api/client';
	import { facesStore } from '../stores/faces.svelte';
	import type { FaceClusterType } from '../types';

	interface Props {
		title?: string;
		excludeClusterIds?: string[];
	}

	let { title = 'Select a Person', excludeClusterIds = [] }: Props = $props();

	const dispatch = createEventDispatcher<{
		close: void;
		select: { cluster: FaceClusterType };
	}>();

	let searchQuery = $state('');
	let loading = $state(true);
	let error = $state('');

	// Derived state from store
	const storeClusters = $derived(facesStore.clusters);

	// Filtered clusters based on search and exclusions
	const filteredClusters = $derived.by(() => {
		return storeClusters
			.filter((cluster: FaceClusterType) => !excludeClusterIds.includes(cluster.id))
			.filter((cluster: FaceClusterType) => {
				if (!searchQuery.trim()) return true;
				const query = searchQuery.toLowerCase();
				const name = cluster.name?.toLowerCase() || 'unknown';
				return name.includes(query);
			})
			.sort((a: FaceClusterType, b: FaceClusterType) => {
				// Sort by name (named first, then by name alphabetically, then unnamed by photo count)
				if (a.name && !b.name) return -1;
				if (!a.name && b.name) return 1;
				if (a.name && b.name) return a.name.localeCompare(b.name);
				return b.photoCount - a.photoCount;
			});
	});

	onMount(async () => {
		try {
			await facesStore.load();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load clusters';
		} finally {
			loading = false;
		}
	});

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			dispatch('close');
		}
	}

	function handleSelect(cluster: FaceClusterType) {
		dispatch('select', { cluster });
	}

	function getCropUrl(cluster: FaceClusterType): string {
		if (!cluster.representativeFace) return '';
		return `${API_HOST}${cluster.representativeFace.cropUrl}`;
	}
</script>

<div
	class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
	on:click={handleBackdropClick}
	on:keydown={(e) => e.key === 'Escape' && dispatch('close')}
	role="dialog"
	aria-modal="true"
>
	<div class="card relative w-full max-w-2xl max-h-[80vh] flex flex-col p-6">
		<!-- Header -->
		<div class="mb-4">
			<h2 class="text-xl font-bold text-gray-900 mb-2">{title}</h2>

			<!-- Search input -->
			<input
				type="text"
				bind:value={searchQuery}
				placeholder="Search by name..."
				class="input w-full"
				disabled={loading}
			/>
		</div>

		<!-- Close button -->
		<button
			type="button"
			class="absolute right-4 top-4 text-gray-400 hover:text-gray-600"
			on:click={() => dispatch('close')}
			aria-label="Close modal"
		>
			×
		</button>

		<!-- Content -->
		<div class="flex-1 overflow-y-auto">
			{#if loading}
				<div class="flex items-center justify-center py-8">
					<p class="text-gray-500">Loading clusters...</p>
				</div>
			{:else if error}
				<div class="flex items-center justify-center py-8">
					<p class="text-red-500">{error}</p>
				</div>
			{:else if filteredClusters.length === 0}
				<div class="flex items-center justify-center py-8">
					<p class="text-gray-500">
						{searchQuery ? 'No clusters match your search' : 'No clusters available'}
					</p>
				</div>
			{:else}
				<div class="space-y-2">
					{#each filteredClusters as cluster (cluster.id)}
						<button
							type="button"
							class="w-full flex items-center gap-4 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 hover:border-gray-300 transition-colors text-left"
							on:click={() => handleSelect(cluster)}
						>
							<!-- Representative face -->
							<div class="flex-shrink-0">
								{#if cluster.representativeFace}
									<img
										src={getCropUrl(cluster)}
										alt={cluster.name || 'Unknown person'}
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
									{cluster.name || 'Unknown'}
								</p>
								<p class="text-sm text-gray-500">
									{cluster.faceCount} {cluster.faceCount === 1 ? 'face' : 'faces'} ·
									{cluster.photoCount} {cluster.photoCount === 1 ? 'photo' : 'photos'}
								</p>
							</div>

							<!-- Select indicator -->
							<div class="flex-shrink-0 text-gray-400">
								<svg
									class="w-5 h-5"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M9 5l7 7-7 7"
									/>
								</svg>
							</div>
						</button>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Footer -->
		<div class="mt-4 pt-4 border-t border-gray-200 flex justify-end">
			<button type="button" class="btn-secondary" on:click={() => dispatch('close')}>
				Cancel
			</button>
		</div>
	</div>
</div>
