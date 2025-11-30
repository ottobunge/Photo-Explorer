<script lang="ts">
	import type { UploadItem } from '../types';

	interface Props {
		items?: UploadItem[];
	}

	const { items = [] }: Props = $props();
</script>

{#if items.length > 0}
	<div class="space-y-2" data-testid="upload-progress">
		{#each items as item (item.id)}
			<div class="rounded-lg border border-gray-200 bg-white p-3">
				<div class="flex items-center justify-between">
					<span class="truncate text-sm font-medium text-gray-700">{item.file.name}</span>
					<span class="ml-2 text-xs" class:text-gray-500={item.status === 'pending'}
						class:text-primary-600={item.status === 'uploading'}
						class:text-green-600={item.status === 'completed'}
						class:text-red-600={item.status === 'failed'}>
						{#if item.status === 'pending'}
							Waiting...
						{:else if item.status === 'uploading'}
							{item.progress}%
						{:else if item.status === 'completed'}
							Done
						{:else}
							Failed
						{/if}
					</span>
				</div>

				{#if item.status === 'uploading'}
					<div class="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-gray-200">
						<div
							class="h-full bg-primary-600 transition-all duration-300"
							style="width: {item.progress}%"
						></div>
					</div>
				{/if}

				{#if item.error}
					<p class="mt-1 text-xs text-red-500">{item.error}</p>
				{/if}
			</div>
		{/each}
	</div>
{/if}
