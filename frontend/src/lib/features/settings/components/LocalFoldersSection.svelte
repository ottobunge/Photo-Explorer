<script lang="ts">
	import { settingsStore } from '../stores/settings.svelte';

	// Derived value for local connectors
	const localConnectors = $derived(settingsStore.connectors.filter((c) => c.type === 'local'));
	import ConnectorCard from './ConnectorCard.svelte';
	import type { LocalFolderConfig } from '../types';

	let showAddModal = $state(false);
	let error = $state<string | null>(null);

	// Form state
	let folderPath = $state('');
	let folderName = $state('');
	let recursive = $state(true);
	let watch = $state(true);
	let autoAlbum = $state(false);
	let adding = $state(false);

	function openAddModal(): void {
		folderPath = '';
		folderName = '';
		recursive = true;
		watch = true;
		autoAlbum = false;
		showAddModal = true;
	}

	function closeAddModal(): void {
		showAddModal = false;
	}

	async function handleAddFolder(): Promise<void> {
		if (!folderPath.trim()) {
			error = 'Please enter a folder path';
			return;
		}

		adding = true;
		error = null;

		try {
			const config: LocalFolderConfig = {
				type: 'local',
				path: folderPath.trim(),
				recursive,
				watch,
				autoAlbum
			};

			const trimmedName = folderName.trim();
			if (trimmedName) {
				config.name = trimmedName;
			}

			await settingsStore.addLocalFolder(config);
			closeAddModal();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to add folder';
		} finally {
			adding = false;
		}
	}

	async function handleRemove(event: CustomEvent<{ id: string }>): Promise<void> {
		if (!confirm('Remove this folder from Photo Explorer?\n\nWARNING: All indexed photos and their data (embeddings, face detections, etc.) will be permanently deleted from Photo Explorer. Your original files on disk will not be affected.')) {
			return;
		}

		try {
			await settingsStore.removeConnector(event.detail.id);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to remove folder';
		}
	}
</script>

<section class="settings-section">
	<div class="section-header">
		<div class="header-row">
			<h2 class="section-title">
				<span class="section-icon">📁</span>
				Local Folders
			</h2>
			<button class="add-btn" onclick={openAddModal}>
				+ Add Folder
			</button>
		</div>
		<p class="section-description">
			Add local folders to index photos from your computer. Files stay where they are - only metadata and embeddings are indexed.
		</p>
	</div>

	{#if error}
		<div class="error-banner">
			<span class="error-icon">⚠️</span>
			<span>{error}</span>
			<button class="dismiss-btn" onclick={() => (error = null)}>×</button>
		</div>
	{/if}

	{#if localConnectors.length > 0}
		<div class="connectors-list">
			{#each localConnectors as connector (connector.id)}
				<ConnectorCard {connector} on:remove={handleRemove} />
			{/each}
		</div>
	{:else}
		<div class="empty-state">
			<div class="empty-icon">📂</div>
			<p class="empty-text">No folders configured for indexing</p>
			<button class="add-folder-btn" onclick={openAddModal}>
				+ Add Your First Folder
			</button>
		</div>
	{/if}
</section>

<!-- Add Folder Modal -->
{#if showAddModal}
	<div class="modal-overlay" onclick={closeAddModal} onkeydown={(e) => e.key === 'Escape' && closeAddModal()} role="button" tabindex="0">
		<div class="modal" onclick={(e) => { e.stopPropagation(); }} onkeydown={(e) => { e.stopPropagation(); }} role="dialog" aria-modal="true" aria-labelledby="modal-title" tabindex="-1">
			<div class="modal-header">
				<h3 id="modal-title">Add Local Folder</h3>
				<button class="close-btn" onclick={closeAddModal} aria-label="Close modal">×</button>
			</div>

			<form onsubmit={(e) => { e.preventDefault(); handleAddFolder(); }}>
				<div class="form-group">
					<label for="folder-path">Folder Path</label>
					<input
						id="folder-path"
						type="text"
						bind:value={folderPath}
						placeholder="/home/user/Photos"
						required
					/>
					<p class="form-hint">Enter the full path to the folder containing your photos</p>
				</div>

				<div class="form-group">
					<label for="folder-name">Display Name (optional)</label>
					<input
						id="folder-name"
						type="text"
						bind:value={folderName}
						placeholder="My Photos"
					/>
				</div>

				<div class="form-group">
					<label class="checkbox-label">
						<input type="checkbox" bind:checked={recursive} />
						<span>Include subfolders</span>
					</label>
				</div>

				<div class="form-group">
					<label class="checkbox-label">
						<input type="checkbox" bind:checked={watch} />
						<span>Watch for changes</span>
					</label>
					<p class="form-hint">Automatically detect new and modified files</p>
				</div>

				<div class="form-group">
					<label class="checkbox-label">
						<input type="checkbox" bind:checked={autoAlbum} />
						<span>Create albums from folders</span>
					</label>
					<p class="form-hint">Automatically create albums based on folder structure</p>
				</div>

				<div class="modal-actions">
					<button type="button" class="cancel-btn" onclick={closeAddModal}>
						Cancel
					</button>
					<button type="submit" class="submit-btn" disabled={adding}>
						{#if adding}
							<span class="spinner"></span>
							Adding...
						{:else}
							Add Folder
						{/if}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}

<style>
	.settings-section {
		background: var(--card-bg, #ffffff);
		border: 1px solid var(--border-color, #e5e7eb);
		border-radius: 12px;
		padding: 1.5rem;
		margin-bottom: 1.5rem;
	}

	.section-header {
		margin-bottom: 1.5rem;
	}

	.header-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.section-title {
		font-size: 1.25rem;
		font-weight: 600;
		margin: 0;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.section-icon {
		font-size: 1.5rem;
	}

	.section-description {
		color: var(--text-muted, #6b7280);
		margin: 0;
		font-size: 0.9375rem;
	}

	.add-btn {
		padding: 0.5rem 1rem;
		background: var(--primary, #3b82f6);
		color: white;
		border: none;
		border-radius: 6px;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
	}

	.add-btn:hover {
		background: var(--primary-dark, #2563eb);
	}

	.error-banner {
		background: var(--error-bg, #fef2f2);
		border: 1px solid var(--error-border, #fecaca);
		border-radius: 8px;
		padding: 0.75rem 1rem;
		margin-bottom: 1rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--error-text, #dc2626);
	}

	.dismiss-btn {
		margin-left: auto;
		background: none;
		border: none;
		font-size: 1.25rem;
		cursor: pointer;
		padding: 0;
		line-height: 1;
		color: inherit;
	}

	.empty-state {
		text-align: center;
		padding: 2rem;
		background: var(--bg-secondary, #f9fafb);
		border-radius: 8px;
	}

	.empty-icon {
		font-size: 2.5rem;
		margin-bottom: 0.75rem;
	}

	.empty-text {
		color: var(--text-muted, #6b7280);
		margin: 0 0 1rem;
	}

	.add-folder-btn {
		padding: 0.75rem 1.5rem;
		background: var(--primary, #3b82f6);
		color: white;
		border: none;
		border-radius: 8px;
		font-size: 1rem;
		font-weight: 500;
		cursor: pointer;
	}

	.add-folder-btn:hover {
		background: var(--primary-dark, #2563eb);
	}

	/* Modal styles */
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}

	.modal {
		background: var(--card-bg, #ffffff);
		border-radius: 12px;
		width: 100%;
		max-width: 480px;
		max-height: 90vh;
		overflow-y: auto;
	}

	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1.25rem 1.5rem;
		border-bottom: 1px solid var(--border-color, #e5e7eb);
	}

	.modal-header h3 {
		margin: 0;
		font-size: 1.125rem;
		font-weight: 600;
	}

	.close-btn {
		background: none;
		border: none;
		font-size: 1.5rem;
		cursor: pointer;
		padding: 0;
		line-height: 1;
		color: var(--text-muted, #6b7280);
	}

	.close-btn:hover {
		color: var(--text-primary, #111827);
	}

	form {
		padding: 1.5rem;
	}

	.form-group {
		margin-bottom: 1.25rem;
	}

	.form-group label {
		display: block;
		font-weight: 500;
		margin-bottom: 0.5rem;
		font-size: 0.875rem;
	}

	.form-group input[type='text'] {
		width: 100%;
		padding: 0.625rem 0.75rem;
		border: 1px solid var(--border-color, #e5e7eb);
		border-radius: 6px;
		font-size: 0.9375rem;
	}

	.form-group input[type='text']:focus {
		outline: none;
		border-color: var(--primary, #3b82f6);
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
	}

	.form-hint {
		margin: 0.375rem 0 0;
		font-size: 0.75rem;
		color: var(--text-muted, #9ca3af);
	}

	.checkbox-label {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		cursor: pointer;
		font-weight: normal !important;
	}

	.checkbox-label input[type='checkbox'] {
		width: 16px;
		height: 16px;
		cursor: pointer;
	}

	.modal-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		padding-top: 1rem;
		border-top: 1px solid var(--border-color, #e5e7eb);
	}

	.cancel-btn {
		padding: 0.625rem 1rem;
		background: var(--bg-secondary, #f9fafb);
		border: 1px solid var(--border-color, #e5e7eb);
		border-radius: 6px;
		font-size: 0.875rem;
		cursor: pointer;
	}

	.cancel-btn:hover {
		background: var(--bg-tertiary, #f3f4f6);
	}

	.submit-btn {
		padding: 0.625rem 1rem;
		background: var(--primary, #3b82f6);
		color: white;
		border: none;
		border-radius: 6px;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.submit-btn:hover:not(:disabled) {
		background: var(--primary-dark, #2563eb);
	}

	.submit-btn:disabled {
		opacity: 0.7;
		cursor: not-allowed;
	}

	.spinner {
		width: 14px;
		height: 14px;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top-color: white;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
