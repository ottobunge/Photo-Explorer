import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import ClusterPicker from './ClusterPicker.svelte';
import { facesStore } from '../stores/faces.svelte';
import type { FaceClusterType } from '../types';

// Mock the facesStore for Svelte 5 runes
vi.mock('../stores/faces.svelte', () => ({
	facesStore: {
		clusters: [],
		loading: false,
		error: null,
		load: vi.fn().mockResolvedValue(undefined),
		nameCluster: vi.fn(),
		mergeClusters: vi.fn(),
		reset: vi.fn()
	}
}));

// Helper to get mocked facesStore methods without unbound-method errors
const getMockedLoad = (): ReturnType<typeof vi.fn> => {
	const store = facesStore as { load: ReturnType<typeof vi.fn> };
	return store.load;
};

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
		// Reset store state
		facesStore.clusters = [];
		facesStore.loading = false;
		facesStore.error = null;
		// Reset the load mock to resolve immediately
		const mockLoad = getMockedLoad();
		mockLoad.mockResolvedValue(undefined);
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
		// Set store state directly (Svelte 5 pattern)
		facesStore.clusters = [];
		facesStore.loading = true;
		facesStore.error = null;

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		expect(screen.getByText('Loading clusters...')).toBeInTheDocument();
	});

	it('should show error state', async () => {
		// Set store state directly (Svelte 5 pattern)
		facesStore.clusters = [];
		facesStore.loading = false;
		facesStore.error = 'Failed to load clusters';
		const mockLoad = getMockedLoad();
		mockLoad.mockRejectedValue(new Error('Failed to load clusters'));

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		await waitFor(() => {
			expect(screen.getByText('Failed to load clusters')).toBeInTheDocument();
		});
	});

	it('should show no clusters message when list is empty', async () => {
		// Set store state directly (Svelte 5 pattern)
		facesStore.clusters = [];
		facesStore.loading = false;
		facesStore.error = null;

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		await waitFor(() => {
			expect(screen.getByText('No clusters available')).toBeInTheDocument();
		});
	});

	it('should render cluster list', async () => {
		// Set store state directly (Svelte 5 pattern)
		facesStore.clusters = mockClusters;
		facesStore.loading = false;
		facesStore.error = null;

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		await waitFor(() => {
			expect(screen.getByText('Alice')).toBeInTheDocument();
		});
		expect(screen.getByText('Bob')).toBeInTheDocument();
		expect(screen.getByText('Charlie')).toBeInTheDocument();
		expect(screen.getByText('Unknown')).toBeInTheDocument();
	});

	it('should show face and photo counts', async () => {
		// Set store state directly (Svelte 5 pattern)
		const cluster = mockClusters[0];
		expect(cluster).toBeDefined();
		facesStore.clusters = [cluster];
		facesStore.loading = false;
		facesStore.error = null;

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		await waitFor(() => {
			expect(screen.getByText(/15 faces/)).toBeInTheDocument();
		});
		expect(screen.getByText(/12 photos/)).toBeInTheDocument();
	});

	it('should exclude clusters by ID', async () => {
		// Set store state directly (Svelte 5 pattern)
		facesStore.clusters = mockClusters;
		facesStore.loading = false;
		facesStore.error = null;

		render(ClusterPicker, {
			props: {
				excludeClusterIds: ['cluster-1', 'cluster-2']
			}
		});

		await waitFor(() => {
			expect(screen.getByText('Charlie')).toBeInTheDocument();
		});
		expect(screen.queryByText('Alice')).not.toBeInTheDocument();
		expect(screen.queryByText('Bob')).not.toBeInTheDocument();
	});

	it('should filter clusters by search query', async () => {
		// Set store state directly (Svelte 5 pattern)
		facesStore.clusters = mockClusters;
		facesStore.loading = false;
		facesStore.error = null;

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		await waitFor(() => {
			expect(screen.getByPlaceholderText('Search by name...')).not.toBeDisabled();
		});

		const searchInput = screen.getByPlaceholderText('Search by name...');
		await fireEvent.input(searchInput, { target: { value: 'alice' } });

		expect(screen.getByText('Alice')).toBeInTheDocument();
		expect(screen.queryByText('Bob')).not.toBeInTheDocument();
		expect(screen.queryByText('Charlie')).not.toBeInTheDocument();
	});

	it('should show no results message when search has no matches', async () => {
		// Set store state directly (Svelte 5 pattern)
		facesStore.clusters = mockClusters;
		facesStore.loading = false;
		facesStore.error = null;

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		await waitFor(() => {
			expect(screen.getByPlaceholderText('Search by name...')).not.toBeDisabled();
		});

		const searchInput = screen.getByPlaceholderText('Search by name...');
		await fireEvent.input(searchInput, { target: { value: 'nonexistent' } });

		expect(screen.getByText('No clusters match your search')).toBeInTheDocument();
	});

	it('should sort clusters: named first, then by name alphabetically', async () => {
		// Set store state directly (Svelte 5 pattern)
		// eslint-disable-next-line @typescript-eslint/no-non-null-assertion
		facesStore.clusters = [mockClusters[3]!, mockClusters[2]!, mockClusters[0]!, mockClusters[1]!];
		facesStore.loading = false;
		facesStore.error = null;

		const { container: _container } = render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		await waitFor(() => {
			expect(screen.getByText('Alice')).toBeInTheDocument();
		});

		// Get only cluster buttons (inside the scrollable container, not Cancel or X buttons)
		const scrollContainer = _container.querySelector('.overflow-y-auto');
		const clusterButtons = scrollContainer?.querySelectorAll('button[type="button"]') ?? [];

		// Named clusters should appear first, alphabetically: Alice, Bob, Charlie, Unknown
		const textContent = Array.from(clusterButtons).map((btn) => btn.textContent);

		expect(textContent[0]).toContain('Alice');
		expect(textContent[1]).toContain('Bob');
		expect(textContent[2]).toContain('Charlie');
		expect(textContent[3]).toContain('Unknown');
	});

	// TODO: These event tests need the component to be migrated to Svelte 5 callback props
	// Currently the component uses createEventDispatcher which doesn't work with addEventListener in tests
	it.skip('should dispatch close event when backdrop is clicked', async () => {
		// Set store state directly (Svelte 5 pattern)
		facesStore.clusters = mockClusters;
		facesStore.loading = false;
		facesStore.error = null;

		const closeMock = vi.fn();

		// @ts-expect-error - container unused in skipped test
		// eslint-disable-next-line @typescript-eslint/no-unused-vars
		const { container } = render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		await waitFor(() => {
			expect(screen.getByRole('dialog')).toBeInTheDocument();
		});

		const backdrop = screen.getByRole('dialog').parentElement!;

		// Listen for the custom close event on the backdrop (component root)
		backdrop.addEventListener('close', closeMock);

		await fireEvent.click(backdrop);

		expect(closeMock).toHaveBeenCalled();
	});

	it.skip('should dispatch close event when Cancel button is clicked', async () => {
		// Set store state directly (Svelte 5 pattern)
		facesStore.clusters = mockClusters;
		facesStore.loading = false;
		facesStore.error = null;

		const closeMock = vi.fn();

		// @ts-expect-error - container unused in skipped test
		// eslint-disable-next-line @typescript-eslint/no-unused-vars
		const { container } = render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		await waitFor(() => {
			expect(screen.getByText('Cancel')).toBeInTheDocument();
		});

		const backdrop = screen.getByRole('dialog').parentElement!;

		// Listen for the custom close event on the backdrop (component root)
		backdrop.addEventListener('close', closeMock);

		const cancelButton = screen.getByText('Cancel');
		await fireEvent.click(cancelButton);

		expect(closeMock).toHaveBeenCalled();
	});

	it.skip('should dispatch close event when X button is clicked', async () => {
		// Set store state directly (Svelte 5 pattern)
		facesStore.clusters = mockClusters;
		facesStore.loading = false;
		facesStore.error = null;

		const closeMock = vi.fn();

		// @ts-expect-error - container unused in skipped test
		// eslint-disable-next-line @typescript-eslint/no-unused-vars
		const { container } = render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		await waitFor(() => {
			expect(screen.getByLabelText('Close modal')).toBeInTheDocument();
		});

		const backdrop = screen.getByRole('dialog').parentElement!;

		// Listen for the custom close event on the backdrop (component root)
		backdrop.addEventListener('close', closeMock);

		const closeButton = screen.getByLabelText('Close modal');
		await fireEvent.click(closeButton);

		expect(closeMock).toHaveBeenCalled();
	});

	it.skip('should dispatch select event when cluster is clicked', async () => {
		// Set store state directly (Svelte 5 pattern)
		facesStore.clusters = mockClusters;
		facesStore.loading = false;
		facesStore.error = null;

		const selectMock = vi.fn();

		// @ts-expect-error - container unused in skipped test
		// eslint-disable-next-line @typescript-eslint/no-unused-vars
		const { container } = render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		await waitFor(() => {
			expect(screen.getByText('Alice')).toBeInTheDocument();
		});

		const backdrop = screen.getByRole('dialog').parentElement!;

		// Listen for the custom select event on the backdrop (component root)
		backdrop.addEventListener('select', selectMock);

		const aliceButton = screen.getByText('Alice').closest('button')!;
		await fireEvent.click(aliceButton);

		expect(selectMock).toHaveBeenCalledTimes(1);
		expect(selectMock.mock.calls[0]![0].detail.cluster.id).toBe('cluster-1');
		expect(selectMock.mock.calls[0]![0].detail.cluster.name).toBe('Alice');
	});

	it('should show representative face image when available', async () => {
		// Set store state directly (Svelte 5 pattern)
		// eslint-disable-next-line @typescript-eslint/no-non-null-assertion
		facesStore.clusters = [mockClusters[0]!];
		facesStore.loading = false;
		facesStore.error = null;

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		await waitFor(() => {
			const img = screen.getByRole('img', { name: 'Alice' });
			expect(img).toBeInTheDocument();
			expect(img).toHaveAttribute('src', 'http://localhost:8000/api/v1/faces/crops/face-1.jpg');
		});
	});

	it('should show placeholder when no representative face', async () => {
		const clusterWithoutFace: FaceClusterType = {
			id: 'cluster-no-face',
			name: 'No Face',
			faceCount: 3,
			photoCount: 3
		};

		// Set store state directly (Svelte 5 pattern)
		facesStore.clusters = [clusterWithoutFace];
		facesStore.loading = false;
		facesStore.error = null;

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		await waitFor(() => {
			// Placeholder should be visible
			expect(screen.getByText('?')).toBeInTheDocument();
		});
	});

	it('should disable search input while loading', () => {
		// Set store state directly (Svelte 5 pattern)
		facesStore.clusters = [];
		facesStore.loading = true;
		facesStore.error = null;

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		const searchInput = screen.getByPlaceholderText('Search by name...');
		expect(searchInput).toBeDisabled();
	});

	it('should call facesStore.load on mount', async () => {
		// Set store state directly (Svelte 5 pattern)
		facesStore.clusters = mockClusters;
		facesStore.loading = false;
		facesStore.error = null;

		render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		await waitFor(() => {
			const mockLoad = getMockedLoad();
			expect(mockLoad).toHaveBeenCalled();
		});
	});

	it.skip('should handle keyboard Escape key', async () => {
		// Set store state directly (Svelte 5 pattern)
		facesStore.clusters = mockClusters;
		facesStore.loading = false;
		facesStore.error = null;

		const closeMock = vi.fn();

		// @ts-expect-error - container unused in skipped test
		// eslint-disable-next-line @typescript-eslint/no-unused-vars
		const { container } = render(ClusterPicker, {
			props: {
				excludeClusterIds: []
			}
		});

		await waitFor(() => {
			expect(screen.getByRole('dialog')).toBeInTheDocument();
		});

		const dialog = screen.getByRole('dialog');
		const backdrop = dialog.parentElement!;

		// Listen for the custom close event on the backdrop (component root)
		backdrop.addEventListener('close', closeMock);

		await fireEvent.keyDown(backdrop, { key: 'Escape' });

		expect(closeMock).toHaveBeenCalled();
	});
});
