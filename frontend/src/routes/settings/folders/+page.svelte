<script lang="ts">
	import { FolderList, AddFolderModal, type WatchedFolder } from '$features/folders';

	const folders: WatchedFolder[] = [];
	let showAddModal = false;
</script>

<svelte:head>
	<title>Watched Folders - Photo Explorer</title>
</svelte:head>

<div class="p-8">
	<header class="mb-8 flex items-center justify-between">
		<div>
			<h1 class="text-3xl font-bold text-gray-900">Watched Folders</h1>
			<p class="mt-2 text-gray-600">Automatically import photos from local directories</p>
		</div>
		<button type="button" class="btn-primary" on:click={() => (showAddModal = true)}>
			Add Folder
		</button>
	</header>

	<FolderList {folders} />

	{#if showAddModal}
		<AddFolderModal onClose={() => (showAddModal = false)} onAdded={() => (showAddModal = false)} />
	{/if}
</div>
