<script lang="ts">
	import { facesStore } from '../stores/faces.svelte';
	import type { FaceClusterType } from '../types';

	interface Props {
		cluster: FaceClusterType;
		onClose: () => void;
		onTagged: () => void;
	}

	const { cluster, onClose, onTagged }: Props = $props();

	let name = $state(cluster.name ?? '');
	let loading = $state(false);
	let error = $state('');

	async function handleSubmit(): Promise<void> {
		if (!name.trim()) {
			error = 'Name is required';
			return;
		}

		loading = true;
		error = '';

		try {
			await facesStore.nameCluster(cluster.id, name);
			onTagged();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to tag face';
		} finally {
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

		<form onsubmit={(e) => { e.preventDefault(); void handleSubmit(); }}>
			<div class="mb-4">
				<label for="name" class="mb-1 block text-sm font-medium text-gray-700">Name</label>
				<!-- svelte-ignore a11y_autofocus -->
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
				<button type="button" class="btn-secondary" onclick={onClose} disabled={loading}>
					Cancel
				</button>
				<button type="submit" class="btn-primary" disabled={loading}>
					{loading ? 'Saving...' : 'Save'}
				</button>
			</div>
		</form>
	</div>
</div>
