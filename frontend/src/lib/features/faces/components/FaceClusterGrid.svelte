<script lang="ts">
	import type { FaceClusterType } from '../types';
	import FaceCluster from './FaceCluster.svelte';

	interface Props {
		clusters: FaceClusterType[];
	}

	const { clusters = [] }: Props = $props();
</script>

<div data-testid="face-cluster-grid">
	{#if clusters.length === 0}
		<div class="card p-12 text-center">
			<div class="mb-4 text-4xl">&#128101;</div>
			<p class="text-gray-500">No face clusters yet</p>
			<p class="mt-2 text-sm text-gray-400">Upload photos with faces to start grouping</p>
		</div>
	{:else}
		<div class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
			{#each clusters as cluster (cluster.id)}
				<FaceCluster {cluster} />
			{/each}
		</div>
	{/if}
</div>
