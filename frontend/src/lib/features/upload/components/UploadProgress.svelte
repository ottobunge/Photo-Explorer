<script lang="ts">
	import type { UploadItem } from '../types';
	import LoadingSpinner from '$lib/shared/components/LoadingSpinner.svelte';

	interface Props {
		items?: UploadItem[];
		oncancel?: (itemId: string) => void;
		onretry?: (itemId: string) => void;
		onremove?: (itemId: string) => void;
		onclearCompleted?: () => void;
	}

	const {
		items = [],
		oncancel,
		onretry,
		onremove,
		onclearCompleted
	}: Props = $props();

	// Derived values
	const completedCount = $derived(items.filter(item => item.status === 'completed').length);
	const uploadingCount = $derived(items.filter(item => item.status === 'uploading').length);
	const pendingCount = $derived(items.filter(item => item.status === 'pending').length);
	const failedCount = $derived(items.filter(item => item.status === 'failed').length);

	const totalProgress = $derived(() => {
		if (items.length === 0) return 0;
		const sum = items.reduce((acc, item) => acc + (item.progress || 0), 0);
		return Math.round(sum / items.length);
	});

	const hasCompletedItems = $derived(completedCount > 0);

	// Format file size for display
	function formatFileSize(bytes: number): string {
		if (bytes === 0) return '0 B';
		const k = 1024;
		const sizes = ['B', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
	}

	// Get status text
	function getStatusText(status: UploadItem['status']): string {
		switch (status) {
			case 'pending':
				return 'Waiting...';
			case 'uploading':
				return 'Uploading...';
			case 'completed':
				return 'Complete';
			case 'failed':
				return 'Failed';
			default:
				return '';
		}
	}

	// Handle action clicks
	function handleCancel(itemId: string): void {
		oncancel?.(itemId);
	}

	function handleRetry(itemId: string): void {
		onretry?.(itemId);
	}

	function handleRemove(itemId: string): void {
		onremove?.(itemId);
	}

	function handleClearCompleted(): void {
		onclearCompleted?.();
	}
</script>

<div class="space-y-2" data-testid="upload-progress">
	{#each items as item, index (item.id)}
		<div
			class="rounded-lg border border-gray-200 bg-white p-3 {item.status}"
			data-testid="upload-item-{item.id}"
		>
			<div class="flex items-center justify-between">
				<div class="flex items-center flex-1 min-w-0">
					{#if item.status === 'completed'}
						<span class="text-green-500 mr-2" data-testid="completed-icon">✓</span>
					{:else if item.status === 'uploading'}
						<span class="mr-2" data-testid="uploading-spinner">
							<LoadingSpinner size="sm" />
						</span>
					{:else if item.status === 'failed'}
						<span class="text-red-500 mr-2" data-testid="failed-icon">✗</span>
					{:else}
						<span class="text-gray-400 mr-2" data-testid="pending-icon">○</span>
					{/if}

					<div class="flex-1 min-w-0">
						<span
							class="truncate text-sm font-medium text-gray-700 block"
							data-testid="file-name"
							title={item.file.name || 'Unnamed file'}
						>
							{item.file.name || 'Unnamed file'}
						</span>
						<span class="text-xs text-gray-500" data-testid="file-size">
							{formatFileSize(item.file.size || 0)}
						</span>
					</div>
				</div>

				<div class="flex items-center gap-2 ml-4">
					<span
						class="text-xs font-medium"
						class:text-gray-500={item.status === 'pending'}
						class:text-primary-600={item.status === 'uploading'}
						class:text-green-600={item.status === 'completed'}
						class:text-red-600={item.status === 'failed'}
					>
						{#if item.status === 'uploading'}
							{item.progress}%
						{:else}
							{getStatusText(item.status)}
						{/if}
					</span>

					{#if item.status === 'uploading' && oncancel}
						<button
							type="button"
							onclick={() => handleCancel(item.id)}
							class="text-gray-400 hover:text-gray-600 transition-colors"
							aria-label="Cancel upload"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
							</svg>
						</button>
					{:else if item.status === 'failed' && onretry}
						<button
							type="button"
							onclick={() => handleRetry(item.id)}
							class="text-primary-600 hover:text-primary-700 transition-colors"
							aria-label="Retry upload"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
							</svg>
						</button>
					{:else if item.status === 'completed' && onremove}
						<button
							type="button"
							onclick={() => handleRemove(item.id)}
							class="text-gray-400 hover:text-gray-600 transition-colors"
							aria-label="Remove from list"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
							</svg>
						</button>
					{/if}
				</div>
			</div>

			<div class="mt-2">
				<div
					class="h-1.5 w-full overflow-hidden rounded-full bg-gray-200"
					role="progressbar"
					aria-valuemin="0"
					aria-valuemax="100"
					aria-valuenow={item.progress}
					aria-label="Upload progress"
				>
					<div
						class="h-full transition-all duration-300"
						class:bg-primary-600={item.status === 'uploading'}
						class:bg-green-600={item.status === 'completed'}
						class:bg-red-600={item.status === 'failed'}
						class:bg-gray-400={item.status === 'pending'}
						style="width: {item.progress}%"
					></div>
				</div>
			</div>

			{#if item.error}
				<p class="mt-1 text-xs text-red-500">{item.error}</p>
			{/if}
		</div>
	{/each}

	{#if items.length > 0}
		<!-- Summary section -->
		<div class="border-t pt-2 mt-2" data-testid="upload-summary">
			<div class="flex items-center justify-between text-sm">
				<div class="flex gap-4 text-xs">
					{#if uploadingCount > 0}
						<span data-testid="uploading-count" class="text-primary-600">
							Uploading: {uploadingCount}
						</span>
					{/if}
					{#if pendingCount > 0}
						<span data-testid="pending-count" class="text-gray-500">
							Pending: {pendingCount}
						</span>
					{/if}
					{#if completedCount > 0}
						<span data-testid="completed-count" class="text-green-600">
							Completed: {completedCount}
						</span>
					{/if}
					{#if failedCount > 0}
						<span data-testid="failed-count" class="text-red-600">
							Failed: {failedCount}
						</span>
					{/if}
				</div>

				{#if hasCompletedItems && onclearCompleted}
					<button
						type="button"
						onclick={handleClearCompleted}
						class="text-xs text-primary-600 hover:text-primary-700 transition-colors"
						aria-label="Clear completed"
					>
						Clear completed
					</button>
				{/if}
			</div>

			{#if totalProgress() > 0}
				<div class="mt-2 text-xs text-gray-500" data-testid="total-progress">
					Overall progress: {totalProgress()}%
				</div>
			{/if}
		</div>
	{/if}

	<!-- Live region for accessibility announcements -->
	<div aria-live="polite" aria-atomic="true" class="sr-only">
		{#if items.length > 0}
			Upload progress: {completedCount} completed, {uploadingCount} uploading, {pendingCount} pending, {failedCount} failed
		{/if}
	</div>
</div>

<style>
	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}
</style>