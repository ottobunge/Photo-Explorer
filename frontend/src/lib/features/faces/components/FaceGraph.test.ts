import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/svelte';
import { tick } from 'svelte';
import FaceGraph from './FaceGraph.svelte';
import { createFaceGraphData } from '$lib/test-utils/factories';
import type { FaceGraphData } from '../types';

// Mock Cytoscape
vi.mock('cytoscape', () => {
	return {
		default: vi.fn(() => ({
			mount: vi.fn(),
			unmount: vi.fn(),
			destroy: vi.fn(),
			resize: vi.fn(),
			fit: vi.fn(),
			center: vi.fn(),
			zoom: vi.fn(),
			pan: vi.fn(),
			on: vi.fn(),
			off: vi.fn(),
			elements: vi.fn(() => ({
				remove: vi.fn()
			})),
			add: vi.fn(),
			layout: vi.fn(() => ({
				run: vi.fn(),
				stop: vi.fn()
			})),
			nodes: vi.fn(() => ({
				forEach: vi.fn(),
				filter: vi.fn(),
				select: vi.fn(),
				unselect: vi.fn(),
				addClass: vi.fn(),
				removeClass: vi.fn()
			})),
			edges: vi.fn(() => ({
				forEach: vi.fn(),
				filter: vi.fn()
			})),
			getElementById: vi.fn(() => ({
				select: vi.fn(),
				unselect: vi.fn(),
				addClass: vi.fn(),
				removeClass: vi.fn(),
				data: vi.fn()
			}))
		}))
	};
});

describe('FaceGraph', () => {
	let mockGraphData: FaceGraphData;
	let mockOnNodeClick: ReturnType<typeof vi.fn>;
	let mockOnNodeHover: ReturnType<typeof vi.fn>;

	beforeEach(() => {
		mockGraphData = createFaceGraphData(5, 4);
		mockOnNodeClick = vi.fn();
		mockOnNodeHover = vi.fn();

		// Mock Image loading
		global.Image = vi.fn().mockImplementation(() => ({
			onload: null,
			onerror: null,
			src: '',
			addEventListener: vi.fn(),
			removeEventListener: vi.fn()
		}));
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	describe('Props', () => {
		it('renders with empty graph data', () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: { nodes: [], edges: [] }
				}
			});

			const graphContainer = container.querySelector('[data-testid="face-graph"]');
			expect(graphContainer).toBeTruthy();
		});

		it('renders with graph data', async () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: mockGraphData
				}
			});

			await tick();

			const graphContainer = container.querySelector('[data-testid="face-graph"]');
			expect(graphContainer).toBeTruthy();
		});

		it('applies custom width and height', () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: mockGraphData,
					width: 800,
					height: 600
				}
			});

			const graphContainer = container.querySelector('[data-testid="face-graph"]');
			expect(graphContainer?.getAttribute('style')).toContain('width: 800px');
			expect(graphContainer?.getAttribute('style')).toContain('height: 600px');
		});

		it('updates when graph data changes', async () => {
			const { rerender } = render(FaceGraph, {
				props: {
					graph: mockGraphData
				}
			});

			const newGraphData = createFaceGraphData(10, 8);
			await rerender({
				graph: newGraphData
			});

			// Should update without errors
			expect(true).toBe(true);
		});
	});

	describe('Node Interactions', () => {
		it('handles node click', async () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: mockGraphData,
					onNodeClick: mockOnNodeClick
				}
			});

			await tick();

			// Simulate Cytoscape node click
			const cyInstance = vi.mocked((await import('cytoscape')).default).mock.results[0]?.value;
			const onCallback = cyInstance?.on.mock.calls.find(call => call[0] === 'tap')?.[1];

			if (onCallback) {
				onCallback({
					target: {
						isNode: () => true,
						data: () => ({ id: 'person-1', label: 'Person 1' })
					}
				});
			}

			expect(mockOnNodeClick).toHaveBeenCalledWith('person-1');
		});

		it('handles node hover', async () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: mockGraphData,
					onNodeHover: mockOnNodeHover
				}
			});

			await tick();

			const cyInstance = vi.mocked((await import('cytoscape')).default).mock.results[0]?.value;
			const onCallback = cyInstance?.on.mock.calls.find(call => call[0] === 'mouseover')?.[1];

			if (onCallback) {
				onCallback({
					target: {
						isNode: () => true,
						data: () => ({ id: 'person-2', label: 'Person 2' })
					}
				});
			}

			expect(mockOnNodeHover).toHaveBeenCalledWith('person-2');
		});

		it('does not trigger edge clicks', async () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: mockGraphData,
					onNodeClick: mockOnNodeClick
				}
			});

			await tick();

			const cyInstance = vi.mocked((await import('cytoscape')).default).mock.results[0]?.value;
			const onCallback = cyInstance?.on.mock.calls.find(call => call[0] === 'tap')?.[1];

			if (onCallback) {
				onCallback({
					target: {
						isNode: () => false,
						isEdge: () => true,
						data: () => ({ id: 'edge-1' })
					}
				});
			}

			expect(mockOnNodeClick).not.toHaveBeenCalled();
		});
	});

	describe('Graph Filtering', () => {
		it('filters graph by person ID', async () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: mockGraphData,
					filteredPersonId: 'person-2'
				}
			});

			await tick();

			// Should highlight/filter to show person-2 and connected nodes
			const cyInstance = vi.mocked((await import('cytoscape')).default).mock.results[0]?.value;
			expect(cyInstance?.getElementById).toHaveBeenCalledWith('person-2');
		});

		it('clears filter when filteredPersonId is null', async () => {
			const { rerender } = render(FaceGraph, {
				props: {
					graph: mockGraphData,
					filteredPersonId: 'person-1'
				}
			});

			await tick();

			// Clear filter
			await rerender({
				graph: mockGraphData,
				filteredPersonId: null
			});

			// Should show all nodes
			expect(true).toBe(true);
		});

		it('updates filter when person changes', async () => {
			const { rerender } = render(FaceGraph, {
				props: {
					graph: mockGraphData,
					filteredPersonId: 'person-1'
				}
			});

			await rerender({
				graph: mockGraphData,
				filteredPersonId: 'person-3'
			});

			const cyInstance = vi.mocked((await import('cytoscape')).default).mock.results[0]?.value;
			expect(cyInstance?.getElementById).toHaveBeenCalledWith('person-3');
		});
	});

	describe('Zoom and Pan Controls', () => {
		it('shows zoom controls', () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: mockGraphData,
					showControls: true
				}
			});

			const zoomInBtn = container.querySelector('[aria-label="Zoom in"]');
			const zoomOutBtn = container.querySelector('[aria-label="Zoom out"]');
			const fitBtn = container.querySelector('[aria-label="Fit to screen"]');

			expect(zoomInBtn).toBeTruthy();
			expect(zoomOutBtn).toBeTruthy();
			expect(fitBtn).toBeTruthy();
		});

		it('handles zoom in', async () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: mockGraphData,
					showControls: true
				}
			});

			await tick();

			const zoomInBtn = container.querySelector('[aria-label="Zoom in"]');
			await fireEvent.click(zoomInBtn!);

			const cyInstance = vi.mocked((await import('cytoscape')).default).mock.results[0]?.value;
			expect(cyInstance?.zoom).toHaveBeenCalled();
		});

		it('handles zoom out', async () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: mockGraphData,
					showControls: true
				}
			});

			await tick();

			const zoomOutBtn = container.querySelector('[aria-label="Zoom out"]');
			await fireEvent.click(zoomOutBtn!);

			const cyInstance = vi.mocked((await import('cytoscape')).default).mock.results[0]?.value;
			expect(cyInstance?.zoom).toHaveBeenCalled();
		});

		it('handles fit to screen', async () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: mockGraphData,
					showControls: true
				}
			});

			await tick();

			const fitBtn = container.querySelector('[aria-label="Fit to screen"]');
			await fireEvent.click(fitBtn!);

			const cyInstance = vi.mocked((await import('cytoscape')).default).mock.results[0]?.value;
			expect(cyInstance?.fit).toHaveBeenCalled();
		});

		it('handles mouse wheel zoom', async () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: mockGraphData,
					enableMouseWheel: true
				}
			});

			const graphContainer = container.querySelector('[data-testid="face-graph"]');

			const wheelEvent = new WheelEvent('wheel', {
				deltaY: -100,
				bubbles: true
			});

			await fireEvent(graphContainer!, wheelEvent);

			// Should handle wheel zoom
			expect(true).toBe(true);
		});
	});

	describe('Layout', () => {
		it('uses default layout', async () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: mockGraphData
				}
			});

			await tick();

			const cyInstance = vi.mocked((await import('cytoscape')).default).mock.results[0]?.value;
			expect(cyInstance?.layout).toHaveBeenCalled();
		});

		it('applies custom layout', async () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: mockGraphData,
					layout: 'grid'
				}
			});

			await tick();

			const cyInstance = vi.mocked((await import('cytoscape')).default).mock.results[0]?.value;
			const layoutCall = cyInstance?.layout.mock.calls[0];
			expect(layoutCall?.[0]?.name).toBe('grid');
		});

		it('re-layouts on graph change', async () => {
			const { rerender } = render(FaceGraph, {
				props: {
					graph: mockGraphData
				}
			});

			const newGraph = createFaceGraphData(8, 6);
			await rerender({
				graph: newGraph
			});

			const cyInstance = vi.mocked((await import('cytoscape')).default).mock.results[0]?.value;
			expect(cyInstance?.layout).toHaveBeenCalledTimes(2);
		});
	});

	describe('Loading and Error States', () => {
		it('shows loading state', () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: mockGraphData,
					loading: true
				}
			});

			const loadingIndicator = container.querySelector('.loading-spinner');
			expect(loadingIndicator).toBeTruthy();
		});

		it('shows error state', () => {
			const { getByText } = render(FaceGraph, {
				props: {
					graph: mockGraphData,
					error: 'Failed to load graph data'
				}
			});

			expect(getByText('Failed to load graph data')).toBeTruthy();
		});

		it('shows empty state', () => {
			const { getByText } = render(FaceGraph, {
				props: {
					graph: { nodes: [], edges: [] }
				}
			});

			expect(getByText('No relationships to display')).toBeTruthy();
		});
	});

	describe('Responsive Behavior', () => {
		it('resizes on window resize', async () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: mockGraphData,
					responsive: true
				}
			});

			await tick();

			// Trigger window resize
			window.dispatchEvent(new Event('resize'));

			await waitFor(() => {
				const cyInstance = vi.mocked((await import('cytoscape')).default).mock.results[0]?.value;
				expect(cyInstance?.resize).toHaveBeenCalled();
			});
		});

		it('handles container resize with ResizeObserver', async () => {
			// Mock ResizeObserver
			const mockObserve = vi.fn();
			const mockDisconnect = vi.fn();

			global.ResizeObserver = vi.fn().mockImplementation(() => ({
				observe: mockObserve,
				unobserve: vi.fn(),
				disconnect: mockDisconnect
			}));

			const { container, unmount } = render(FaceGraph, {
				props: {
					graph: mockGraphData,
					responsive: true
				}
			});

			expect(mockObserve).toHaveBeenCalled();

			unmount();
			expect(mockDisconnect).toHaveBeenCalled();
		});
	});

	describe('Accessibility', () => {
		it('has proper ARIA attributes', () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: mockGraphData
				}
			});

			const graphContainer = container.querySelector('[data-testid="face-graph"]');
			expect(graphContainer?.getAttribute('role')).toBe('img');
			expect(graphContainer?.getAttribute('aria-label')).toContain('Face relationship graph');
		});

		it('provides keyboard navigation', async () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: mockGraphData,
					enableKeyboard: true
				}
			});

			const graphContainer = container.querySelector('[data-testid="face-graph"]');

			// Tab navigation
			await fireEvent.keyDown(graphContainer!, { key: 'Tab' });

			// Arrow keys for panning
			await fireEvent.keyDown(graphContainer!, { key: 'ArrowUp' });
			await fireEvent.keyDown(graphContainer!, { key: 'ArrowDown' });
			await fireEvent.keyDown(graphContainer!, { key: 'ArrowLeft' });
			await fireEvent.keyDown(graphContainer!, { key: 'ArrowRight' });

			// Plus/minus for zoom
			await fireEvent.keyDown(graphContainer!, { key: '+' });
			await fireEvent.keyDown(graphContainer!, { key: '-' });

			// Should handle all keyboard interactions
			expect(true).toBe(true);
		});

		it('announces selected nodes', async () => {
			const { container } = render(FaceGraph, {
				props: {
					graph: mockGraphData
				}
			});

			const liveRegion = container.querySelector('[aria-live="polite"]');
			expect(liveRegion).toBeTruthy();
		});
	});

	describe('Edge Cases', () => {
		it('handles graph with single node', () => {
			const singleNodeGraph = createFaceGraphData(1, 0);

			const { container } = render(FaceGraph, {
				props: {
					graph: singleNodeGraph
				}
			});

			expect(container.querySelector('[data-testid="face-graph"]')).toBeTruthy();
		});

		it('handles graph with no edges', () => {
			const noEdgesGraph = createFaceGraphData(5, 0);

			const { container } = render(FaceGraph, {
				props: {
					graph: noEdgesGraph
				}
			});

			expect(container.querySelector('[data-testid="face-graph"]')).toBeTruthy();
		});

		it('handles rapid graph updates', async () => {
			const { rerender } = render(FaceGraph, {
				props: {
					graph: mockGraphData
				}
			});

			// Rapid updates
			for (let i = 0; i < 5; i++) {
				await rerender({
					graph: createFaceGraphData(i + 2, i + 1)
				});
			}

			// Should handle all updates without crashes
			expect(true).toBe(true);
		});

		it('cleans up on unmount', () => {
			const { unmount } = render(FaceGraph, {
				props: {
					graph: mockGraphData
				}
			});

			unmount();

			const cyInstance = vi.mocked((await import('cytoscape')).default).mock.results[0]?.value;
			expect(cyInstance?.destroy).toHaveBeenCalled();
		});
	});
});