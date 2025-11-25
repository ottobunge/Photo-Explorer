// Faces store

import { writable } from 'svelte/store';
import { client, ApiError } from '$lib/api/client';
import type { FacesState } from '../types';

function createFacesStore() {
	const { subscribe, update } = writable<FacesState>({
		clusters: [],
		loading: false,
		error: null
	});

	return {
		subscribe,

		async load(options?: { namedOnly?: boolean; unnamedOnly?: boolean }) {
			update((state) => ({ ...state, loading: true, error: null }));

			try {
				const params: Record<string, string> = {};
				if (options?.namedOnly) params['named_only'] = 'true';
				if (options?.unnamedOnly) params['unnamed_only'] = 'true';

				const result = await client.get<{ clusters: any[] }>('/faces/clusters', params);
				update((state) => ({
					...state,
					clusters: result.data.clusters,
					loading: false
				}));
			} catch (error) {
				const message = error instanceof ApiError ? error.message : 'Failed to load clusters';
				update((state) => ({
					...state,
					error: message,
					loading: false
				}));
			}
		},

		async nameCluster(clusterId: string, name: string) {
			const result = await client.patch<any>(`/faces/clusters/${clusterId}`, { name });
			update((state) => ({
				...state,
				clusters: state.clusters.map((c) => (c.id === clusterId ? result.data : c))
			}));
		},

		async mergeClusters(sourceIds: string[], targetId: string) {
			await client.post('/faces/clusters/merge', {
				source_cluster_ids: sourceIds,
				target_cluster_id: targetId
			});
			// Reload clusters
			await this.load();
		}
	};
}

export const facesStore = createFacesStore();
