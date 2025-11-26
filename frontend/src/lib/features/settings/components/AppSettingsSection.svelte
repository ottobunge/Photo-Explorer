<script lang="ts">
	import { settingsStore } from '../stores/settings';
	import { onMount } from 'svelte';
	import { STATUS_MESSAGE_TIMEOUT, DEFAULT_THUMBNAIL_QUALITY } from '$lib/constants';

	let saving = false;
	let error: string | null = null;
	let successMessage: string | null = null;

	// Local form state
	let thumbnailQuality = $state(DEFAULT_THUMBNAIL_QUALITY);
	let clipModel = $state('ViT-B/32');
	let faceDetectionEnabled = $state(true);
	let autoIndexNewPhotos = $state(true);

	const clipModels = [
		{ value: 'ViT-B/32', label: 'ViT-B/32 (Fast, Good Quality)' },
		{ value: 'ViT-B/16', label: 'ViT-B/16 (Balanced)' },
		{ value: 'ViT-L/14', label: 'ViT-L/14 (Best Quality, Slower)' }
	];

	// Load settings on mount
	onMount(async () => {
		await settingsStore.loadSettings();
	});

	// Sync form state with store when settings change
	$effect(() => {
		if (settingsStore.appSettings) {
			thumbnailQuality = settingsStore.appSettings.thumbnailQuality;
			clipModel = settingsStore.appSettings.clipModel;
			faceDetectionEnabled = settingsStore.appSettings.faceDetectionEnabled;
			autoIndexNewPhotos = settingsStore.appSettings.autoIndexNewPhotos;
		}
	});

	async function handleSave() {
		saving = true;
		error = null;
		successMessage = null;

		try {
			await settingsStore.updateSettings({
				thumbnailQuality,
				clipModel,
				faceDetectionEnabled,
				autoIndexNewPhotos
			});
			successMessage = 'Settings saved successfully';
			setTimeout(() => (successMessage = null), STATUS_MESSAGE_TIMEOUT);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save settings';
		} finally {
			saving = false;
		}
	}

	function hasChanges(): boolean {
		if (!settingsStore.appSettings) return false;
		return (
			thumbnailQuality !== settingsStore.appSettings.thumbnailQuality ||
			clipModel !== settingsStore.appSettings.clipModel ||
			faceDetectionEnabled !== settingsStore.appSettings.faceDetectionEnabled ||
			autoIndexNewPhotos !== settingsStore.appSettings.autoIndexNewPhotos
		);
	}
</script>

<section class="settings-section">
	<div class="section-header">
		<h2 class="section-title">
			<span class="section-icon">⚙️</span>
			Application Settings
		</h2>
		<p class="section-description">
			Configure how Photo Explorer processes and indexes your photos.
		</p>
	</div>

	{#if error}
		<div class="error-banner">
			<span class="error-icon">⚠️</span>
			<span>{error}</span>
			<button class="dismiss-btn" on:click={() => (error = null)}>×</button>
		</div>
	{/if}

	{#if successMessage}
		<div class="success-banner">
			<span class="success-icon">✓</span>
			<span>{successMessage}</span>
		</div>
	{/if}

	<form on:submit|preventDefault={handleSave}>
		<div class="settings-grid">
			<div class="form-group">
				<label for="thumbnail-quality">Thumbnail Quality</label>
				<div class="range-input">
					<input
						id="thumbnail-quality"
						type="range"
						min="50"
						max="100"
						step="5"
						bind:value={thumbnailQuality}
					/>
					<span class="range-value">{thumbnailQuality}%</span>
				</div>
				<p class="form-hint">Higher quality means larger thumbnail files</p>
			</div>

			<div class="form-group">
				<label for="clip-model">CLIP Model</label>
				<select id="clip-model" bind:value={clipModel}>
					{#each clipModels as model}
						<option value={model.value}>{model.label}</option>
					{/each}
				</select>
				<p class="form-hint">Used for semantic search and image understanding</p>
			</div>

			<div class="form-group">
				<label class="checkbox-label">
					<input type="checkbox" bind:checked={faceDetectionEnabled} />
					<span>Enable Face Detection</span>
				</label>
				<p class="form-hint">Automatically detect and group faces in photos</p>
			</div>

			<div class="form-group">
				<label class="checkbox-label">
					<input type="checkbox" bind:checked={autoIndexNewPhotos} />
					<span>Auto-index New Photos</span>
				</label>
				<p class="form-hint">Automatically process new photos when detected</p>
			</div>
		</div>

		<div class="form-actions">
			<button type="submit" class="save-btn" disabled={saving || !hasChanges()}>
				{#if saving}
					<span class="spinner"></span>
					Saving...
				{:else}
					Save Changes
				{/if}
			</button>
		</div>
	</form>
</section>

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

	.section-title {
		font-size: 1.25rem;
		font-weight: 600;
		margin: 0 0 0.5rem;
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

	.success-banner {
		background: var(--success-bg, #f0fdf4);
		border: 1px solid var(--success-border, #bbf7d0);
		border-radius: 8px;
		padding: 0.75rem 1rem;
		margin-bottom: 1rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--success-text, #16a34a);
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

	.settings-grid {
		display: grid;
		gap: 1.5rem;
	}

	.form-group {
		margin: 0;
	}

	.form-group > label {
		display: block;
		font-weight: 500;
		margin-bottom: 0.5rem;
		font-size: 0.875rem;
	}

	.form-group select {
		width: 100%;
		padding: 0.625rem 0.75rem;
		border: 1px solid var(--border-color, #e5e7eb);
		border-radius: 6px;
		font-size: 0.9375rem;
		background: var(--card-bg, #ffffff);
	}

	.form-group select:focus {
		outline: none;
		border-color: var(--primary, #3b82f6);
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
	}

	.range-input {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.range-input input[type='range'] {
		flex: 1;
		height: 6px;
		-webkit-appearance: none;
		background: var(--bg-tertiary, #e5e7eb);
		border-radius: 3px;
	}

	.range-input input[type='range']::-webkit-slider-thumb {
		-webkit-appearance: none;
		width: 18px;
		height: 18px;
		background: var(--primary, #3b82f6);
		border-radius: 50%;
		cursor: pointer;
	}

	.range-value {
		min-width: 3rem;
		text-align: right;
		font-weight: 500;
		font-size: 0.875rem;
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
		font-weight: 500 !important;
	}

	.checkbox-label input[type='checkbox'] {
		width: 16px;
		height: 16px;
		cursor: pointer;
	}

	.form-actions {
		margin-top: 1.5rem;
		padding-top: 1.5rem;
		border-top: 1px solid var(--border-color, #e5e7eb);
	}

	.save-btn {
		padding: 0.75rem 1.5rem;
		background: var(--primary, #3b82f6);
		color: white;
		border: none;
		border-radius: 8px;
		font-size: 1rem;
		font-weight: 500;
		cursor: pointer;
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
	}

	.save-btn:hover:not(:disabled) {
		background: var(--primary-dark, #2563eb);
	}

	.save-btn:disabled {
		opacity: 0.5;
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
