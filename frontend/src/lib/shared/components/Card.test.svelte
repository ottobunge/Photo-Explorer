<script lang="ts">
	import Card from './Card.svelte';

	interface Props {
		showCard?: boolean;
		title?: string;
		subtitle?: string;
		content?: string;
		headerContent?: string;
		footerContent?: string;
		actionsContent?: string;
		imageUrl?: string;
		imageAlt?: string;
		complexContent?: boolean;
		[key: string]: unknown;
	}

	const {
		showCard = false,
		title,
		subtitle,
		content,
		headerContent,
		footerContent,
		actionsContent,
		imageUrl,
		imageAlt,
		complexContent = false,
		...cardProps
	}: Props = $props();
</script>

{#if showCard}
	<Card {...cardProps}>
		{#snippet header()}
			{#if title}
				<h3>{title}</h3>
			{/if}
			{#if subtitle}
				<p>{subtitle}</p>
			{/if}
			{#if headerContent}
				<div>{headerContent}</div>
			{/if}
		{/snippet}

		{#snippet children()}
			{#if imageUrl}
				<img src={imageUrl} alt={imageAlt || ''} />
			{/if}
			{#if content}
				<p>{content}</p>
			{/if}
			{#if complexContent}
				<div class="nested-content">
					<Card>
						<p>Nested card content</p>
					</Card>
				</div>
			{/if}
		{/snippet}

		{#snippet footer()}
			{#if footerContent}
				<div>{footerContent}</div>
			{/if}
		{/snippet}

		{#snippet actions()}
			{#if actionsContent}
				<div>{actionsContent}</div>
			{/if}
		{/snippet}
	</Card>
{/if}