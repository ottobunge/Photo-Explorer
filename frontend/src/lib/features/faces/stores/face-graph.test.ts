import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { faceGraphStore } from './face-graph.svelte';
import * as apiClient from '$lib/api/client';
import type { SocialGraph } from '../types';

// Mock the API client
vi.mock('$lib/api/client', () => ({
	client: {
		get: vi.fn()
	},
	ApiError: class ApiError extends Error {
		code: string;
		constructor(message: string, code: string) {
			super(message);
			this.code = code;
		}
	}
}));

describe('faceGraphStore', () => {
	beforeEach(() => {
		// Reset store state before each test
		faceGraphStore.reset();
		vi.clearAllMocks();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	describe('initial state', () => {
		it('should have null graph initially', () => {
			const state = get(faceGraphStore);
			expect(state.graph).toBeNull();
			expect(state.filteredPersonId).toBeNull();
			expect(state.loading).toBe(false);
			expect(state.error).toBeNull();
		});
	});

	describe('loadGraph', () => {
		it('should load graph successfully', async () => {
			const mockGraph: SocialGraph = {
				nodes: [
					{
						id: '1',
						name: 'Alice',
						face_count: 15,
						representative_face_id: 'face-1'
					},
					{
						id: '2',
						name: 'Bob',
						face_count: 10,
						representative_face_id: 'face-2'
					}
				],
				edges: [
					{
						person_a_id: '1',
						person_b_id: '2',
						shared_photo_count: 5,
						sample_photo_ids: ['photo-1', 'photo-2']
					}
				],
				node_count: 2,
				edge_count: 1,
				is_empty: false,
				has_connections: true
			};

			vi.mocked(apiClient.client.get).mockResolvedValueOnce({
				success: true,
				data: mockGraph
			});

			await faceGraphStore.loadGraph();

			const state = get(faceGraphStore);
			expect(state.graph).toEqual(mockGraph);
			expect(state.loading).toBe(false);
			expect(state.error).toBeNull();
			expect(state.filteredPersonId).toBeNull();
		});

		it('should set loading state while fetching', async () => {
			let resolvePromise: (value: any) => void;
			const promise = new Promise((resolve) => {
				resolvePromise = resolve;
			});

			vi.mocked(apiClient.client.get).mockReturnValueOnce(promise as any);

			const loadPromise = faceGraphStore.loadGraph();

			// Check loading state is true
			const loadingState = get(faceGraphStore);
			expect(loadingState.loading).toBe(true);

			// Resolve the promise
			resolvePromise!({
				success: true,
				data: {
					nodes: [],
					edges: [],
					node_count: 0,
					edge_count: 0,
					is_empty: true,
					has_connections: false
				}
			});

			await loadPromise;

			// Check loading state is false after completion
			const finalState = get(faceGraphStore);
			expect(finalState.loading).toBe(false);
		});

		it('should handle API errors', async () => {
			const error = new apiClient.ApiError('Network error', 'NETWORK_ERROR');
			vi.mocked(apiClient.client.get).mockRejectedValueOnce(error);

			await faceGraphStore.loadGraph();

			const state = get(faceGraphStore);
			expect(state.loading).toBe(false);
			expect(state.error).toBe('Network error');
			expect(state.graph).toBeNull();
		});

		it('should handle unknown errors', async () => {
			const error = new Error('Unknown error');
			vi.mocked(apiClient.client.get).mockRejectedValueOnce(error);

			await faceGraphStore.loadGraph();

			const state = get(faceGraphStore);
			expect(state.loading).toBe(false);
			expect(state.error).toBe('Failed to load social graph');
		});

		it('should load filtered graph when person ID provided', async () => {
			const mockGraph: SocialGraph = {
				nodes: [
					{
						id: '1',
						name: 'Alice',
						face_count: 15,
						representative_face_id: 'face-1'
					},
					{
						id: '2',
						name: 'Bob',
						face_count: 10,
						representative_face_id: 'face-2'
					}
				],
				edges: [
					{
						person_a_id: '1',
						person_b_id: '2',
						shared_photo_count: 5,
						sample_photo_ids: ['photo-1']
					}
				],
				node_count: 2,
				edge_count: 1,
				is_empty: false,
				has_connections: true
			};

			vi.mocked(apiClient.client.get).mockResolvedValueOnce({
				success: true,
				data: mockGraph
			});

			await faceGraphStore.loadGraph('1');

			const state = get(faceGraphStore);
			expect(state.graph).toEqual(mockGraph);
			expect(state.filteredPersonId).toBe('1');

			// Verify API was called with correct params
			expect(apiClient.client.get).toHaveBeenCalledWith(
				'/faces/graph',
				{ person_id: '1' }
			);
		});
	});

	describe('filterByPerson', () => {
		it('should load graph filtered by person', async () => {
			const mockGraph: SocialGraph = {
				nodes: [
					{
						id: '1',
						name: 'Alice',
						face_count: 15,
						representative_face_id: 'face-1'
					}
				],
				edges: [],
				node_count: 1,
				edge_count: 0,
				is_empty: false,
				has_connections: false
			};

			vi.mocked(apiClient.client.get).mockResolvedValueOnce({
				success: true,
				data: mockGraph
			});

			await faceGraphStore.filterByPerson('1');

			const state = get(faceGraphStore);
			expect(state.filteredPersonId).toBe('1');
			expect(apiClient.client.get).toHaveBeenCalledWith(
				'/faces/graph',
				{ person_id: '1' }
			);
		});
	});

	describe('clearFilter', () => {
		it('should load unfiltered graph', async () => {
			// First load a filtered graph
			vi.mocked(apiClient.client.get).mockResolvedValueOnce({
				success: true,
				data: {
					nodes: [],
					edges: [],
					node_count: 0,
					edge_count: 0,
					is_empty: true,
					has_connections: false
				}
			});

			await faceGraphStore.filterByPerson('1');

			// Then clear the filter
			vi.mocked(apiClient.client.get).mockResolvedValueOnce({
				success: true,
				data: {
					nodes: [],
					edges: [],
					node_count: 0,
					edge_count: 0,
					is_empty: true,
					has_connections: false
				}
			});

			await faceGraphStore.clearFilter();

			const state = get(faceGraphStore);
			expect(state.filteredPersonId).toBeNull();
			expect(apiClient.client.get).toHaveBeenLastCalledWith(
				'/faces/graph',
				{}
			);
		});
	});

	describe('reset', () => {
		it('should reset store to initial state', async () => {
			// Load some data first
			vi.mocked(apiClient.client.get).mockResolvedValueOnce({
				success: true,
				data: {
					nodes: [{ id: '1', name: 'Alice', face_count: 15, representative_face_id: 'face-1' }],
					edges: [],
					node_count: 1,
					edge_count: 0,
					is_empty: false,
					has_connections: false
				}
			});

			await faceGraphStore.loadGraph();

			// Verify data is loaded
			let state = get(faceGraphStore);
			expect(state.graph).not.toBeNull();

			// Reset the store
			faceGraphStore.reset();

			// Verify reset to initial state
			state = get(faceGraphStore);
			expect(state.graph).toBeNull();
			expect(state.filteredPersonId).toBeNull();
			expect(state.loading).toBe(false);
			expect(state.error).toBeNull();
		});
	});

	describe('empty graph handling', () => {
		it('should handle empty graph correctly', async () => {
			const emptyGraph: SocialGraph = {
				nodes: [],
				edges: [],
				node_count: 0,
				edge_count: 0,
				is_empty: true,
				has_connections: false
			};

			vi.mocked(apiClient.client.get).mockResolvedValueOnce({
				success: true,
				data: emptyGraph
			});

			await faceGraphStore.loadGraph();

			const state = get(faceGraphStore);
			expect(state.graph).toEqual(emptyGraph);
			expect(state.graph?.isEmpty).toBe(true);
			expect(state.graph?.hasConnections).toBe(false);
		});
	});

	describe('graph with isolated nodes', () => {
		it('should handle graph with nodes but no edges', async () => {
			const graphWithIsolatedNodes: SocialGraph = {
				nodes: [
					{ id: '1', name: 'Alice', face_count: 5, representative_face_id: 'face-1' },
					{ id: '2', name: 'Bob', face_count: 3, representative_face_id: 'face-2' }
				],
				edges: [],
				node_count: 2,
				edge_count: 0,
				is_empty: false,
				has_connections: false
			};

			vi.mocked(apiClient.client.get).mockResolvedValueOnce({
				success: true,
				data: graphWithIsolatedNodes
			});

			await faceGraphStore.loadGraph();

			const state = get(faceGraphStore);
			expect(state.graph?.isEmpty).toBe(false);
			expect(state.graph?.hasConnections).toBe(false);
			expect(state.graph?.nodeCount).toBe(2);
			expect(state.graph?.edgeCount).toBe(0);
		});
	});
});
