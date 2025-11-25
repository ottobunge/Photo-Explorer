<script lang="ts">
	import { albumsStore } from '../stores/albums';

	interface Props {
		onClose: () => void;
		onCreated: () => void;
	}

	const { onClose, onCreated }: Props = $props();

	let name = $state('');
	let description = $state('');
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
			await albumsStore.create(name, description || undefined);
			onCreated();
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Failed to create album';
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

<div
	class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
	onclick={handleBackdropClick}
	onkeydown={handleKeydown}
	role="dialog"
	aria-modal="true"
	tabindex="-1"
>
	<div class="card w-full max-w-md p-6">
		<h2 class="mb-4 text-xl font-bold text-gray-900">Create Album</h2>

		<form onsubmit={(e) => { e.preventDefault(); void handleSubmit(); }}>
			<div class="mb-4">
				<label for="name" class="mb-1 block text-sm font-medium text-gray-700">Name</label>
				<input
					id="name"
					type="text"
					bind:value={name}
					class="input"
					placeholder="Summer Vacation 2024"
					disabled={loading}
				/>
			</div>

			<div class="mb-4">
				<label for="description" class="mb-1 block text-sm font-medium text-gray-700">
					Description (optional)
				</label>
				<textarea
					id="description"
					bind:value={description}
					class="input min-h-[80px]"
					placeholder="Photos from our trip to..."
					disabled={loading}
				></textarea>
			</div>

			{#if error}
				<p class="mb-4 text-sm text-red-500">{error}</p>
			{/if}

			<div class="flex justify-end gap-3">
				<button type="button" class="btn-secondary" onclick={onClose} disabled={loading}>
					Cancel
				</button>
				<button type="submit" class="btn-primary" disabled={loading}>
					{loading ? 'Creating...' : 'Create Album'}
				</button>
			</div>
		</form>
	</div>
</div>
