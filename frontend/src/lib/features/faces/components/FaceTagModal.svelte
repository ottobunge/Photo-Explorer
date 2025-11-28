<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { facesStore } from '../stores/faces.svelte';
	import type { FaceClusterType } from '../types';

	export let cluster: FaceClusterType;

	const dispatch = createEventDispatcher<{ close: void; tagged: void }>();

	let name = cluster.name ?? '';
	let loading = false;
	let error = '';

	async function handleSubmit(): Promise<void> {
		if (!name.trim()) {
			error = 'Name is required';
			return;
		}

		loading = true;
		error = '';

		try {
			await facesStore.nameCluster(cluster.id, name);
			dispatch('tagged');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to tag face';
		} finally {
			loading = false;
		}
	}

	function handleBackdropClick(e: MouseEvent): void {
		if (e.target === e.currentTarget) {
			dispatch('close');
		}
	}
</script>

<div
	class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
	on:click={handleBackdropClick}
	on:keydown={(e) => e.key === 'Escape' && dispatch('close')}
	role="dialog"
	aria-modal="true"
	aria-labelledby="face-tag-modal-title"
	tabindex="-1"
>
	<div class="card w-full max-w-sm p-6">
		<div class="mb-4 flex items-center gap-4">
			{#if cluster.representativeFace}
				<img
					src={cluster.representativeFace.cropUrl}
					alt="Face preview"
					class="h-16 w-16 rounded-full object-cover"
				/>
			{/if}
			<h2 id="face-tag-modal-title" class="text-xl font-bold text-gray-900">Tag This Person</h2>
		</div>

		<form on:submit|preventDefault={handleSubmit}>
			<div class="mb-4">
				<label for="name" class="mb-1 block text-sm font-medium text-gray-700">Name</label>
				<input
					id="name"
					type="text"
					bind:value={name}
					class="input"
					placeholder="John Doe"
					disabled={loading}
					autofocus
				/>
			</div>

			{#if error}
				<p class="mb-4 text-sm text-red-500">{error}</p>
			{/if}

			<div class="flex justify-end gap-3">
				<button type="button" class="btn-secondary" on:click={() => dispatch('close')} disabled={loading}>
					Cancel
				</button>
				<button type="submit" class="btn-primary" disabled={loading}>
					{loading ? 'Saving...' : 'Save'}
				</button>
			</div>
		</form>
	</div>
</div>
