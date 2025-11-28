<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let disabled = false;
	export let accept = 'image/*';

	const dispatch = createEventDispatcher<{ filesSelected: File[] }>();

	let dragOver = false;
	let fileInput: HTMLInputElement;

	function handleDragOver(e: DragEvent) {
		e.preventDefault();
		if (!disabled) {dragOver = true;}
	}

	function handleDragLeave() {
		dragOver = false;
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		dragOver = false;
		if (disabled) {return;}

		const files = Array.from(e.dataTransfer?.files || []).filter((f) =>
			f.type.startsWith('image/')
		);
		if (files.length > 0) {
			dispatch('filesSelected', files);
		}
	}

	function handleFileSelect(e: Event) {
		const input = e.target as HTMLInputElement;
		const files = Array.from(input.files || []);
		if (files.length > 0) {
			dispatch('filesSelected', files);
		}
		input.value = '';
	}

	function handleClick() {
		if (!disabled) {fileInput.click();}
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			handleClick();
		}
	}
</script>

<div
	class="relative rounded-xl border-2 border-dashed p-12 text-center transition-colors"
	class:border-gray-300={!dragOver}
	class:bg-gray-50={!dragOver}
	class:border-primary-500={dragOver}
	class:bg-primary-50={dragOver}
	class:opacity-50={disabled}
	class:cursor-not-allowed={disabled}
	class:cursor-pointer={!disabled}
	on:dragover={handleDragOver}
	on:dragleave={handleDragLeave}
	on:drop={handleDrop}
	on:click={handleClick}
	on:keydown={handleKeyDown}
	role="button"
	tabindex={disabled ? -1 : 0}
	data-testid="upload-zone"
>
	<input
		bind:this={fileInput}
		type="file"
		{accept}
		multiple
		class="hidden"
		on:change={handleFileSelect}
		{disabled}
	/>

	<div class="pointer-events-none">
		<div class="mb-4 text-5xl">📷</div>
		<p class="text-lg font-medium text-gray-700">
			{dragOver ? 'Drop photos here' : 'Drag & drop photos here'}
		</p>
		<p class="mt-2 text-gray-500">or click to select files</p>
		<p class="mt-4 text-sm text-gray-400">Supports JPEG, PNG, WebP, HEIC</p>
	</div>
</div>
