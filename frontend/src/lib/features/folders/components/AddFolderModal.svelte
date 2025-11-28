<script lang="ts">
	import { foldersStore } from '../stores/folders';

	interface Props {
		onClose: () => void;
		onAdded: () => void;
	}

	const { onClose, onAdded }: Props = $props();

	let path = $state('');
	let name = $state('');
	let recursive = $state(true);
	let autoAlbum = $state(false);
	let loading = $state(false);
	let error = $state('');

	async function handleSubmit(): Promise<void> {
		if (!path.trim()) {
			error = 'Path is required';
			return;
		}

		loading = true;
		error = '';

		try {
			const options: { name?: string; recursive?: boolean; autoAlbum?: boolean } = {
				recursive,
				autoAlbum
			};
			if (name) {
				options.name = name;
			}
			await foldersStore.add(path, options);
			onAdded();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to add folder';
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
	<div class="card w-full max-w-md p-6">
		<h2 id="add-folder-modal-title" class="mb-4 text-xl font-bold text-gray-900">Add Watched Folder</h2>

		<form onsubmit={(e) => { e.preventDefault(); void handleSubmit(); }}>
			<div class="mb-4">
				<label for="path" class="mb-1 block text-sm font-medium text-gray-700">Folder Path</label>
				<!-- svelte-ignore a11y_autofocus -->
				<input
					id="path"
					type="text"
					bind:value={path}
					class="input"
					placeholder="/home/user/Pictures"
					disabled={loading}
					autofocus
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
				<button type="button" class="btn-secondary" onclick={onClose} disabled={loading}>
					Cancel
				</button>
				<button type="submit" class="btn-primary" disabled={loading}>
					{loading ? 'Adding...' : 'Add Folder'}
				</button>
			</div>
		</form>
	</div>
</div>
