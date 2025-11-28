<script lang="ts">
	import { onDestroy } from 'svelte';
	import cytoscape from 'cytoscape';
	import type { Core, ElementDefinition } from 'cytoscape';
	import { faceGraphStore } from '../stores/face-graph.svelte';
	import { goto } from '$app/navigation';
	import type { GraphNode, GraphEdge } from '../types';

	let containerElement = $state<HTMLDivElement | null>(null);
	let cy: Core | null = null;

	// Derived state from store using Svelte 5 runes
	const graph = $derived(faceGraphStore.graph);
	const loading = $derived(faceGraphStore.loading);
	const error = $derived(faceGraphStore.error);
	const filteredPersonId = $derived(faceGraphStore.filteredPersonId);

	// Initialize Cytoscape when container becomes available
	$effect(() => {
		console.log('FaceGraph effect - containerElement:', containerElement, 'cy:', cy);
		if (containerElement && !cy) {
			console.log('Initializing cytoscape...');
			// Capture container reference for event handlers
			const container = containerElement;
			cy = cytoscape({
				container: containerElement,
				style: [
					{
						selector: 'node',
						style: {
							'background-color': '#4f46e5',
							label: 'data(name)',
							'text-valign': 'center',
							'text-halign': 'center',
							color: '#1f2937',
							'font-size': '12px',
							'font-weight': 'bold',
							width: 'data(size)',
							height: 'data(size)',
							'border-width': 2,
							'border-color': '#fff',
							'overlay-opacity': 0
						}
					},
					{
						selector: 'node:active',
						style: {
							'background-color': '#818cf8',
							'border-color': '#4f46e5',
							'border-width': 3
						}
					},
					{
						selector: 'node.highlighted',
						style: {
							'background-color': '#10b981',
							'border-color': '#059669',
							'border-width': 3
						}
					},
					{
						selector: 'edge',
						style: {
							width: 'data(thickness)',
							'line-color': '#d1d5db',
							'curve-style': 'bezier',
							'target-arrow-shape': 'none',
							opacity: 0.6
						}
					},
					{
						selector: 'edge:active',
						style: {
							'line-color': '#4f46e5',
							opacity: 1,
							width: 4
						}
					}
				],
				layout: {
					name: 'cose',
					animate: true,
					animationDuration: 500,
					nodeRepulsion: 8000,
					idealEdgeLength: 100,
					edgeElasticity: 100,
					nestingFactor: 1.2,
					gravity: 1,
					numIter: 1000,
					initialTemp: 200,
					coolingFactor: 0.95,
					minTemp: 1.0
				},
				userZoomingEnabled: true,
				userPanningEnabled: true,
				boxSelectionEnabled: false,
				wheelSensitivity: 0.2,
				minZoom: 0.5,
				maxZoom: 3
			});

			// Handle node clicks
			cy.on('tap', 'node', (event) => {
				const node = event.target;
				const personId = node.data('id');

				// If already filtered by this person, clear filter
				if (filteredPersonId === personId) {
					faceGraphStore.clearFilter();
				} else {
					// Filter to this person's network
					faceGraphStore.filterByPerson(personId);
				}
			});

			// Handle edge clicks
			cy.on('tap', 'edge', (event) => {
				const edge = event.target;
				const personAId = edge.data('source');
				const personBId = edge.data('target');

				// Navigate to relationship photos page
				goto(`/faces/relationships/${personAId}/${personBId}`);
			});

			// Add hover tooltips
			cy.on('mouseover', 'node', (event) => {
				const node = event.target;
				const nameData: unknown = node.data('name');
				const name = (nameData !== null && nameData !== '') ? String(nameData) : 'Unknown';
				const faceCountData: unknown = node.data('faceCount');
				const faceCount = (faceCountData !== null) ? Number(faceCountData) : 0;
				node.data('label', `${name}\n${faceCount} faces`);
			});

			cy.on('mouseover', 'edge', (event) => {
				const edge = event.target;
				const sharedCountData: unknown = edge.data('sharedPhotoCount');
				const sharedCount = (sharedCountData !== null) ? Number(sharedCountData) : 0;
				container.title = `${sharedCount} photos together`;
			});

			cy.on('mouseout', 'edge', () => {
				container.title = '';
			});
		}
	});

	// Update graph when data changes using Svelte 5 $effect
	$effect(() => {
		console.log('Graph data changed:', {
			hasCy: !!cy,
			hasGraph: !!graph,
			isEmpty: graph?.is_empty,
			hasConnections: graph?.has_connections,
			nodeCount: graph?.node_count,
			edgeCount: graph?.edge_count,
			nodesLength: graph?.nodes.length,
			edgesLength: graph?.edges.length
		});
		if (cy && graph) {
			updateGraph(graph.nodes, graph.edges, filteredPersonId);
		}
	});

	function updateGraph(nodes: GraphNode[], edges: GraphEdge[], currentFilteredPersonId: string | null): void {
		console.log('updateGraph called:', { nodes: nodes.length, edges: edges.length, hasCy: !!cy });
		if (!cy) {
			console.warn('Cannot update graph - cy not initialized');
			return;
		}

		// Convert nodes to Cytoscape format
		const cytoscapeNodes: ElementDefinition[] = nodes.map((node) => ({
			data: {
				id: node.id,
				name: node.name ?? 'Unknown',
				faceCount: node.face_count || 0,
				size: Math.max(30, Math.min(80, (node.face_count || 0) * 2)), // Size based on face count
				representativeFaceId: node.representative_face_id
			},
			classes: currentFilteredPersonId === node.id ? 'highlighted' : ''
		}));

		// Convert edges to Cytoscape format
		const cytoscapeEdges: ElementDefinition[] = edges.map((edge) => ({
			data: {
				id: `${edge.person_a_id}-${edge.person_b_id}`,
				source: edge.person_a_id,
				target: edge.person_b_id,
				sharedPhotoCount: edge.shared_photo_count || 0,
				thickness: Math.max(1, Math.min(8, (edge.shared_photo_count || 0) / 2)), // Thickness based on shared photos
				samplePhotoIds: edge.sample_photo_ids
			}
		}));

		// Update the graph
		cy.elements().remove();
		cy.add([...cytoscapeNodes, ...cytoscapeEdges]);

		// Run layout
		const layout = cy.layout({
			name: 'cose',
			animate: true,
			animationDuration: 500,
			nodeRepulsion: 8000,
			idealEdgeLength: 100,
			edgeElasticity: 100,
			nestingFactor: 1.2,
			gravity: 1,
			numIter: 1000,
			initialTemp: 200,
			coolingFactor: 0.95,
			minTemp: 1.0
		});

		layout.run();

		// Fit to viewport after layout completes
		setTimeout(() => {
			cy?.fit(undefined, 50);
		}, 600);
	}

	function handleZoomIn(): void {
		if (cy) {
			cy.zoom(cy.zoom() * 1.2);
			cy.center();
		}
	}

	function handleZoomOut(): void {
		if (cy) {
			cy.zoom(cy.zoom() * 0.8);
			cy.center();
		}
	}

	function handleReset(): void {
		if (cy) {
			cy.fit(undefined, 50);
		}
	}

	onDestroy(() => {
		if (cy) {
			cy.destroy();
		}
	});
</script>

<div class="face-graph-container" data-testid="face-graph">
	{#if loading}
		<div class="loading-state">
			<div class="spinner"></div>
			<p>Loading social graph...</p>
		</div>
	{:else if error}
		<div class="error-state">
			<p class="error-message">{error}</p>
			<button onclick={() => faceGraphStore.loadGraph()} class="retry-button"> Retry </button>
		</div>
	{:else if graph?.is_empty}
		<div class="empty-state">
			<p>No people found in your photo collection yet.</p>
			<p class="hint">Upload photos with faces to see the social graph.</p>
		</div>
	{:else if graph && !graph.has_connections}
		<div class="no-connections-state">
			<p>No relationships found.</p>
			<p class="hint">People appear in photos alone, with no co-appearances yet.</p>
		</div>
	{:else}
		<div class="graph-wrapper">
			{#if filteredPersonId}
				<div class="filter-banner">
					<span>Showing network for selected person</span>
					<button onclick={() => faceGraphStore.clearFilter()} class="clear-filter-button">
						Show All
					</button>
				</div>
			{/if}

			<div class="graph-controls" data-testid="graph-controls">
				<button onclick={handleZoomIn} class="control-button" title="Zoom In"> + </button>
				<button onclick={handleZoomOut} class="control-button" title="Zoom Out"> − </button>
				<button onclick={handleReset} class="control-button" title="Reset View"> ⟲ </button>
			</div>

			<div bind:this={containerElement} class="cytoscape-container"></div>

			{#if graph}
				<div class="graph-stats">
					<span>{graph.node_count} {graph.node_count === 1 ? 'person' : 'people'}</span>
					<span>•</span>
					<span>
						{graph.edge_count} {graph.edge_count === 1 ? 'relationship' : 'relationships'}
					</span>
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.face-graph-container {
		width: 100%;
		height: 600px;
		position: relative;
		background: #f9fafb;
		border-radius: 8px;
		overflow: hidden;
	}

	.graph-wrapper {
		width: 100%;
		height: 100%;
		position: relative;
	}

	.cytoscape-container {
		width: 100%;
		height: 100%;
	}

	.loading-state,
	.error-state,
	.empty-state,
	.no-connections-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		padding: 2rem;
		text-align: center;
	}

	.spinner {
		width: 40px;
		height: 40px;
		border: 3px solid #e5e7eb;
		border-top-color: #4f46e5;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
		margin-bottom: 1rem;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.error-message {
		color: #dc2626;
		margin-bottom: 1rem;
	}

	.retry-button,
	.control-button,
	.clear-filter-button {
		padding: 0.5rem 1rem;
		background: #4f46e5;
		color: white;
		border: none;
		border-radius: 6px;
		cursor: pointer;
		font-weight: 500;
		transition: background 0.2s;
	}

	.retry-button:hover,
	.control-button:hover,
	.clear-filter-button:hover {
		background: #4338ca;
	}

	.hint {
		color: #6b7280;
		font-size: 0.875rem;
		margin-top: 0.5rem;
	}

	.filter-banner {
		position: absolute;
		top: 1rem;
		left: 50%;
		transform: translateX(-50%);
		z-index: 10;
		background: #eef2ff;
		padding: 0.75rem 1.5rem;
		border-radius: 9999px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.filter-banner span {
		color: #4f46e5;
		font-weight: 500;
		font-size: 0.875rem;
	}

	.clear-filter-button {
		padding: 0.25rem 0.75rem;
		font-size: 0.75rem;
	}

	.graph-controls {
		position: absolute;
		top: 1rem;
		right: 1rem;
		z-index: 10;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.control-button {
		width: 40px;
		height: 40px;
		padding: 0;
		font-size: 1.25rem;
		line-height: 1;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.graph-stats {
		position: absolute;
		bottom: 1rem;
		left: 50%;
		transform: translateX(-50%);
		z-index: 10;
		background: white;
		padding: 0.5rem 1rem;
		border-radius: 9999px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		color: #6b7280;
	}
</style>
