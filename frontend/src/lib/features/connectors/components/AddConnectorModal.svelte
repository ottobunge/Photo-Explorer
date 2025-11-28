<script lang="ts">
	import Modal from '$lib/shared/components/Modal.svelte';
	import { createEventDispatcher } from 'svelte';
	import { settingsStore } from '$lib/features/settings';
	import type { LocalFolderConfig } from '$lib/features/settings/types';

	const dispatch = createEventDispatcher<{ close: void }>();

	let connecting = false;
	let error: string | null = null;
	let selectedType: 'google_photos' | 'local' | null = null;
	let localFolderPath = '';
	let localFolderName = '';
	let recursive = true;

	async function handleGooglePhotos() {
		connecting = true;
		error = null;

		try {
			const authUrl = await settingsStore.connectGooglePhotos();
			// Redirect to Google OAuth
			window.location.href = authUrl;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to connect to Google Photos';
			connecting = false;
		}
	}

	async function handleCreateLocal() {
		if (!localFolderPath.trim()) {
			error = 'Please enter a folder path';
			return;
		}

		connecting = true;
		error = null;

		try {
			const config: LocalFolderConfig = {
				type: 'local',
				path: localFolderPath,
				recursive,
				watch: false,
				autoAlbum: false
			};
			if (localFolderName) {
				config.name = localFolderName;
			}
			await settingsStore.addLocalFolder(config);
			dispatch('close');
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to create local connector';
			connecting = false;
		}
	}

	function handleBack() {
		selectedType = null;
		error = null;
	}
</script>

<Modal title={selectedType ? 'Add Connector' : 'Choose Connector Type'} on:close>
	{#if !selectedType}
		<!-- Type selection -->
		<div class="connector-types">
			<button class="connector-type-card" on:click={() => (selectedType = 'google_photos')}>
				<div class="icon">📷</div>
				<h3>Google Photos</h3>
				<p>Connect your Google Photos library for cloud photo management</p>
			</button>

			<button class="connector-type-card" on:click={() => (selectedType = 'local')}>
				<div class="icon">📁</div>
				<h3>Local Folder</h3>
				<p>Index photos from a folder on your computer</p>
			</button>
		</div>
	{:else if selectedType === 'google_photos'}
		<!-- Google Photos flow -->
		<div class="connector-form">
			<div class="info-box">
				<h4>How it works:</h4>
				<ul>
					<li>Connect your Google account to enable photo import</li>
					<li>Click "Import Photos" to select which photos to index</li>
					<li>Photos remain in your Google Photos library</li>
					<li>Only metadata and AI embeddings are stored locally</li>
				</ul>
			</div>

			{#if error}
				<div class="error-banner">{error}</div>
			{/if}

			<div class="button-group">
				<button class="btn-secondary" on:click={handleBack} disabled={connecting}>Back</button>
				<button class="btn-primary" on:click={handleGooglePhotos} disabled={connecting}>
					{#if connecting}
						<span class="spinner"></span>
						Connecting...
					{:else}
						Connect Google Photos
					{/if}
				</button>
			</div>
		</div>
	{:else if selectedType === 'local'}
		<!-- Local folder form -->
		<div class="connector-form">
			<div class="form-group">
				<label for="path">Folder Path *</label>
				<input
					id="path"
					type="text"
					bind:value={localFolderPath}
					placeholder="/home/user/Pictures"
					disabled={connecting}
				/>
			</div>

			<div class="form-group">
				<label for="name">Display Name</label>
				<input
					id="name"
					type="text"
					bind:value={localFolderName}
					placeholder="My Photos (optional)"
					disabled={connecting}
				/>
			</div>

			<div class="form-group">
				<label class="checkbox-label">
					<input type="checkbox" bind:checked={recursive} disabled={connecting} />
					<span>Scan subfolders recursively</span>
				</label>
			</div>

			{#if error}
				<div class="error-banner">{error}</div>
			{/if}

			<div class="button-group">
				<button class="btn-secondary" on:click={handleBack} disabled={connecting}>Back</button>
				<button class="btn-primary" on:click={handleCreateLocal} disabled={connecting}>
					{#if connecting}
						<span class="spinner"></span>
						Creating...
					{:else}
						Create Connector
					{/if}
				</button>
			</div>
		</div>
	{/if}
</Modal>

<style>
	.connector-types {
		display: grid;
		gap: 1rem;
		margin-bottom: 1rem;
	}

	.connector-type-card {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 2rem;
		border: 2px solid #e5e7eb;
		border-radius: 12px;
		background: white;
		cursor: pointer;
		transition: all 0.2s;
		text-align: center;
	}

	.connector-type-card:hover {
		border-color: #3b82f6;
		background: #f0f9ff;
		transform: translateY(-2px);
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
	}

	.connector-type-card .icon {
		font-size: 3rem;
		margin-bottom: 1rem;
	}

	.connector-type-card h3 {
		margin: 0 0 0.5rem;
		font-size: 1.25rem;
		font-weight: 600;
		color: #1f2937;
	}

	.connector-type-card p {
		margin: 0;
		font-size: 0.875rem;
		color: #6b7280;
	}

	.connector-form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.info-box {
		background: #f0f9ff;
		border: 1px solid #bfdbfe;
		border-radius: 8px;
		padding: 1rem;
	}

	.info-box h4 {
		margin: 0 0 0.5rem;
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e40af;
	}

	.info-box ul {
		margin: 0;
		padding-left: 1.25rem;
		font-size: 0.875rem;
		color: #1e40af;
	}

	.info-box li {
		margin-bottom: 0.25rem;
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.form-group label {
		font-size: 0.875rem;
		font-weight: 500;
		color: #374151;
	}

	.form-group input[type='text'] {
		padding: 0.625rem;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.875rem;
	}

	.form-group input[type='text']:focus {
		outline: none;
		border-color: #3b82f6;
		ring: 2px solid #dbeafe;
	}

	.form-group input[type='text']:disabled {
		background: #f9fafb;
		cursor: not-allowed;
	}

	.checkbox-label {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		cursor: pointer;
	}

	.checkbox-label input[type='checkbox'] {
		width: 1rem;
		height: 1rem;
		cursor: pointer;
	}

	.checkbox-label span {
		font-size: 0.875rem;
		color: #374151;
	}

	.error-banner {
		background: #fef2f2;
		border: 1px solid #fecaca;
		border-radius: 6px;
		padding: 0.75rem;
		color: #dc2626;
		font-size: 0.875rem;
	}

	.button-group {
		display: flex;
		gap: 0.75rem;
		justify-content: flex-end;
		margin-top: 0.5rem;
	}

	.btn-primary,
	.btn-secondary {
		padding: 0.625rem 1.25rem;
		border-radius: 6px;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s;
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
	}

	.btn-primary {
		background: #3b82f6;
		color: white;
		border: none;
	}

	.btn-primary:hover:not(:disabled) {
		background: #2563eb;
	}

	.btn-primary:disabled {
		opacity: 0.7;
		cursor: not-allowed;
	}

	.btn-secondary {
		background: white;
		color: #374151;
		border: 1px solid #d1d5db;
	}

	.btn-secondary:hover:not(:disabled) {
		background: #f9fafb;
	}

	.btn-secondary:disabled {
		opacity: 0.7;
		cursor: not-allowed;
	}

	.spinner {
		width: 16px;
		height: 16px;
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
