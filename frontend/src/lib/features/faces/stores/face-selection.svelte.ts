// Face selection store for managing selection state in edit/manual grouping mode

import { splitFace, moveFace, mergeClusters } from '$lib/api/faces';
import type { Face, FaceClusterType } from '../types';

/**
 * Store for managing face and cluster selection in edit mode.
 * Uses Svelte 5 runes for reactive state management.
 */
class FaceSelectionStore {
	// State properties
	editMode = $state<boolean>(false);
	// Use arrays instead of Sets for better reactivity with Svelte 5 runes
	private _selectedFaceIds = $state<string[]>([]);
	private _selectedClusterIds = $state<string[]>([]);
	operationInProgress = $state<boolean>(false);
	error = $state<string | null>(null);

	// Expose as Sets for backwards compatibility
	get selectedFaceIds(): Set<string> {
		return new Set(this._selectedFaceIds);
	}

	get selectedClusterIds(): Set<string> {
		return new Set(this._selectedClusterIds);
	}

	// Derived state for convenience
	get hasSelectedFaces(): boolean {
		return this._selectedFaceIds.length > 0;
	}

	get hasSelectedClusters(): boolean {
		return this._selectedClusterIds.length > 0;
	}

	get selectedFaceCount(): number {
		return this._selectedFaceIds.length;
	}

	get selectedClusterCount(): number {
		return this._selectedClusterIds.length;
	}

	get hasAnySelection(): boolean {
		return this.hasSelectedFaces || this.hasSelectedClusters;
	}

	// ==================
	// Edit Mode Management
	// ==================

	/**
	 * Enable edit/selection mode.
	 * Clears any existing selections when entering edit mode.
	 */
	enterEditMode(): void {
		this.editMode = true;
		this.clearAll();
	}

	/**
	 * Disable edit/selection mode.
	 * Automatically clears all selections when exiting.
	 */
	exitEditMode(): void {
		this.editMode = false;
		this.clearAll();
	}

	/**
	 * Toggle edit mode on/off.
	 */
	toggleEditMode(): void {
		if (this.editMode) {
			this.exitEditMode();
		} else {
			this.enterEditMode();
		}
	}

	// ==================
	// Face Selection
	// ==================

	/**
	 * Select a single face.
	 * @param faceId - ID of the face to select
	 */
	selectFace(faceId: string): void {
		if (!this._selectedFaceIds.includes(faceId)) {
			this._selectedFaceIds.push(faceId);
		}
	}

	/**
	 * Deselect a single face.
	 * @param faceId - ID of the face to deselect
	 */
	deselectFace(faceId: string): void {
		this._selectedFaceIds = this._selectedFaceIds.filter((id) => id !== faceId);
	}

	/**
	 * Toggle face selection.
	 * @param faceId - ID of the face to toggle
	 */
	toggleFace(faceId: string): void {
		if (this.selectedFaceIds.has(faceId)) {
			this.deselectFace(faceId);
		} else {
			this.selectFace(faceId);
		}
	}

	/**
	 * Check if a face is selected.
	 * @param faceId - ID of the face to check
	 * @returns true if the face is selected
	 */
	isFaceSelected(faceId: string): boolean {
		return this._selectedFaceIds.includes(faceId);
	}

	/**
	 * Select multiple faces at once.
	 * @param faceIds - Array of face IDs to select
	 */
	selectFaces(faceIds: string[]): void {
		faceIds.forEach((id) => {
			if (!this._selectedFaceIds.includes(id)) {
				this._selectedFaceIds.push(id);
			}
		});
	}

	/**
	 * Select all faces from the provided list.
	 * Useful for "Select All" functionality in a view.
	 * @param faces - Array of faces to select
	 */
	selectAllFaces(faces: Face[]): void {
		faces.forEach((face) => {
			if (!this._selectedFaceIds.includes(face.id)) {
				this._selectedFaceIds.push(face.id);
			}
		});
	}

	/**
	 * Deselect all faces.
	 */
	clearFaceSelection(): void {
		this._selectedFaceIds = [];
	}

	// ==================
	// Cluster Selection
	// ==================

	/**
	 * Select a single cluster.
	 * @param clusterId - ID of the cluster to select
	 */
	selectCluster(clusterId: string): void {
		if (!this._selectedClusterIds.includes(clusterId)) {
			this._selectedClusterIds.push(clusterId);
		}
	}

	/**
	 * Deselect a single cluster.
	 * @param clusterId - ID of the cluster to deselect
	 */
	deselectCluster(clusterId: string): void {
		this._selectedClusterIds = this._selectedClusterIds.filter((id) => id !== clusterId);
	}

	/**
	 * Toggle cluster selection.
	 * @param clusterId - ID of the cluster to toggle
	 */
	toggleCluster(clusterId: string): void {
		if (this.selectedClusterIds.has(clusterId)) {
			this.deselectCluster(clusterId);
		} else {
			this.selectCluster(clusterId);
		}
	}

	/**
	 * Check if a cluster is selected.
	 * @param clusterId - ID of the cluster to check
	 * @returns true if the cluster is selected
	 */
	isClusterSelected(clusterId: string): boolean {
		return this._selectedClusterIds.includes(clusterId);
	}

	/**
	 * Select multiple clusters at once.
	 * @param clusterIds - Array of cluster IDs to select
	 */
	selectClusters(clusterIds: string[]): void {
		clusterIds.forEach((id) => {
			if (!this._selectedClusterIds.includes(id)) {
				this._selectedClusterIds.push(id);
			}
		});
	}

	/**
	 * Select all clusters from the provided list.
	 * @param clusters - Array of clusters to select
	 */
	selectAllClusters(clusters: FaceClusterType[]): void {
		clusters.forEach((cluster) => {
			if (!this._selectedClusterIds.includes(cluster.id)) {
				this._selectedClusterIds.push(cluster.id);
			}
		});
	}

	/**
	 * Deselect all clusters.
	 */
	clearClusterSelection(): void {
		this._selectedClusterIds = [];
	}

	// ==================
	// Bulk Operations
	// ==================

	/**
	 * Clear all selections (faces and clusters).
	 */
	clearAll(): void {
		this._selectedFaceIds = [];
		this._selectedClusterIds = [];
		this.error = null;
	}

	/**
	 * Get array of selected face IDs.
	 * @returns Array of selected face IDs
	 */
	getSelectedFaceIds(): string[] {
		return [...this._selectedFaceIds];
	}

	/**
	 * Get array of selected cluster IDs.
	 * @returns Array of selected cluster IDs
	 */
	getSelectedClusterIds(): string[] {
		return [...this._selectedClusterIds];
	}

	// ==================
	// Cluster Operations
	// ==================

	/**
	 * Split selected faces into new clusters.
	 * Each face will be moved to its own new cluster.
	 * Clears selection and exits edit mode on success.
	 * @returns Array of newly created clusters
	 * @throws Error if operation fails
	 */
	async splitSelectedFaces(): Promise<FaceClusterType[]> {
		if (!this.hasSelectedFaces) {
			throw new Error('No faces selected for split operation');
		}

		this.operationInProgress = true;
		this.error = null;

		try {
			const faceIds = this.getSelectedFaceIds();
			const results = await Promise.all(faceIds.map((faceId) => splitFace(faceId)));

			// Success - clear selection and exit edit mode
			this.clearAll();
			this.exitEditMode();

			return results;
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to split faces';
			this.error = errorMessage;
			console.error('Failed to split faces:', err);
			throw err;
		} finally {
			this.operationInProgress = false;
		}
	}

	/**
	 * Move selected faces to a target cluster.
	 * Clears selection and exits edit mode on success.
	 * @param targetClusterId - ID of the cluster to move faces to
	 * @returns The target cluster with faces added
	 * @throws Error if operation fails
	 */
	async moveSelectedFaces(targetClusterId: string): Promise<FaceClusterType> {
		if (!this.hasSelectedFaces) {
			throw new Error('No faces selected for move operation');
		}

		this.operationInProgress = true;
		this.error = null;

		try {
			const faceIds = this.getSelectedFaceIds();

			// Move all faces to target cluster
			// Only return the result from the last operation since they all target the same cluster
			let result: FaceClusterType | null = null;
			for (const faceId of faceIds) {
				result = await moveFace(faceId, targetClusterId);
			}

			if (!result) {
				throw new Error('Move operation completed but no result returned');
			}

			// Success - clear selection and exit edit mode
			this.clearAll();
			this.exitEditMode();

			return result;
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to move faces';
			this.error = errorMessage;
			console.error('Failed to move faces:', err);
			throw err;
		} finally {
			this.operationInProgress = false;
		}
	}

	/**
	 * Merge selected clusters into a target cluster.
	 * Target cluster must be one of the selected clusters.
	 * Clears selection and exits edit mode on success.
	 * @param targetClusterId - ID of the cluster to merge into (must be in selection)
	 * @returns The target cluster with all faces merged
	 * @throws Error if operation fails or target is not selected
	 */
	async mergeSelectedClusters(targetClusterId: string): Promise<FaceClusterType> {
		if (!this.hasSelectedClusters) {
			throw new Error('No clusters selected for merge operation');
		}

		if (this.selectedClusterIds.size < 2) {
			throw new Error('At least 2 clusters must be selected for merge operation');
		}

		if (!this.isClusterSelected(targetClusterId)) {
			throw new Error('Target cluster must be one of the selected clusters');
		}

		this.operationInProgress = true;
		this.error = null;

		try {
			// Get all selected clusters except the target
			const sourceClusterIds = this.getSelectedClusterIds().filter((id) => id !== targetClusterId);

			const result = await mergeClusters(sourceClusterIds, targetClusterId);

			// Success - clear selection and exit edit mode
			this.clearAll();
			this.exitEditMode();

			return result;
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to merge clusters';
			this.error = errorMessage;
			console.error('Failed to merge clusters:', err);
			throw err;
		} finally {
			this.operationInProgress = false;
		}
	}

	// ==================
	// Utility Methods
	// ==================

	/**
	 * Clear error state.
	 */
	clearError(): void {
		this.error = null;
	}

	/**
	 * Reset store to initial state.
	 */
	reset(): void {
		this.editMode = false;
		this._selectedFaceIds = [];
		this._selectedClusterIds = [];
		this.operationInProgress = false;
		this.error = null;
	}
}

// Export singleton instance
export const faceSelectionStore = new FaceSelectionStore();
