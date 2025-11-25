// Faces store

import { writable } from 'svelte/store';
import type { FacesState, FaceClusterType } from '../types';

function createFacesStore() {
	const { subscribe, set, update } = writable<FacesState>({
		clusters: [],
		loading: false,
		error: null
	});

	return {
		subscribe,

		async load(options?: { namedOnly?: boolean; unnamedOnly?: boolean }) {
			update((state) => ({ ...state, loading: true, error: null }));

			try {
				const params = new URLSearchParams();
				if (options?.namedOnly) params.set('named_only', 'true');
				if (options?.unnamedOnly) params.set('unnamed_only', 'true');

				const response = await fetch(`/api/v1/faces/clusters?${params}`);
				if (!response.ok) throw new Error('Failed to load clusters');

				const data = await response.json();
				update((state) => ({
					...state,
					clusters: data.data.clusters,
					loading: false
				}));
			} catch (error) {
				update((state) => ({
					...state,
					error: error instanceof Error ? error.message : 'Failed to load clusters',
					loading: false
				}));
			}
		},

		async nameCluster(clusterId: string, name: string) {
			const response = await fetch(`/api/v1/faces/clusters/${clusterId}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name })
			});

			if (!response.ok) throw new Error('Failed to name cluster');

			const data = await response.json();
			update((state) => ({
				...state,
				clusters: state.clusters.map((c) => (c.id === clusterId ? data.data : c))
			}));
		},

		async mergeClusters(sourceIds: string[], targetId: string) {
			const response = await fetch('/api/v1/faces/clusters/merge', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					source_cluster_ids: sourceIds,
					target_cluster_id: targetId
				})
			});

			if (!response.ok) throw new Error('Failed to merge clusters');

			// Reload clusters
			await this.load();
		}
	};
}

export const facesStore = createFacesStore();
