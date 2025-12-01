<script lang="ts">
	import Modal from './Modal.svelte';
	import type { Snippet } from 'svelte';

	interface Props {
		showModal?: boolean;
		title?: string;
		content?: string;
		footerContent?: string;
		onclose?: () => void;
	}

	const {
		showModal = false,
		title,
		content = '',
		footerContent = '',
		onclose
	}: Props = $props();
</script>

{#if showModal}
	<Modal {title} {onclose}>
		{#snippet children()}
			{#if content}
				<p>{content}</p>
			{/if}
		{/snippet}

		{#snippet footer()}
			{#if footerContent}
				<div>{footerContent}</div>
			{/if}
		{/snippet}
	</Modal>
{/if}