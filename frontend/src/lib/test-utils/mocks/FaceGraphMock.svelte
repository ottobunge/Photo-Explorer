<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		graph?: {
			nodes: any[];
			edges: any[];
		};
		width?: number;
		height?: number;
		showControls?: boolean;
		onNodeClick?: (nodeId: string) => void;
		onNodeHover?: (nodeId: string) => void;
		filteredPersonId?: string | null;
		layout?: string;
		loading?: boolean;
		error?: string;
		enableMouseWheel?: boolean;
		responsive?: boolean;
		enableKeyboard?: boolean;
	}

	const {
		graph,
		width = 600,
		height = 400,
		showControls = false,
		onNodeClick,
		onNodeHover,
		filteredPersonId,
		layout = 'cose',
		loading = false,
		error,
		enableMouseWheel = false,
		responsive = false,
		enableKeyboard = false
	}: Props = $props();

	function handleNodeClick(nodeId: string): void {
		onNodeClick?.(nodeId);
	}

	function handleNodeHover(nodeId: string): void {
		onNodeHover?.(nodeId);
	}
</script>

<div
	data-testid="face-graph"
	class="face-graph"
	style="width: {width}px; height: {height}px;"
	role="img"
	aria-label="Face relationship graph with {graph?.nodes.length || 0} nodes and {graph?.edges.length || 0} edges"
>
	{#if loading}
		<div class="loading-spinner">Loading...</div>
	{:else if error}
		<div class="error-message">{error}</div>
	{:else if !graph || graph.nodes.length === 0}
		<div>No relationships to display</div>
	{:else}
		<!-- Mock nodes for testing -->
		{#each graph.nodes as node}
			<div
				class="mock-node"
				data-node-id={node.id}
				onclick={() => { handleNodeClick(node.id); }}
				onmouseover={() => { handleNodeHover(node.id); }}
			>
				{node.label || node.id}
			</div>
		{/each}

		{#if showControls}
			<div class="graph-controls">
				<button aria-label="Zoom in">+</button>
				<button aria-label="Zoom out">-</button>
				<button aria-label="Fit to screen">⟲</button>
			</div>
		{/if}
	{/if}

	<!-- Live region for accessibility -->
	<div aria-live="polite" class="sr-only"></div>
</div>

<style>
	.face-graph {
		position: relative;
		border: 1px solid #ccc;
	}

	.mock-node {
		display: none; /* Hidden but present for testing */
	}

	.graph-controls {
		position: absolute;
		top: 10px;
		right: 10px;
	}

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