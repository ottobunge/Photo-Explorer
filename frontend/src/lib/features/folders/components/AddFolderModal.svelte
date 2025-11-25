<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { foldersStore } from '../stores/folders';

	const dispatch = createEventDispatcher<{ close: void; added: void }>();

	let path = '';
	let name = '';
	let recursive = true;
	let autoAlbum = false;
	let loading = false;
	let error = '';

	async function handleSubmit() {
		if (!path.trim()) {
			error = 'Path is required';
			return;
		}

		loading = true;
		error = '';

		try {
			await foldersStore.add(path, {
				name: name || undefined,
				recursive,
				autoAlbum
			});
			dispatch('added');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to add folder';
		} finally {
			loading = false;
		}
	}

	function handleBackdropClick(e: MouseEvent) {
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
>
	<div class="card w-full max-w-md p-6">
		<h2 class="mb-4 text-xl font-bold text-gray-900">Add Watched Folder</h2>

		<form on:submit|preventDefault={handleSubmit}>
			<div class="mb-4">
				<label for="path" class="mb-1 block text-sm font-medium text-gray-700">Folder Path</label>
				<input
					id="path"
					type="text"
					bind:value={path}
					class="input"
					placeholder="/home/user/Pictures"
					disabled={loading}
				/>
				<p class="mt-1 text-xs text-gray-500">Absolute path to the folder on your system</p>
			</div>

			<div class="mb-4">
				<label for="name" class="mb-1 block text-sm font-medium text-gray-700">
					Display Name (optional)
				</label>
				<input
					id="name"
					type="text"
					bind:value={name}
					class="input"
					placeholder="My Photos"
					disabled={loading}
				/>
			</div>

			<div class="mb-4 space-y-2">
				<label class="flex items-center gap-2">
					<input type="checkbox" bind:checked={recursive} class="rounded" disabled={loading} />
					<span class="text-sm text-gray-700">Include subfolders</span>
				</label>
				<label class="flex items-center gap-2">
					<input type="checkbox" bind:checked={autoAlbum} class="rounded" disabled={loading} />
					<span class="text-sm text-gray-700">Create albums from subfolders</span>
				</label>
			</div>

			{#if error}
				<p class="mb-4 text-sm text-red-500">{error}</p>
			{/if}

			<div class="flex justify-end gap-3">
				<button type="button" class="btn-secondary" on:click={() => dispatch('close')} disabled={loading}>
					Cancel
				</button>
				<button type="submit" class="btn-primary" disabled={loading}>
					{loading ? 'Adding...' : 'Add Folder'}
				</button>
			</div>
		</form>
	</div>
</div>
