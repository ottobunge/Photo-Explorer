<script lang="ts">
	import type { FaceClusterType } from '../types';

	interface Props {
		cluster: FaceClusterType;
	}

	const { cluster }: Props = $props();
</script>

<a
	href="/faces/{cluster.id}"
	class="group block rounded-lg border border-gray-200 bg-white p-3 transition-shadow hover:shadow-md"
	data-testid="face-cluster"
>
	<div class="mx-auto mb-2 aspect-square w-24 overflow-hidden rounded-full bg-gray-100">
		{#if cluster.representativeFace}
			<img
				src={cluster.representativeFace.cropUrl}
				alt={cluster.name ?? 'Unknown person'}
				class="h-full w-full object-cover"
				loading="lazy"
			/>
		{:else}
			<div class="flex h-full items-center justify-center text-2xl text-gray-300">&#128100;</div>
		{/if}
	</div>
	<div class="text-center">
		<p class="font-medium text-gray-900 group-hover:text-primary-600">
			{cluster.name ?? 'Unknown'}
		</p>
		<p class="text-sm text-gray-500">{cluster.faceCount} faces</p>
		<p class="text-xs text-gray-400">{cluster.photoCount} photos</p>
	</div>
</a>
