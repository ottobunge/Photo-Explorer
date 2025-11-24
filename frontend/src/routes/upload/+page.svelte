<script lang="ts">
	import { UploadZone, UploadProgress } from '$features/upload';

	let files: File[] = [];
	let uploading = false;

	function handleFilesSelected(event: CustomEvent<File[]>) {
		files = [...files, ...event.detail];
	}

	function removeFile(index: number) {
		files = files.filter((_, i) => i !== index);
	}

	async function handleUpload() {
		if (files.length === 0) return;
		uploading = true;
		// TODO: Call upload API
		await new Promise((resolve) => setTimeout(resolve, 2000));
		uploading = false;
		files = [];
	}
</script>

<svelte:head>
	<title>Upload Photos - Photo Explorer</title>
</svelte:head>

<div class="p-8">
	<header class="mb-8">
		<h1 class="text-3xl font-bold text-gray-900">Upload Photos</h1>
		<p class="mt-2 text-gray-600">Drag and drop photos or click to select</p>
	</header>

	<div class="mx-auto max-w-3xl">
		<UploadZone on:filesSelected={handleFilesSelected} disabled={uploading} />

		{#if files.length > 0}
			<div class="mt-6">
				<h2 class="mb-4 font-semibold text-gray-900">Selected Files ({files.length})</h2>
				<ul class="space-y-2">
					{#each files as file, index}
						<li class="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-3">
							<span class="truncate">{file.name}</span>
							<button
								type="button"
								class="text-gray-400 hover:text-red-500"
								on:click={() => removeFile(index)}
								disabled={uploading}
							>
								×
							</button>
						</li>
					{/each}
				</ul>

				<div class="mt-6 flex justify-end gap-4">
					<button type="button" class="btn-secondary" on:click={() => (files = [])} disabled={uploading}>
						Clear All
					</button>
					<button type="button" class="btn-primary" on:click={handleUpload} disabled={uploading}>
						{uploading ? 'Uploading...' : `Upload ${files.length} Photos`}
					</button>
				</div>
			</div>
		{/if}
	</div>
</div>
