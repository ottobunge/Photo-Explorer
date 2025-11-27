// Faces store using Svelte 5 runes

import { client, ApiError } from '$lib/api/client';
import type { FaceClusterType } from '../types';

/**
 * Store for managing face clusters list.
 * Uses Svelte 5 runes for reactive state management.
 */
class FacesStore {
	// State properties
	clusters = $state<FaceClusterType[]>([]);
	loading = $state<boolean>(false);
	error = $state<string | null>(null);

	/**
	 * Load face clusters with optional filters
	 */
	async load(options?: { namedOnly?: boolean; unnamedOnly?: boolean }): Promise<void> {
		this.loading = true;
		this.error = null;

		try {
			const params: Record<string, string> = {};
			if (options?.namedOnly) params['named_only'] = 'true';
			if (options?.unnamedOnly) params['unnamed_only'] = 'true';

			const result = await client.get<{ clusters: FaceClusterType[] }>(
				'/faces/clusters',
				params
			);

			if (result.success && result.data) {
				this.clusters = result.data.clusters;
			}
		} catch (err) {
			const message = err instanceof ApiError ? err.message : 'Failed to load clusters';
			this.error = message;
			console.error('Failed to load face clusters:', err);
		} finally {
			this.loading = false;
		}
	}

	/**
	 * Update the name of a cluster
	 */
	async nameCluster(clusterId: string, name: string): Promise<void> {
		try {
			const result = await client.patch<FaceClusterType>(`/faces/clusters/${clusterId}`, {
				name
			});

			if (result.success && result.data) {
				// Update the cluster in the list
				this.clusters = this.clusters.map((c) =>
					c.id === clusterId ? result.data! : c
				);
			}
		} catch (err) {
			const message = err instanceof ApiError ? err.message : 'Failed to update cluster name';
			this.error = message;
			console.error('Failed to name cluster:', err);
			throw err;
		}
	}

	/**
	 * Merge multiple clusters into a target cluster
	 */
	async mergeClusters(sourceIds: string[], targetId: string): Promise<void> {
		try {
			await client.post('/faces/clusters/merge', {
				source_cluster_ids: sourceIds,
				target_cluster_id: targetId
			});

			// Reload clusters after merge
			await this.load();
		} catch (err) {
			const message = err instanceof ApiError ? err.message : 'Failed to merge clusters';
			this.error = message;
			console.error('Failed to merge clusters:', err);
			throw err;
		}
	}

	/**
	 * Reset the store to initial state
	 */
	reset(): void {
		this.clusters = [];
		this.loading = false;
		this.error = null;
	}
}

// Export singleton instance
export const facesStore = new FacesStore();
