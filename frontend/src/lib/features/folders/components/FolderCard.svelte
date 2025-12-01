<script lang="ts">
	import type { WatchedFolder } from '../types';
	import { foldersStore } from '../stores/folders.svelte';

	interface Props {
		folder: WatchedFolder;
	}

	const { folder }: Props = $props();

	let scanning = $state(false);

	async function handleScan(): Promise<void> {
		scanning = true;
		try {
			await foldersStore.triggerScan(folder.id);
		} finally {
			scanning = false;
		}
	}
</script>

<div class="card p-4" data-testid="folder-card">
	<div class="flex items-start justify-between">
		<div class="flex-1">
			<h3 class="font-medium text-gray-900">{folder.name ?? folder.path}</h3>
			<p class="mt-1 text-sm text-gray-500">{folder.path}</p>
			<div class="mt-2 flex gap-3 text-xs text-gray-400">
				<span>{folder.recursive ? '📁 Recursive' : '📄 Top-level only'}</span>
				{#if folder.autoAlbum}
					<span>📚 Auto-albums</span>
				{/if}
			</div>
		</div>

		{#if folder.stats}
			<div class="text-right text-sm">
				<p class="text-gray-600">{folder.stats.processed} / {folder.stats.totalFiles}</p>
				{#if folder.stats.pending > 0}
					<p class="text-yellow-600">{folder.stats.pending} pending</p>
				{/if}
				{#if folder.stats.failed > 0}
					<p class="text-red-600">{folder.stats.failed} failed</p>
				{/if}
			</div>
		{/if}
	</div>

	<div class="mt-4 flex gap-2">
		<button type="button" class="btn-secondary text-sm" onclick={handleScan} disabled={scanning}>
			{scanning ? 'Scanning...' : 'Scan Now'}
		</button>
		<button type="button" class="btn-ghost text-sm text-red-600 hover:bg-red-50" onclick={() => foldersStore.remove(folder.id, false)}>
			Remove
		</button>
	</div>
</div>
