// Face Graph store using Svelte 5 runes

import { client, ApiError } from '$lib/api/client';
import type { SocialGraph } from '../types';

/**
 * Store for managing face social graph state.
 * Uses Svelte 5 runes for reactive state management.
 */
class FaceGraphStore {
	// State properties
	graph = $state<SocialGraph | null>(null);
	filteredPersonId = $state<string | null>(null);
	loading = $state<boolean>(false);
	error = $state<string | null>(null);

	/**
	 * Load the social graph, optionally filtered by a person
	 */
	async loadGraph(personId?: string): Promise<void> {
		this.loading = true;
		this.error = null;

		try {
			const params: Record<string, string> = {};
			if (personId) {
				params['person_id'] = personId;
			}

			const result = await client.get<SocialGraph>('/faces/graph', params);

			if (result.success && result.data !== null && result.data !== undefined) {
				this.graph = result.data;
				this.filteredPersonId = personId ?? null;
			}
		} catch (err) {
			const message = err instanceof ApiError ? err.message : 'Failed to load social graph';
			this.error = message;
			console.error('Failed to load social graph:', err);
		} finally {
			this.loading = false;
		}
	}

	/**
	 * Filter the graph to show only a specific person's network
	 */
	async filterByPerson(personId: string): Promise<void> {
		await this.loadGraph(personId);
	}

	/**
	 * Clear the filter and show the complete graph
	 */
	async clearFilter(): Promise<void> {
		await this.loadGraph();
	}

	/**
	 * Reset the store to initial state
	 */
	reset(): void {
		this.graph = null;
		this.filteredPersonId = null;
		this.loading = false;
		this.error = null;
	}
}

// Export singleton instance
export const faceGraphStore = new FaceGraphStore();
