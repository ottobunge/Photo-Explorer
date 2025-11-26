<script lang="ts">
	import { settingsStore } from '../stores/settings';
	import { Card, EmptyState } from '$lib/shared/components';
	import ConnectorCard from './ConnectorCard.svelte';

	// Derived value for Google Photos connectors
	let googlePhotosConnectors = $derived(settingsStore.connectors.filter((c) => c.type === 'google_photos'));

	let error: string | null = null;

	async function handleConnect() {
		error = null;

		try {
			const authUrl = await settingsStore.connectGooglePhotos();
			// Redirect to Google OAuth (connecting state will persist during redirect)
			window.location.href = authUrl;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to connect to Google Photos';
		}
	}

	async function handleDisconnect() {
		if (!confirm('Are you sure you want to disconnect Google Photos? Your indexed photos will remain, but syncing will stop.')) {
			return;
		}

		try {
			await settingsStore.disconnectGooglePhotos();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to disconnect';
		}
	}

	async function handleRemove(event: CustomEvent<{ id: string }>) {
		if (!confirm('Remove this Google Photos connection?')) {
			return;
		}

		try {
			await settingsStore.removeConnector(event.detail.id);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to remove connector';
		}
	}
</script>

<section class="settings-section">
	<div class="section-header">
		<h2 class="section-title">
			<span class="section-icon">📷</span>
			Google Photos
		</h2>
		<p class="section-description">
			Connect your Google Photos library to index and search your cloud photos.
			Photos stay in Google Photos - only metadata and embeddings are stored locally.
		</p>
	</div>

	{#if error}
		<div class="error-banner">
			<span class="error-icon">⚠️</span>
			<span>{error}</span>
			<button class="dismiss-btn" on:click={() => (error = null)}>×</button>
		</div>
	{/if}

	{#if googlePhotosConnectors.length > 0}
		<div class="connectors-list">
			{#each googlePhotosConnectors as connector (connector.id)}
				<ConnectorCard {connector} on:remove={handleRemove} />
			{/each}
		</div>

		<button class="add-account-btn" on:click={handleConnect} disabled={settingsStore.connecting}>
			{#if settingsStore.connecting}
				<span class="spinner"></span>
				Connecting...
			{:else}
				+ Add Another Account
			{/if}
		</button>
	{:else}
		<EmptyState
			icon="🔗"
			title="No Google Photos account connected"
			description=""
		>
			{#snippet action()}
				<button class="connect-btn" on:click={handleConnect} disabled={settingsStore.connecting}>
					{#if settingsStore.connecting}
						<span class="spinner"></span>
						Connecting...
					{:else}
						<span class="google-icon">
							<svg viewBox="0 0 24 24" width="18" height="18">
								<path
									fill="#4285F4"
									d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
								/>
								<path
									fill="#34A853"
									d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
								/>
								<path
									fill="#FBBC05"
									d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
								/>
								<path
									fill="#EA4335"
									d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
								/>
							</svg>
						</span>
						Connect Google Photos
					{/if}
				</button>
			{/snippet}
		</EmptyState>
	{/if}

	<div class="section-info">
		<h4>How it works</h4>
		<ul>
			<li>Connect your Google account to enable photo import</li>
			<li>Click "Import Photos" to select which photos to index</li>
			<li>Photos remain in your Google Photos library</li>
			<li>Only metadata and AI embeddings are stored locally</li>
			<li>Images are fetched on-demand when viewing</li>
		</ul>
	</div>
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

	.connectors-list {
		margin-bottom: 1rem;
	}

	.add-account-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		width: 100%;
		padding: 0.625rem;
		background: var(--bg-secondary, #f9fafb);
		border: 1px dashed var(--border-color, #d1d5db);
		border-radius: 8px;
		font-size: 0.875rem;
		color: var(--text-muted, #6b7280);
		cursor: pointer;
		transition: all 0.2s;
		margin-bottom: 1rem;
	}

	.add-account-btn:hover:not(:disabled) {
		background: var(--bg-tertiary, #f3f4f6);
		border-color: var(--primary, #3b82f6);
		color: var(--primary, #3b82f6);
	}

	.add-account-btn:disabled {
		opacity: 0.7;
		cursor: not-allowed;
	}

	.connect-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1.5rem;
		background: var(--primary, #3b82f6);
		color: white;
		border: none;
		border-radius: 8px;
		font-size: 1rem;
		font-weight: 500;
		cursor: pointer;
		transition: background 0.2s;
	}

	.connect-btn:hover:not(:disabled) {
		background: var(--primary-dark, #2563eb);
	}

	.connect-btn:disabled {
		opacity: 0.7;
		cursor: not-allowed;
	}

	.google-icon {
		display: flex;
		align-items: center;
	}

	.section-info {
		background: var(--bg-secondary, #f9fafb);
		border-radius: 8px;
		padding: 1rem;
	}

	.section-info h4 {
		margin: 0 0 0.5rem;
		font-size: 0.875rem;
		font-weight: 600;
	}

	.section-info ul {
		margin: 0;
		padding-left: 1.25rem;
		font-size: 0.875rem;
		color: var(--text-muted, #6b7280);
	}

	.section-info li {
		margin-bottom: 0.25rem;
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
