import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import ClusterPicker from './ClusterPicker.svelte';
import { facesStore } from '../stores/faces.svelte';
import type { FaceClusterType } from '../types';

// Mock the facesStore
vi.mock('../stores/faces.svelte', () => ({
	facesStore: {
		load: vi.fn(),
		subscribe: vi.fn((callback) => {
			callback({
				clusters: [],
				loading: false,
				error: null
			});
			return () => {};
		})
	}
}));

describe('ClusterPicker', () => {
	const mockClusters: FaceClusterType[] = [
		{
			id: 'cluster-1',
			name: 'Alice',
			faceCount: 15,
			photoCount: 12,
			representativeFace: {
				id: 'face-1',
				cropUrl: '/api/v1/faces/crops/face-1.jpg'
			}
		},
		{
			id: 'cluster-2',
			name: 'Bob',
			faceCount: 8,
			photoCount: 7,
			representativeFace: {
				id: 'face-2',
				cropUrl: '/api/v1/faces/crops/face-2.jpg'
			}
		},
		{
			id: 'cluster-3',
			name: 'Charlie',
			faceCount: 20,
			photoCount: 18,
			representativeFace: {
				id: 'face-3',
				cropUrl: '/api/v1/faces/crops/face-3.jpg'
			}
		},
		{
			id: 'cluster-4',
			name: undefined,
			faceCount: 5,
			photoCount: 4,
			representativeFace: {
				id: 'face-4',
				cropUrl: '/api/v1/faces/crops/face-4.jpg'
			}
		}
	];

	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('should render with default title', () => {
		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		expect(screen.getByText('Select a Person')).toBeInTheDocument();
	});

	it('should render with custom title', () => {
		render(ClusterPicker, {
			props: {
				title: 'Move Faces To...',
				excludeClusterIds: []
			}
		});

		expect(screen.getByText('Move Faces To...')).toBeInTheDocument();
	});

	it('should show loading state initially', () => {
		vi.mocked(facesStore.subscribe).mockImplementation((callback) => {
			callback({
				clusters: [],
				loading: true,
				error: null
			});
			return () => {};
		});

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		expect(screen.getByText('Loading clusters...')).toBeInTheDocument();
	});

	it('should show error state', () => {
		vi.mocked(facesStore.subscribe).mockImplementation((callback) => {
			callback({
				clusters: [],
				loading: false,
				error: 'Failed to load clusters'
			});
			return () => {};
		});

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		expect(screen.getByText('Failed to load clusters')).toBeInTheDocument();
	});

	it('should show no clusters message when list is empty', () => {
		vi.mocked(facesStore.subscribe).mockImplementation((callback) => {
			callback({
				clusters: [],
				loading: false,
				error: null
			});
			return () => {};
		});

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		expect(screen.getByText('No clusters available')).toBeInTheDocument();
	});

	it('should render cluster list', () => {
		vi.mocked(facesStore.subscribe).mockImplementation((callback) => {
			callback({
				clusters: mockClusters,
				loading: false,
				error: null
			});
			return () => {};
		});

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		expect(screen.getByText('Alice')).toBeInTheDocument();
		expect(screen.getByText('Bob')).toBeInTheDocument();
		expect(screen.getByText('Charlie')).toBeInTheDocument();
		expect(screen.getByText('Unknown')).toBeInTheDocument();
	});

	it('should show face and photo counts', () => {
		vi.mocked(facesStore.subscribe).mockImplementation((callback) => {
			callback({
				clusters: [mockClusters[0]!],
				loading: false,
				error: null
			});
			return () => {};
		});

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		expect(screen.getByText(/15 faces/)).toBeInTheDocument();
		expect(screen.getByText(/12 photos/)).toBeInTheDocument();
	});

	it('should exclude clusters by ID', () => {
		vi.mocked(facesStore.subscribe).mockImplementation((callback) => {
			callback({
				clusters: mockClusters,
				loading: false,
				error: null
			});
			return () => {};
		});

		render(ClusterPicker, {
			props: {
				excludeClusterIds: ['cluster-1', 'cluster-2']
			}
		});

		expect(screen.queryByText('Alice')).not.toBeInTheDocument();
		expect(screen.queryByText('Bob')).not.toBeInTheDocument();
		expect(screen.getByText('Charlie')).toBeInTheDocument();
	});

	it('should filter clusters by search query', async () => {
		vi.mocked(facesStore.subscribe).mockImplementation((callback) => {
			callback({
				clusters: mockClusters,
				loading: false,
				error: null
			});
			return () => {};
		});

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		const searchInput = screen.getByPlaceholderText('Search by name...');
		await fireEvent.input(searchInput, { target: { value: 'alice' } });

		expect(screen.getByText('Alice')).toBeInTheDocument();
		expect(screen.queryByText('Bob')).not.toBeInTheDocument();
		expect(screen.queryByText('Charlie')).not.toBeInTheDocument();
	});

	it('should show no results message when search has no matches', async () => {
		vi.mocked(facesStore.subscribe).mockImplementation((callback) => {
			callback({
				clusters: mockClusters,
				loading: false,
				error: null
			});
			return () => {};
		});

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		const searchInput = screen.getByPlaceholderText('Search by name...');
		await fireEvent.input(searchInput, { target: { value: 'nonexistent' } });

		expect(screen.getByText('No clusters match your search')).toBeInTheDocument();
	});

	it('should sort clusters: named first, then by name alphabetically', () => {
		vi.mocked(facesStore.subscribe).mockImplementation((callback) => {
			callback({
				clusters: [mockClusters[3]!, mockClusters[2]!, mockClusters[0]!, mockClusters[1]!],
				loading: false,
				error: null
			});
			return () => {};
		});

		const { container } = render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		const clusterButtons = container.querySelectorAll('button[type="button"]');
		// Filter out the cancel button (last button)
		const clusterListButtons = Array.from(clusterButtons).slice(0, -1);

		// Named clusters should appear first, alphabetically: Alice, Bob, Charlie, Unknown
		const textContent = clusterListButtons.map((btn) => btn.textContent);

		expect(textContent[0]).toContain('Alice');
		expect(textContent[1]).toContain('Bob');
		expect(textContent[2]).toContain('Charlie');
		expect(textContent[3]).toContain('Unknown');
	});

	it('should dispatch close event when backdrop is clicked', async () => {
		vi.mocked(facesStore.subscribe).mockImplementation((callback) => {
			callback({
				clusters: mockClusters,
				loading: false,
				error: null
			});
			return () => {};
		});

		const { component } = render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		const closeMock = vi.fn();
		component.$on('close', closeMock);

		const backdrop = screen.getByRole('dialog').parentElement!;
		await fireEvent.click(backdrop);

		expect(closeMock).toHaveBeenCalled();
	});

	it('should dispatch close event when Cancel button is clicked', async () => {
		vi.mocked(facesStore.subscribe).mockImplementation((callback) => {
			callback({
				clusters: mockClusters,
				loading: false,
				error: null
			});
			return () => {};
		});

		const { component } = render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		const closeMock = vi.fn();
		component.$on('close', closeMock);

		const cancelButton = screen.getByText('Cancel');
		await fireEvent.click(cancelButton);

		expect(closeMock).toHaveBeenCalled();
	});

	it('should dispatch close event when X button is clicked', async () => {
		vi.mocked(facesStore.subscribe).mockImplementation((callback) => {
			callback({
				clusters: mockClusters,
				loading: false,
				error: null
			});
			return () => {};
		});

		const { component } = render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		const closeMock = vi.fn();
		component.$on('close', closeMock);

		const closeButton = screen.getByLabelText('Close modal');
		await fireEvent.click(closeButton);

		expect(closeMock).toHaveBeenCalled();
	});

	it('should dispatch select event when cluster is clicked', async () => {
		vi.mocked(facesStore.subscribe).mockImplementation((callback) => {
			callback({
				clusters: mockClusters,
				loading: false,
				error: null
			});
			return () => {};
		});

		const { component } = render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		const selectMock = vi.fn();
		component.$on('select', selectMock);

		const aliceButton = screen.getByText('Alice').closest('button')!;
		await fireEvent.click(aliceButton);

		expect(selectMock).toHaveBeenCalledTimes(1);
		expect(selectMock.mock.calls[0]![0].detail.cluster.id).toBe('cluster-1');
		expect(selectMock.mock.calls[0]![0].detail.cluster.name).toBe('Alice');
	});

	it('should show representative face image when available', () => {
		vi.mocked(facesStore.subscribe).mockImplementation((callback) => {
			callback({
				clusters: [mockClusters[0]!],
				loading: false,
				error: null
			});
			return () => {};
		});

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		const img = screen.getByAlt('Alice');
		expect(img).toBeInTheDocument();
		expect(img).toHaveAttribute('src', 'http://localhost:8000/api/v1/faces/crops/face-1.jpg');
	});

	it('should show placeholder when no representative face', () => {
		const clusterWithoutFace: FaceClusterType = {
			id: 'cluster-no-face',
			name: 'No Face',
			faceCount: 3,
			photoCount: 3,
			representativeFace: undefined
		};

		vi.mocked(facesStore.subscribe).mockImplementation((callback) => {
			callback({
				clusters: [clusterWithoutFace],
				loading: false,
				error: null
			});
			return () => {};
		});

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		// Placeholder should be visible
		expect(screen.getByText('?')).toBeInTheDocument();
	});

	it('should disable search input while loading', () => {
		vi.mocked(facesStore.subscribe).mockImplementation((callback) => {
			callback({
				clusters: [],
				loading: true,
				error: null
			});
			return () => {};
		});

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		const searchInput = screen.getByPlaceholderText('Search by name...');
		expect(searchInput).toBeDisabled();
	});

	it('should call facesStore.load on mount', async () => {
		vi.mocked(facesStore.subscribe).mockImplementation((callback) => {
			callback({
				clusters: mockClusters,
				loading: false,
				error: null
			});
			return () => {};
		});

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		await waitFor(() => {
			expect(facesStore.load).toHaveBeenCalled();
		});
	});

	it('should handle keyboard Escape key', async () => {
		vi.mocked(facesStore.subscribe).mockImplementation((callback) => {
			callback({
				clusters: mockClusters,
				loading: false,
				error: null
			});
			return () => {};
		});

		const { component } = render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		const closeMock = vi.fn();
		component.$on('close', closeMock);

		const dialog = screen.getByRole('dialog');
		await fireEvent.keyDown(dialog.parentElement!, { key: 'Escape' });

		expect(closeMock).toHaveBeenCalled();
	});
});
