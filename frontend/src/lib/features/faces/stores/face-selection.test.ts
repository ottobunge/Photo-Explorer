import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { faceSelectionStore } from './face-selection.svelte';
import * as facesApi from '$lib/api/faces';
import type { Face, FaceClusterType } from '../types';

// Mock the faces API
vi.mock('$lib/api/faces', () => ({
	splitFace: vi.fn(),
	moveFace: vi.fn(),
	mergeClusters: vi.fn()
}));

describe('faceSelectionStore', () => {
	const mockFace1: Face = {
		id: 'face-1',
		photoId: 'photo-1',
		cropUrl: '/crops/face-1.jpg'
	};

	const mockFace2: Face = {
		id: 'face-2',
		photoId: 'photo-2',
		cropUrl: '/crops/face-2.jpg'
	};

	const mockFace3: Face = {
		id: 'face-3',
		photoId: 'photo-3',
		cropUrl: '/crops/face-3.jpg'
	};

	const mockCluster1: FaceClusterType = {
		id: 'cluster-1',
		name: 'Alice',
		faceCount: 10,
		photoCount: 8,
		representativeFace: {
			id: 'face-1',
			cropUrl: '/crops/face-1.jpg'
		}
	};

	const mockCluster2: FaceClusterType = {
		id: 'cluster-2',
		name: 'Bob',
		faceCount: 5,
		photoCount: 4,
		representativeFace: {
			id: 'face-4',
			cropUrl: '/crops/face-4.jpg'
		}
	};

	const mockCluster3: FaceClusterType = {
		id: 'cluster-3',
		faceCount: 3,
		photoCount: 3
	};

	beforeEach(() => {
		// Reset store to initial state
		faceSelectionStore.reset();
		vi.clearAllMocks();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	describe('initial state', () => {
		it('should start with edit mode disabled', () => {
			expect(faceSelectionStore.editMode).toBe(false);
		});

		it('should start with empty selections', () => {
			expect(faceSelectionStore.selectedFaceIds.size).toBe(0);
			expect(faceSelectionStore.selectedClusterIds.size).toBe(0);
		});

		it('should have no operation in progress', () => {
			expect(faceSelectionStore.operationInProgress).toBe(false);
		});

		it('should have no error', () => {
			expect(faceSelectionStore.error).toBeNull();
		});

		it('should have correct derived state', () => {
			expect(faceSelectionStore.hasSelectedFaces).toBe(false);
			expect(faceSelectionStore.hasSelectedClusters).toBe(false);
			expect(faceSelectionStore.selectedFaceCount).toBe(0);
			expect(faceSelectionStore.selectedClusterCount).toBe(0);
			expect(faceSelectionStore.hasAnySelection).toBe(false);
		});
	});

	describe('edit mode management', () => {
		it('should enter edit mode', () => {
			faceSelectionStore.enterEditMode();
			expect(faceSelectionStore.editMode).toBe(true);
		});

		it('should exit edit mode', () => {
			faceSelectionStore.enterEditMode();
			faceSelectionStore.selectFace('face-1');
			faceSelectionStore.exitEditMode();

			expect(faceSelectionStore.editMode).toBe(false);
			expect(faceSelectionStore.selectedFaceIds.size).toBe(0);
		});

		it('should toggle edit mode on', () => {
			faceSelectionStore.toggleEditMode();
			expect(faceSelectionStore.editMode).toBe(true);
		});

		it('should toggle edit mode off', () => {
			faceSelectionStore.enterEditMode();
			faceSelectionStore.toggleEditMode();
			expect(faceSelectionStore.editMode).toBe(false);
		});

		it('should clear selections when entering edit mode', () => {
			faceSelectionStore.selectFace('face-1');
			faceSelectionStore.selectCluster('cluster-1');

			faceSelectionStore.enterEditMode();

			expect(faceSelectionStore.selectedFaceIds.size).toBe(0);
			expect(faceSelectionStore.selectedClusterIds.size).toBe(0);
		});
	});

	describe('face selection', () => {
		it('should select a face', () => {
			faceSelectionStore.selectFace('face-1');

			expect(faceSelectionStore.isFaceSelected('face-1')).toBe(true);
			expect(faceSelectionStore.selectedFaceCount).toBe(1);
			expect(faceSelectionStore.hasSelectedFaces).toBe(true);
		});

		it('should deselect a face', () => {
			faceSelectionStore.selectFace('face-1');
			faceSelectionStore.deselectFace('face-1');

			expect(faceSelectionStore.isFaceSelected('face-1')).toBe(false);
			expect(faceSelectionStore.selectedFaceCount).toBe(0);
		});

		it('should toggle face selection on', () => {
			faceSelectionStore.toggleFace('face-1');

			expect(faceSelectionStore.isFaceSelected('face-1')).toBe(true);
		});

		it('should toggle face selection off', () => {
			faceSelectionStore.selectFace('face-1');
			faceSelectionStore.toggleFace('face-1');

			expect(faceSelectionStore.isFaceSelected('face-1')).toBe(false);
		});

		it('should select multiple faces at once', () => {
			faceSelectionStore.selectFaces(['face-1', 'face-2', 'face-3']);

			expect(faceSelectionStore.selectedFaceCount).toBe(3);
			expect(faceSelectionStore.isFaceSelected('face-1')).toBe(true);
			expect(faceSelectionStore.isFaceSelected('face-2')).toBe(true);
			expect(faceSelectionStore.isFaceSelected('face-3')).toBe(true);
		});

		it('should select all faces from array', () => {
			const faces = [mockFace1, mockFace2, mockFace3];
			faceSelectionStore.selectAllFaces(faces);

			expect(faceSelectionStore.selectedFaceCount).toBe(3);
		});

		it('should clear face selection', () => {
			faceSelectionStore.selectFaces(['face-1', 'face-2']);
			faceSelectionStore.clearFaceSelection();

			expect(faceSelectionStore.selectedFaceCount).toBe(0);
			expect(faceSelectionStore.hasSelectedFaces).toBe(false);
		});

		it('should get array of selected face IDs', () => {
			faceSelectionStore.selectFaces(['face-1', 'face-3']);
			const selected = faceSelectionStore.getSelectedFaceIds();

			expect(selected).toBeInstanceOf(Array);
			expect(selected).toHaveLength(2);
			expect(selected).toContain('face-1');
			expect(selected).toContain('face-3');
		});
	});

	describe('cluster selection', () => {
		it('should select a cluster', () => {
			faceSelectionStore.selectCluster('cluster-1');

			expect(faceSelectionStore.isClusterSelected('cluster-1')).toBe(true);
			expect(faceSelectionStore.selectedClusterCount).toBe(1);
			expect(faceSelectionStore.hasSelectedClusters).toBe(true);
		});

		it('should deselect a cluster', () => {
			faceSelectionStore.selectCluster('cluster-1');
			faceSelectionStore.deselectCluster('cluster-1');

			expect(faceSelectionStore.isClusterSelected('cluster-1')).toBe(false);
			expect(faceSelectionStore.selectedClusterCount).toBe(0);
		});

		it('should toggle cluster selection on', () => {
			faceSelectionStore.toggleCluster('cluster-1');

			expect(faceSelectionStore.isClusterSelected('cluster-1')).toBe(true);
		});

		it('should toggle cluster selection off', () => {
			faceSelectionStore.selectCluster('cluster-1');
			faceSelectionStore.toggleCluster('cluster-1');

			expect(faceSelectionStore.isClusterSelected('cluster-1')).toBe(false);
		});

		it('should select multiple clusters at once', () => {
			faceSelectionStore.selectClusters(['cluster-1', 'cluster-2', 'cluster-3']);

			expect(faceSelectionStore.selectedClusterCount).toBe(3);
			expect(faceSelectionStore.isClusterSelected('cluster-1')).toBe(true);
			expect(faceSelectionStore.isClusterSelected('cluster-2')).toBe(true);
			expect(faceSelectionStore.isClusterSelected('cluster-3')).toBe(true);
		});

		it('should select all clusters from array', () => {
			const clusters = [mockCluster1, mockCluster2, mockCluster3];
			faceSelectionStore.selectAllClusters(clusters);

			expect(faceSelectionStore.selectedClusterCount).toBe(3);
		});

		it('should clear cluster selection', () => {
			faceSelectionStore.selectClusters(['cluster-1', 'cluster-2']);
			faceSelectionStore.clearClusterSelection();

			expect(faceSelectionStore.selectedClusterCount).toBe(0);
			expect(faceSelectionStore.hasSelectedClusters).toBe(false);
		});

		it('should get array of selected cluster IDs', () => {
			faceSelectionStore.selectClusters(['cluster-1', 'cluster-3']);
			const selected = faceSelectionStore.getSelectedClusterIds();

			expect(selected).toBeInstanceOf(Array);
			expect(selected).toHaveLength(2);
			expect(selected).toContain('cluster-1');
			expect(selected).toContain('cluster-3');
		});
	});

	describe('bulk operations', () => {
		it('should clear all selections', () => {
			faceSelectionStore.selectFaces(['face-1', 'face-2']);
			faceSelectionStore.selectClusters(['cluster-1', 'cluster-2']);

			faceSelectionStore.clearAll();

			expect(faceSelectionStore.selectedFaceCount).toBe(0);
			expect(faceSelectionStore.selectedClusterCount).toBe(0);
			expect(faceSelectionStore.hasAnySelection).toBe(false);
		});

		it('should clear error when clearing all', () => {
			faceSelectionStore.error = 'Some error';
			faceSelectionStore.clearAll();

			expect(faceSelectionStore.error).toBeNull();
		});
	});

	describe('hasAnySelection derived state', () => {
		it('should be true when faces are selected', () => {
			faceSelectionStore.selectFace('face-1');
			expect(faceSelectionStore.hasAnySelection).toBe(true);
		});

		it('should be true when clusters are selected', () => {
			faceSelectionStore.selectCluster('cluster-1');
			expect(faceSelectionStore.hasAnySelection).toBe(true);
		});

		it('should be true when both faces and clusters are selected', () => {
			faceSelectionStore.selectFace('face-1');
			faceSelectionStore.selectCluster('cluster-1');
			expect(faceSelectionStore.hasAnySelection).toBe(true);
		});

		it('should be false when nothing is selected', () => {
			expect(faceSelectionStore.hasAnySelection).toBe(false);
		});
	});

	describe('splitSelectedFaces', () => {
		it('should throw error when no faces selected', async () => {
			await expect(faceSelectionStore.splitSelectedFaces()).rejects.toThrow(
				'No faces selected for split operation'
			);
		});

		it('should split selected faces successfully', async () => {
			const mockResult1: FaceClusterType = {
				id: 'new-cluster-1',
				faceCount: 1,
				photoCount: 1
			};
			const mockResult2: FaceClusterType = {
				id: 'new-cluster-2',
				faceCount: 1,
				photoCount: 1
			};

			vi.mocked(facesApi.splitFace).mockResolvedValueOnce(mockResult1);
			vi.mocked(facesApi.splitFace).mockResolvedValueOnce(mockResult2);

			faceSelectionStore.enterEditMode();
			faceSelectionStore.selectFaces(['face-1', 'face-2']);

			const results = await faceSelectionStore.splitSelectedFaces();

			expect(results).toHaveLength(2);
			expect(results[0]).toEqual(mockResult1);
			expect(results[1]).toEqual(mockResult2);
			expect(vi.mocked(facesApi.splitFace)).toHaveBeenCalledTimes(2);
			expect(vi.mocked(facesApi.splitFace)).toHaveBeenCalledWith('face-1');
			expect(vi.mocked(facesApi.splitFace)).toHaveBeenCalledWith('face-2');
		});

		it('should clear selection and exit edit mode after successful split', async () => {
			const mockResult: FaceClusterType = {
				id: 'new-cluster',
				faceCount: 1,
				photoCount: 1
			};

			vi.mocked(facesApi.splitFace).mockResolvedValue(mockResult);

			faceSelectionStore.enterEditMode();
			faceSelectionStore.selectFace('face-1');

			await faceSelectionStore.splitSelectedFaces();

			expect(faceSelectionStore.editMode).toBe(false);
			expect(faceSelectionStore.selectedFaceCount).toBe(0);
		});

		it('should set operation in progress during split', async () => {
			vi.mocked(facesApi.splitFace).mockImplementation(
				() =>
					new Promise((resolve) => {
						expect(faceSelectionStore.operationInProgress).toBe(true);
						resolve({ id: 'new', faceCount: 1, photoCount: 1 });
					})
			);

			faceSelectionStore.selectFace('face-1');
			await faceSelectionStore.splitSelectedFaces();

			expect(faceSelectionStore.operationInProgress).toBe(false);
		});

		it('should handle split errors', async () => {
			const error = new Error('Network error');
			vi.mocked(facesApi.splitFace).mockRejectedValue(error);

			faceSelectionStore.selectFace('face-1');

			await expect(faceSelectionStore.splitSelectedFaces()).rejects.toThrow('Network error');

			expect(faceSelectionStore.error).toBe('Network error');
			expect(faceSelectionStore.operationInProgress).toBe(false);
		});

		it('should not clear selection on error', async () => {
			vi.mocked(facesApi.splitFace).mockRejectedValue(new Error('Failed'));

			faceSelectionStore.enterEditMode();
			faceSelectionStore.selectFace('face-1');

			await expect(faceSelectionStore.splitSelectedFaces()).rejects.toThrow();

			expect(faceSelectionStore.editMode).toBe(true);
			expect(faceSelectionStore.selectedFaceCount).toBe(1);
		});
	});

	describe('moveSelectedFaces', () => {
		it('should throw error when no faces selected', async () => {
			await expect(faceSelectionStore.moveSelectedFaces('target-cluster')).rejects.toThrow(
				'No faces selected for move operation'
			);
		});

		it('should move selected faces successfully', async () => {
			const mockResult: FaceClusterType = {
				id: 'target-cluster',
				name: 'Alice',
				faceCount: 12,
				photoCount: 10
			};

			vi.mocked(facesApi.moveFace).mockResolvedValue(mockResult);

			faceSelectionStore.enterEditMode();
			faceSelectionStore.selectFaces(['face-1', 'face-2']);

			const result = await faceSelectionStore.moveSelectedFaces('target-cluster');

			expect(result).toEqual(mockResult);
			expect(vi.mocked(facesApi.moveFace)).toHaveBeenCalledTimes(2);
			expect(vi.mocked(facesApi.moveFace)).toHaveBeenCalledWith('face-1', 'target-cluster');
			expect(vi.mocked(facesApi.moveFace)).toHaveBeenCalledWith('face-2', 'target-cluster');
		});

		it('should clear selection and exit edit mode after successful move', async () => {
			const mockResult: FaceClusterType = {
				id: 'target-cluster',
				faceCount: 11,
				photoCount: 10
			};

			vi.mocked(facesApi.moveFace).mockResolvedValue(mockResult);

			faceSelectionStore.enterEditMode();
			faceSelectionStore.selectFace('face-1');

			await faceSelectionStore.moveSelectedFaces('target-cluster');

			expect(faceSelectionStore.editMode).toBe(false);
			expect(faceSelectionStore.selectedFaceCount).toBe(0);
		});

		it('should set operation in progress during move', async () => {
			vi.mocked(facesApi.moveFace).mockImplementation(
				() =>
					new Promise((resolve) => {
						expect(faceSelectionStore.operationInProgress).toBe(true);
						resolve({ id: 'target', faceCount: 11, photoCount: 10 });
					})
			);

			faceSelectionStore.selectFace('face-1');
			await faceSelectionStore.moveSelectedFaces('target-cluster');

			expect(faceSelectionStore.operationInProgress).toBe(false);
		});

		it('should handle move errors', async () => {
			const error = new Error('Target cluster not found');
			vi.mocked(facesApi.moveFace).mockRejectedValue(error);

			faceSelectionStore.selectFace('face-1');

			await expect(faceSelectionStore.moveSelectedFaces('invalid')).rejects.toThrow(
				'Target cluster not found'
			);

			expect(faceSelectionStore.error).toBe('Target cluster not found');
			expect(faceSelectionStore.operationInProgress).toBe(false);
		});
	});

	describe('mergeSelectedClusters', () => {
		it('should throw error when no clusters selected', async () => {
			await expect(faceSelectionStore.mergeSelectedClusters('target')).rejects.toThrow(
				'No clusters selected for merge operation'
			);
		});

		it('should throw error when less than 2 clusters selected', async () => {
			faceSelectionStore.selectCluster('cluster-1');

			await expect(faceSelectionStore.mergeSelectedClusters('cluster-1')).rejects.toThrow(
				'At least 2 clusters must be selected for merge operation'
			);
		});

		it('should throw error when target is not in selection', async () => {
			faceSelectionStore.selectClusters(['cluster-1', 'cluster-2']);

			await expect(faceSelectionStore.mergeSelectedClusters('cluster-3')).rejects.toThrow(
				'Target cluster must be one of the selected clusters'
			);
		});

		it('should merge selected clusters successfully', async () => {
			const mockResult: FaceClusterType = {
				id: 'cluster-1',
				name: 'Alice',
				faceCount: 15,
				photoCount: 12
			};

			vi.mocked(facesApi.mergeClusters).mockResolvedValue(mockResult);

			faceSelectionStore.enterEditMode();
			faceSelectionStore.selectClusters(['cluster-1', 'cluster-2', 'cluster-3']);

			const result = await faceSelectionStore.mergeSelectedClusters('cluster-1');

			expect(result).toEqual(mockResult);
			expect(vi.mocked(facesApi.mergeClusters)).toHaveBeenCalledTimes(1);
			expect(vi.mocked(facesApi.mergeClusters)).toHaveBeenCalledWith(
				['cluster-2', 'cluster-3'],
				'cluster-1'
			);
		});

		it('should clear selection and exit edit mode after successful merge', async () => {
			const mockResult: FaceClusterType = {
				id: 'cluster-1',
				faceCount: 15,
				photoCount: 12
			};

			vi.mocked(facesApi.mergeClusters).mockResolvedValue(mockResult);

			faceSelectionStore.enterEditMode();
			faceSelectionStore.selectClusters(['cluster-1', 'cluster-2']);

			await faceSelectionStore.mergeSelectedClusters('cluster-1');

			expect(faceSelectionStore.editMode).toBe(false);
			expect(faceSelectionStore.selectedClusterCount).toBe(0);
		});

		it('should set operation in progress during merge', async () => {
			vi.mocked(facesApi.mergeClusters).mockImplementation(
				() =>
					new Promise((resolve) => {
						expect(faceSelectionStore.operationInProgress).toBe(true);
						resolve({ id: 'cluster-1', faceCount: 15, photoCount: 12 });
					})
			);

			faceSelectionStore.selectClusters(['cluster-1', 'cluster-2']);
			await faceSelectionStore.mergeSelectedClusters('cluster-1');

			expect(faceSelectionStore.operationInProgress).toBe(false);
		});

		it('should handle merge errors', async () => {
			const error = new Error('Merge failed');
			vi.mocked(facesApi.mergeClusters).mockRejectedValue(error);

			faceSelectionStore.selectClusters(['cluster-1', 'cluster-2']);

			await expect(faceSelectionStore.mergeSelectedClusters('cluster-1')).rejects.toThrow(
				'Merge failed'
			);

			expect(faceSelectionStore.error).toBe('Merge failed');
			expect(faceSelectionStore.operationInProgress).toBe(false);
		});
	});

	describe('error handling', () => {
		it('should clear error', () => {
			faceSelectionStore.error = 'Some error';
			faceSelectionStore.clearError();

			expect(faceSelectionStore.error).toBeNull();
		});

		it('should clear error when calling clearAll', () => {
			faceSelectionStore.error = 'Some error';
			faceSelectionStore.clearAll();

			expect(faceSelectionStore.error).toBeNull();
		});
	});

	describe('reset', () => {
		it('should reset store to initial state', () => {
			faceSelectionStore.enterEditMode();
			faceSelectionStore.selectFaces(['face-1', 'face-2']);
			faceSelectionStore.selectClusters(['cluster-1']);
			faceSelectionStore.error = 'Some error';

			faceSelectionStore.reset();

			expect(faceSelectionStore.editMode).toBe(false);
			expect(faceSelectionStore.selectedFaceCount).toBe(0);
			expect(faceSelectionStore.selectedClusterCount).toBe(0);
			expect(faceSelectionStore.operationInProgress).toBe(false);
			expect(faceSelectionStore.error).toBeNull();
		});
	});
});
