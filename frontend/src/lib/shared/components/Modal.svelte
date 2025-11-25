<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { fade, fly } from 'svelte/transition';

	export let title = '';

	const dispatch = createEventDispatcher<{ close: void }>();

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			dispatch('close');
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			dispatch('close');
		}
	}
</script>

<svelte:window on:keydown={handleKeydown} />

<div
	class="fixed inset-0 z-50 flex items-center justify-center"
	transition:fade={{ duration: 150 }}
>
	<!-- Backdrop -->
	<div
		class="absolute inset-0 bg-black/50"
		on:click={handleBackdropClick}
		role="button"
		tabindex="-1"
	></div>

	<!-- Modal -->
	<div
		class="card relative z-10 w-full max-w-md p-6"
		transition:fly={{ y: 20, duration: 200 }}
		role="dialog"
		aria-modal="true"
		aria-labelledby="modal-title"
	>
		{#if title}
			<h2 id="modal-title" class="mb-4 text-xl font-bold text-gray-900">{title}</h2>
		{/if}

		<slot />

		<button
			type="button"
			class="absolute right-4 top-4 text-gray-400 hover:text-gray-600"
			on:click={() => dispatch('close')}
			aria-label="Close modal"
		>
			×
		</button>
	</div>
</div>
