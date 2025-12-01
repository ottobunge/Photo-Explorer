<script lang="ts">
	import { fade, fly } from 'svelte/transition';
	import type { Snippet } from 'svelte';

	interface Props {
		title?: string;
		children?: Snippet;
		footer?: Snippet;
		onclose?: () => void;
	}

	const { title = '', children, footer, onclose }: Props = $props();

	function handleBackdropClick(e: MouseEvent): void {
		if (e.target === e.currentTarget) {
			onclose?.();
		}
	}

	function handleKeydown(e: KeyboardEvent): void {
		if (e.key === 'Escape') {
			onclose?.();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div
	class="fixed inset-0 z-50 flex items-center justify-center"
	transition:fade={{ duration: 150 }}
>
	<!-- Backdrop -->
	<div
		class="absolute inset-0 bg-black/50"
		onclick={handleBackdropClick}
		onkeydown={(e: KeyboardEvent) => {
			if (e.key === 'Enter') {
				handleBackdropClick(e as unknown as MouseEvent);
			}
		}}
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
		tabindex="-1"
	>
		{#if title}
			<h2 id="modal-title" class="mb-4 text-xl font-bold text-gray-900">{title}</h2>
		{/if}

		{@render children?.()}

		{#if footer}
			<div class="mt-4">
				{@render footer()}
			</div>
		{/if}

		<button
			type="button"
			class="absolute right-4 top-4 text-gray-400 hover:text-gray-600"
			onclick={() => onclose?.()}
			aria-label="Close modal"
		>
			×
		</button>
	</div>
</div>
