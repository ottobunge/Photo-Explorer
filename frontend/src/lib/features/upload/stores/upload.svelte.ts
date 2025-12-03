// Upload store using Svelte 5 runes

import type { UploadItem } from '../types';

/**
 * Store for managing file upload state.
 * Uses Svelte 5 runes for reactive state management.
 */
class UploadStore {
	// State properties
	items: UploadItem[] = $state([]);
	uploading: boolean = $state(false);

	// Derived state
	totalItems: number = $derived(this.items.length);
	pendingItems: number = $derived(this.items.filter((item) => item.status === 'pending').length);
	uploadingItems: number = $derived(this.items.filter((item) => item.status === 'uploading').length);
	completedItems: number = $derived(this.items.filter((item) => item.status === 'completed').length);
	failedItems: number = $derived(this.items.filter((item) => item.status === 'failed').length);
	totalProgress: number = $derived.by(() => {
		if (this.items.length === 0) {return 0;}
		const sum = this.items.reduce((acc, item) => acc + item.progress, 0);
		return Math.round(sum / this.items.length);
	});

	/**
	 * Add files to the upload queue
	 */
	addFiles(files: File[]): void {
		const newItems: UploadItem[] = files.map((file) => ({
			id: crypto.randomUUID(),
			file,
			progress: 0,
			status: 'pending'
		}));
		this.items = [...this.items, ...newItems];
	}

	/**
	 * Remove an item from the upload queue
	 */
	removeItem(id: string): void {
		this.items = this.items.filter((item) => item.id !== id);
	}

	/**
	 * Update the upload progress for a specific item
	 */
	updateProgress(id: string, progress: number): void {
		const item = this.items.find((item) => item.id === id);
		if (!item) return;

		// Don't update if already completed or failed
		if (item.status === 'completed' || item.status === 'failed') return;

		// Update progress
		item.progress = progress;

		// Determine the appropriate status based on progress
		if (progress > 0 && progress < 100) {
			item.status = 'uploading';
		} else if (progress === 100) {
			item.status = 'completed';
		}

		// Trigger reactivity by reassigning the array
		this.items = [...this.items];
	}

	/**
	 * Mark an upload as completed
	 */
	setCompleted(id: string): void {
		const item = this.items.find((item) => item.id === id);
		if (item) {
			item.progress = 100;
			item.status = 'completed';
			// Trigger reactivity
			this.items = [...this.items];
		}
	}

	/**
	 * Mark an upload as failed
	 */
	setFailed(id: string, error: string): void {
		const item = this.items.find((item) => item.id === id);
		if (item) {
			// Preserve existing progress (don't reset to 0)
			item.status = 'failed';
			item.error = error;
			// Trigger reactivity
			this.items = [...this.items];
		}
	}

	/**
	 * Clear all upload items
	 */
	clear(): void {
		this.items = [];
		this.uploading = false;
	}

	/**
	 * Set the uploading state
	 */
	setUploading(uploading: boolean): void {
		this.uploading = uploading;
	}

	/**
	 * Reset the store to initial state
	 */
	reset(): void {
		this.clear();
	}
}

// Export singleton instance
export const uploadStore = new UploadStore();