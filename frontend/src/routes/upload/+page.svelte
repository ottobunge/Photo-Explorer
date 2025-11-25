<script lang="ts">
	import { UploadZone, UploadProgress } from '$features/upload';
	import { client } from '$lib/api/client';
	import { goto } from '$app/navigation';

	let files: File[] = [];
	let uploading = false;
	let uploadProgress = 0;
	let uploadedCount = 0;
	let failedCount = 0;
	let error: string | null = null;

	function handleFilesSelected(event: CustomEvent<File[]>) {
		files = [...files, ...event.detail];
		error = null;
	}

	function removeFile(index: number) {
		files = files.filter((_, i) => i !== index);
	}

	async function handleUpload() {
		if (files.length === 0) return;

		uploading = true;
		uploadProgress = 0;
		uploadedCount = 0;
		failedCount = 0;
		error = null;

		try {
			// Create FormData with all files
			const formData = new FormData();
			for (const file of files) {
				formData.append('files', file);
			}

			// Upload to API
			const response = await fetch('http://localhost:8000/api/v1/photos/upload', {
				method: 'POST',
				body: formData,
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.detail || 'Upload failed');
			}

			const result = await response.json();

			if (result.success && result.data) {
				uploadedCount = result.data.uploaded?.length || 0;
				failedCount = result.data.failed?.length || 0;

				if (failedCount > 0) {
					console.warn('Some uploads failed:', result.data.failed);
				}

				// Show success and redirect after a moment
				uploadProgress = 100;
				await new Promise((resolve) => setTimeout(resolve, 1000));

				// Redirect to photos page
				goto('/search');
			} else {
				throw new Error('Upload failed');
			}
		} catch (err: unknown) {
			error = err instanceof Error ? err.message : 'Upload failed';
			console.error('Upload error:', err);
		} finally {
			uploading = false;
			if (!error) {
				files = [];
			}
		}
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

		{#if error}
			<div class="mt-4 rounded-lg bg-red-50 border border-red-200 p-4">
				<div class="flex items-start gap-3">
					<svg class="w-5 h-5 text-red-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
					<div>
						<p class="font-medium text-red-800">Upload failed</p>
						<p class="text-sm text-red-700 mt-1">{error}</p>
					</div>
				</div>
			</div>
		{/if}

		{#if uploading}
			<div class="mt-4 rounded-lg bg-blue-50 border border-blue-200 p-4">
				<div class="flex items-center gap-3">
					<svg class="w-5 h-5 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
					<div class="flex-1">
						<p class="font-medium text-blue-900">Uploading {files.length} photos...</p>
						<p class="text-sm text-blue-700 mt-1">Photos will be processed in the background</p>
					</div>
				</div>
			</div>
		{/if}

		{#if files.length > 0 && !uploading}
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
							>
								×
							</button>
						</li>
					{/each}
				</ul>

				<div class="mt-6 flex justify-end gap-4">
					<button type="button" class="btn-secondary" on:click={() => (files = [])}>
						Clear All
					</button>
					<button type="button" class="btn-primary" on:click={handleUpload}>
						Upload {files.length} Photo{files.length === 1 ? '' : 's'}
					</button>
				</div>
			</div>
		{/if}
	</div>
</div>
