<script lang="ts">
import { onDestroy, tick } from 'svelte';
	import cytoscape from 'cytoscape';
	import type { Core, ElementDefinition, EventObject, NodeSingular, EdgeSingular } from 'cytoscape';
	import { API_HOST } from '$lib/api/client';
	import { faceGraphStore } from '../stores/face-graph.svelte';
	import { goto } from '$app/navigation';
	import type { GraphNode, GraphEdge } from '../types';

	let containerElement = $state<HTMLDivElement | null>(null);
	let cy: Core | null = null;
	let rerenderTimeout: number | null = null;

	// Derived state from store using Svelte 5 runes
	const graph = $derived(faceGraphStore.graph);
	const loading = $derived(faceGraphStore.loading);
	const error = $derived(faceGraphStore.error);
	const filteredPersonId = $derived(faceGraphStore.filteredPersonId);

// Initialise Cytoscape once, after the container has been bound and has real
// dimensions. This avoids the classic timing issue where Cytoscape measures a
// 0x0 container on first load but works after a hot reload.
async function initCytoscape(container: HTMLDivElement): Promise<void> {
		// Avoid double‑init
		if (cy) {
			return;
		}

		// Wait for Svelte to flush DOM updates, then a microtask so the browser
		// has painted and computed layout.
		await tick();
		await Promise.resolve();

	// Debug: track Cytoscape lifecycle and container size
	console.log('FaceGraph init - containerElement:', container);

		const rect = container.getBoundingClientRect();
		console.log('FaceGraph container rect:', rect);
		if (rect.width === 0 || rect.height === 0) {
			console.error('FaceGraph container has zero dimensions, skipping Cytoscape init');
			return;
		}

		console.log('Initializing cytoscape...');

		cy = cytoscape({
			container,
			style: [
					{
						// Base node styling that always applies
						selector: 'node',
						style: {
							'background-color': '#e5e7eb',
							shape: 'ellipse',
							width: 'data(size)',
							height: 'data(size)',
							'border-width': 2,
							'border-color': '#ffffff',
							// Label styling (person name) rendered below the node
							label: 'data(name)',
							'text-valign': 'bottom',
							'text-halign': 'center',
							'text-margin-y': 8,
							color: '#111827',
							'font-size': '12px',
							'font-weight': 600,
							'overlay-opacity': 0
						}
					},
				{
					// Only apply background images to nodes that actually have an imageUrl.
					// This avoids Cytoscape warnings and keeps nodes without faces visible.
					selector: 'node[imageUrl]',
					style: {
						'background-image': 'data(imageUrl)',
						'background-fit': 'cover',
						'background-opacity': 1
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
			// Use preset layout; we provide explicit positions for nodes in
			// updateGraph to avoid Cytoscape's internal layout bugs.
			layout: { name: 'preset' },
			userZoomingEnabled: true,
			userPanningEnabled: true,
			boxSelectionEnabled: false,
			wheelSensitivity: 0.2,
			minZoom: 0.5,
			maxZoom: 3
		});

		// Handle node clicks: toggle between full graph and a specific person's
		// ego network. We drive the data via the faceGraphStore, and update the
		// URL query params for deep-linking without relying on them for logic.
		cy.on('tap', 'node', (event: EventObject) => {
			const node = event.target as NodeSingular;
			const personId = node.data('id') as string;

			if (filteredPersonId === personId) {
				// Clear filter: load full graph again and drop person_id in URL
				void faceGraphStore.clearFilter();
				void goto('/faces?view=graph', { replaceState: true, keepFocus: true });
			} else {
				// Focus on this person's network
				void faceGraphStore.filterByPerson(personId);
				void goto(`/faces?view=graph&person_id=${personId}`, {
					replaceState: true,
					keepFocus: true
				});
			}
		});

		// Handle edge clicks
		cy.on('tap', 'edge', (event: EventObject) => {
			const edge = event.target as EdgeSingular;
			const personAId = edge.data('source') as string;
			const personBId = edge.data('target') as string;

			// Navigate to relationship photos page
			void goto(`/faces/relationships/${personAId}/${personBId}`);
		});

		// Add hover tooltips
		cy.on('mouseover', 'node', (event: EventObject) => {
			const node = event.target as NodeSingular;
			const nameData = node.data('name') as string | null | undefined;
			const name = (nameData !== null && nameData !== undefined && nameData !== '') ? nameData : 'Unknown';
			const faceCountData = node.data('faceCount') as number | null | undefined;
			const faceCount = faceCountData ?? 0;
			node.data('label', `${name}\n${faceCount} faces`);
		});

		cy.on('mouseover', 'edge', (event: EventObject) => {
			const edge = event.target as EdgeSingular;
			const sharedCountData = edge.data('sharedPhotoCount') as number | null | undefined;
			const sharedCount = sharedCountData ?? 0;
			container.title = `${sharedCount} photos together`;
		});

		cy.on('mouseout', 'edge', () => {
			container.title = '';
		});

		// If graph data was already loaded before Cytoscape initialised
		// (e.g. when navigating directly to ?view=graph), make sure we
		// render it immediately.
		if (graph) {
			void updateGraph(graph.nodes, graph.edges, filteredPersonId);
		}
	}

	// When the bound containerElement becomes available, initialise Cytoscape.
	// Because this is a reactive effect, it will re-run if Svelte rebinds
	// the element after navigation, but initCytoscape itself is idempotent.
	$effect(() => {
		if (!cy && containerElement) {
			void initCytoscape(containerElement);
		}
	});

	// Preload face thumbnails so we only use images that load successfully.
	function preloadImage(url: string): Promise<boolean> {
		return new Promise((resolve) => {
			const img = new Image();
			img.crossOrigin = 'anonymous';
			img.onload = () => {
				resolve(true);
			};
			img.onerror = () => {
				resolve(false);
			};
			img.src = url;
		});
	}

	async function updateGraph(
		nodes: GraphNode[],
		edges: GraphEdge[],
		currentFilteredPersonId: string | null
	): Promise<void> {
		console.log('updateGraph called:', { nodes: nodes.length, edges: edges.length, hasCy: !!cy });
		if (!cy) {
			console.warn('Cannot update graph - cy not initialized');
			return;
		}

		// Preload representative face images; only attach image URLs that load
		// successfully so Cytoscape never tries to draw "broken" images.
		const imageAvailability = new Map<string, string>();
		await Promise.all(
			nodes.map(async (node) => {
				if (node.representative_face_id !== null) {
					const url = `${API_HOST}/api/v1/faces/${node.representative_face_id}/crop`;
					const ok = await preloadImage(url);
					if (ok) {
						imageAvailability.set(node.id, url);
					}
				}
			})
		);

		// Convert nodes to Cytoscape format. We compute simple circular
		// positions ourselves and use Cytoscape's "preset" layout so we don't
		// depend on its force-directed algorithms.
		const nodeCount = Math.max(nodes.length, 1);
		const radius = 200;

		const cytoscapeNodes: ElementDefinition[] = nodes.map((node, index) => {
			const faceCount = node.face_count || 0;
			const size = Math.max(40, Math.min(100, faceCount * 2)); // Size based on face count
			const imageUrl = imageAvailability.get(node.id);

			const angle = (2 * Math.PI * index) / nodeCount;
			const x = radius * Math.cos(angle);
			const y = radius * Math.sin(angle);

			return {
				data: {
					id: node.id,
					name: node.name ?? 'Unknown',
					faceCount,
					size,
					imageUrl,
					representativeFaceId: node.representative_face_id
				},
				position: { x, y },
				classes: currentFilteredPersonId === node.id ? 'highlighted' : ''
			};
		});

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

		// Ensure the graph is visible in the viewport. We still rely on our
		// preset positions, but explicitly tell Cytoscape to resize and fit the
		// current elements. Wrap in try/catch so any internal Cytoscape issues
		// don't break the page.
		try {
			cy.resize();
			cy.fit(cy.elements(), 50);
		} catch (err) {
			console.warn('Cytoscape fit/resize error (non-fatal):', err);
		}
	}

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
			// Immediate render with the latest data
			void updateGraph(graph.nodes, graph.edges, filteredPersonId);

			// Force a second render 2 seconds later to catch any late image
			// load/Cytoscape quirks that might have prevented the first draw.
			if (rerenderTimeout !== null) {
				window.clearTimeout(rerenderTimeout);
			}
			rerenderTimeout = window.setTimeout(() => {
				// cy might be null if component was destroyed, but graph is already checked
				if (cy !== null) {
					console.log('Force re-rendering face graph after delay');
					void updateGraph(graph.nodes, graph.edges, filteredPersonId);
				}
			}, 2000);
		}
	});

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
					<button
						onclick={() => {
							void faceGraphStore.clearFilter();
							void goto('/faces?view=graph', { replaceState: true, keepFocus: true });
						}}
						class="clear-filter-button"
					>
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
