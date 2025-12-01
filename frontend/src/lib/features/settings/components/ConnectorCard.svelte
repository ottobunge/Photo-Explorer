<script lang="ts">
	import type { Connector, PickerSession } from '../types';
	import { isLocalFolderConfig } from '../types';
	import { settingsStore } from '../stores/settings.svelte';
	import { onDestroy } from 'svelte';
	import { StatusBadge } from '$lib/shared/components';
	import type { StatusType } from '$lib/shared/components/StatusBadge.svelte';
	import {
		MESSAGE_DISMISS_TIMEOUT,
		PICKER_CLOSE_DELAY,
		PICKER_POLL_INTERVAL_FALLBACK,
		PICKER_WINDOW_WIDTH,
		PICKER_WINDOW_HEIGHT
	} from '$lib/constants';

	interface Props {
		connector: Connector;
		onsync?: (data: { id: string }) => void;
		onremove?: (data: { id: string }) => void;
	}

	const { connector, onsync, onremove }: Props = $props();

	let syncing = $state(false);
	let reprocessing = $state(false);
	let reprocessMessage = $state<string | null>(null);
	let reprocessMessageTimeout: ReturnType<typeof setTimeout> | null = null;

	// Picker state
	let pickerSession: PickerSession | null = null;
	let pickerWindow: Window | null = null;
	let pickerPolling = false;
	let pickerStatus = $state<'idle' | 'selecting' | 'importing' | 'done' | 'error'>('idle');
	let pickerMessage = $state<string | null>(null);
	let pickerResetTimeout: ReturnType<typeof setTimeout> | null = null;

	// Cleanup on destroy
	onDestroy(() => {
		// Clear all timeouts
		if (reprocessMessageTimeout !== null) {
			clearTimeout(reprocessMessageTimeout);
		}
		if (pickerResetTimeout !== null) {
			clearTimeout(pickerResetTimeout);
		}

		// Close picker window if open
		if (pickerWindow && !pickerWindow.closed) {
			pickerWindow.close();
		}
		pickerWindow = null;

		// Stop polling
		pickerPolling = false;
	});

	// Map connector status to StatusBadge status type
	// All ConnectorStatus values are valid StatusType values
	const status = $derived((): StatusType => {
		const connectorStatus = connector.status;
		// Explicit mapping without type casting
		switch (connectorStatus) {
			case 'connected':
				return 'connected';
			case 'disconnected':
				return 'disconnected';
			case 'syncing':
				return 'syncing';
			case 'error':
				return 'error';
			default:
				return 'info'; // fallback for any unexpected status
		}
	});
	const statusLabel = $derived(connector.status === 'syncing' ? 'Syncing...' : connector.status.charAt(0).toUpperCase() + connector.status.slice(1));

	function getConnectorIcon(type: string): string {
		switch (type) {
			case 'google_photos':
				return '📷';
			case 'local':
				return '📁';
			default:
				return '🔗';
		}
	}

	async function handleToggle(): Promise<void> {
		await settingsStore.toggleConnector(connector.id, !connector.enabled);
	}

	async function handleSync(): Promise<void> {
		syncing = true;
		try {
			await settingsStore.triggerSync(connector.id);
			onsync?.({ id: connector.id });
		} finally {
			syncing = false;
		}
	}

	function handleRemove(): void {
		onremove?.({ id: connector.id });
	}

	async function handleReprocess(): Promise<void> {
		reprocessing = true;
		reprocessMessage = 'Starting reprocess...';
		try {
			const result = await settingsStore.reprocessConnector(connector.id);
			reprocessMessage = result.message;
			// Clear message after timeout
			if (reprocessMessageTimeout !== null) {
				clearTimeout(reprocessMessageTimeout);
			}
			reprocessMessageTimeout = setTimeout(() => {
				reprocessMessage = null;
				reprocessMessageTimeout = null;
			}, MESSAGE_DISMISS_TIMEOUT);
		} catch (err) {
			reprocessMessage = err instanceof Error ? err.message : 'Reprocess failed';
		} finally {
			reprocessing = false;
		}
	}

	function formatDate(dateStr: string | null): string {
		if (!dateStr) {return 'Never';}
		return new Date(dateStr).toLocaleString();
	}

	// Google Photos Picker functions
	async function handleImportPhotos(): Promise<void> {
		if (connector.type !== 'google_photos') {return;}

		pickerStatus = 'selecting';
		pickerMessage = 'Opening photo picker...';

		try {
			// Create a new picker session
			pickerSession = await settingsStore.createPickerSession(connector.id);

			// Open the picker in a popup window
			const left = window.screenX + (window.outerWidth - PICKER_WINDOW_WIDTH) / 2;
			const top = window.screenY + (window.outerHeight - PICKER_WINDOW_HEIGHT) / 2;

			pickerWindow = window.open(
				pickerSession.pickerUri,
				'GooglePhotosPicker',
				`width=${PICKER_WINDOW_WIDTH},height=${PICKER_WINDOW_HEIGHT},left=${left},top=${top},menubar=no,toolbar=no,location=no,status=no`
			);

			if (!pickerWindow) {
				throw new Error('Popup blocked. Please allow popups for this site.');
			}

			pickerMessage = 'Select photos in the picker window...';

			// Start polling for session status
			startPolling();
		} catch (err) {
			pickerStatus = 'error';
			pickerMessage = err instanceof Error ? err.message : 'Failed to open picker';
		}
	}

	function startPolling(): void {
		if (!pickerSession || pickerPolling) {return;}

		pickerPolling = true;
		const pollInterval = (pickerSession.pollIntervalSeconds || PICKER_POLL_INTERVAL_FALLBACK) * 1000;

		const poll = async (): Promise<void> => {
			if (!pickerSession || pickerStatus !== 'selecting') {
				pickerPolling = false;
				return;
			}

			// Check if popup was closed
			if (pickerWindow && pickerWindow.closed) {
				// Give more time for the Google API to register the selection
				await new Promise((resolve) => setTimeout(resolve, PICKER_CLOSE_DELAY));

				// Always try to import when popup closes - the API will return
				// 0 photos if nothing was selected, which is fine
				try {
					await importSelectedPhotos();
				} catch (err) {
					console.error('Import failed after popup closed:', err);
					pickerStatus = 'idle';
					pickerMessage = null;
				}

				pickerPolling = false;
				return;
			}

			try {
				const status = await settingsStore.getPickerSessionStatus(
					connector.id,
					pickerSession.sessionId
				);

				if (status.mediaItemsSet) {
					// User has finished selecting photos
					if (pickerWindow && !pickerWindow.closed) {
						pickerWindow.close();
					}
					await importSelectedPhotos();
					pickerPolling = false;
					return;
				}
			} catch (err) {
				console.error('Failed to poll picker status:', err);
			}

			// Continue polling
			setTimeout(() => void poll(), pollInterval);
		};

		void poll();
	}

	async function importSelectedPhotos(): Promise<void> {
		if (!pickerSession) {return;}

		pickerStatus = 'importing';
		pickerMessage = 'Importing selected photos...';

		try {
			const result = await settingsStore.importPickerPhotos(
				connector.id,
				pickerSession.sessionId
			);

			pickerStatus = 'done';
			pickerMessage = result.message;

			// Note: Don't delete the session here - the worker task needs it
			// to fetch the photos. The worker will delete it when done.
			pickerSession = null;
			pickerWindow = null;

			// Reset after a delay
			if (pickerResetTimeout !== null) {
				clearTimeout(pickerResetTimeout);
			}
			pickerResetTimeout = setTimeout(() => {
				pickerStatus = 'idle';
				pickerMessage = null;
				pickerResetTimeout = null;
			}, MESSAGE_DISMISS_TIMEOUT);
		} catch (err) {
			pickerStatus = 'error';
			pickerMessage = err instanceof Error ? err.message : 'Import failed';
		}
	}

	async function cleanupSession(): Promise<void> {
		if (!pickerSession) {return;}

		try {
			await settingsStore.deletePickerSession(connector.id, pickerSession.sessionId);
		} catch {
			// Ignore cleanup errors
		}

		pickerSession = null;
		pickerWindow = null;
	}

	function cancelPicker(): void {
		if (pickerWindow && !pickerWindow.closed) {
			pickerWindow.close();
		}

		pickerStatus = 'idle';
		pickerMessage = null;
		pickerPolling = false;

		void cleanupSession();
	}
</script>

<div class="connector-card" class:disabled={!connector.enabled}>
	<div class="connector-header">
		<span class="connector-icon">{getConnectorIcon(connector.type)}</span>
		<div class="connector-info">
			<h3 class="connector-name">{connector.name}</h3>
			<p class="connector-type">{connector.type === 'google_photos' ? 'Google Photos' : 'Local Folder'}</p>
		</div>
		<StatusBadge {status} label={statusLabel} />
	</div>

	{#if connector.type === 'local' && isLocalFolderConfig(connector.config)}
		<div class="connector-details">
			<p class="detail-item">
				<span class="detail-label">Path:</span>
				<code class="detail-value">{connector.config.path}</code>
			</p>
		</div>
	{/if}

	{#if connector.errorMessage}
		<div class="connector-error">
			<span class="error-icon">⚠️</span>
			<span class="error-message">{connector.errorMessage}</span>
		</div>
	{/if}

	<div class="connector-meta">
		<span class="meta-item">Last sync: {formatDate(connector.lastSync)}</span>
	</div>

	<!-- Picker Status Banner -->
	{#if pickerStatus !== 'idle' && pickerMessage}
		<div class="picker-status" class:selecting={pickerStatus === 'selecting'} class:importing={pickerStatus === 'importing'} class:done={pickerStatus === 'done'} class:error={pickerStatus === 'error'}>
			<div class="picker-status-content">
				{#if pickerStatus === 'selecting' || pickerStatus === 'importing'}
					<span class="picker-spinner"></span>
				{:else if pickerStatus === 'done'}
					<span class="picker-icon">✓</span>
				{:else if pickerStatus === 'error'}
					<span class="picker-icon">⚠️</span>
				{/if}
				<span class="picker-message">{pickerMessage}</span>
			</div>
			{#if pickerStatus === 'selecting'}
				<button class="picker-cancel-btn" onclick={cancelPicker}>Cancel</button>
			{/if}
		</div>
	{/if}

	<!-- Reprocess Status Banner -->
	{#if reprocessMessage}
		<div class="reprocess-status" class:processing={reprocessing}>
			<div class="reprocess-status-content">
				{#if reprocessing}
					<span class="picker-spinner"></span>
				{:else}
					<span class="picker-icon">✓</span>
				{/if}
				<span class="picker-message">{reprocessMessage}</span>
			</div>
		</div>
	{/if}

	<div class="connector-actions">
		<label class="toggle-switch">
			<input type="checkbox" checked={connector.enabled} onchange={() => void handleToggle()} />
			<span class="toggle-slider"></span>
		</label>

		{#if connector.type === 'google_photos'}
			<button
				class="action-btn import-btn"
				onclick={handleImportPhotos}
				disabled={!connector.enabled || pickerStatus !== 'idle'}
			>
				{#if pickerStatus === 'selecting'}
					<span class="spinner"></span>
					Selecting...
				{:else if pickerStatus === 'importing'}
					<span class="spinner"></span>
					Importing...
				{:else}
					📥 Import Photos
				{/if}
			</button>
			<button
				class="action-btn reprocess-btn"
				onclick={handleReprocess}
				disabled={!connector.enabled || reprocessing}
				title="Regenerate embeddings for semantic search"
			>
				{#if reprocessing}
					<span class="spinner"></span>
					Processing...
				{:else}
					🔄 Reprocess
				{/if}
			</button>
		{:else}
			<button
				class="action-btn sync-btn"
				onclick={handleSync}
				disabled={syncing || connector.status === 'syncing' || !connector.enabled}
			>
				{#if syncing || connector.status === 'syncing'}
					<span class="spinner"></span>
					Syncing...
				{:else}
					🔄 Sync Now
				{/if}
			</button>
		{/if}

		<button class="action-btn remove-btn" onclick={handleRemove}>
			🗑️ Remove
		</button>
	</div>
</div>

<style>
	.connector-card {
		background: var(--card-bg, #ffffff);
		border: 1px solid var(--border-color, #e5e7eb);
		border-radius: 8px;
		padding: 1rem;
		margin-bottom: 1rem;
		transition: opacity 0.2s;
	}

	.connector-card.disabled {
		opacity: 0.6;
	}

	.connector-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 0.75rem;
	}

	.connector-icon {
		font-size: 1.5rem;
	}

	.connector-info {
		flex: 1;
	}

	.connector-name {
		font-weight: 600;
		margin: 0;
		font-size: 1rem;
	}

	.connector-type {
		color: var(--text-muted, #6b7280);
		font-size: 0.875rem;
		margin: 0;
	}

	.connector-details {
		background: var(--bg-secondary, #f9fafb);
		border-radius: 4px;
		padding: 0.5rem 0.75rem;
		margin-bottom: 0.75rem;
	}

	.detail-item {
		margin: 0;
		font-size: 0.875rem;
	}

	.detail-label {
		color: var(--text-muted, #6b7280);
	}

	.detail-value {
		font-family: monospace;
		background: var(--bg-tertiary, #f3f4f6);
		padding: 0.125rem 0.375rem;
		border-radius: 3px;
	}

	.connector-error {
		background: var(--error-bg, #fef2f2);
		border: 1px solid var(--error-border, #fecaca);
		border-radius: 4px;
		padding: 0.5rem 0.75rem;
		margin-bottom: 0.75rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.error-message {
		font-size: 0.875rem;
		color: var(--error-text, #dc2626);
	}

	.connector-meta {
		font-size: 0.75rem;
		color: var(--text-muted, #9ca3af);
		margin-bottom: 0.75rem;
	}

	.connector-actions {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding-top: 0.75rem;
		border-top: 1px solid var(--border-color, #e5e7eb);
	}

	.toggle-switch {
		position: relative;
		display: inline-block;
		width: 44px;
		height: 24px;
	}

	.toggle-switch input {
		opacity: 0;
		width: 0;
		height: 0;
	}

	.toggle-slider {
		position: absolute;
		cursor: pointer;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background-color: var(--toggle-off, #ccc);
		transition: 0.3s;
		border-radius: 24px;
	}

	.toggle-slider:before {
		position: absolute;
		content: '';
		height: 18px;
		width: 18px;
		left: 3px;
		bottom: 3px;
		background-color: white;
		transition: 0.3s;
		border-radius: 50%;
	}

	.toggle-switch input:checked + .toggle-slider {
		background-color: var(--primary, #3b82f6);
	}

	.toggle-switch input:checked + .toggle-slider:before {
		transform: translateX(20px);
	}

	.action-btn {
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--border-color, #e5e7eb);
		border-radius: 6px;
		background: var(--btn-bg, #ffffff);
		cursor: pointer;
		font-size: 0.875rem;
		display: flex;
		align-items: center;
		gap: 0.25rem;
		transition: background 0.2s;
	}

	.action-btn:hover:not(:disabled) {
		background: var(--btn-hover, #f9fafb);
	}

	.action-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.remove-btn {
		margin-left: auto;
		color: var(--error-text, #dc2626);
		border-color: var(--error-border, #fecaca);
	}

	.remove-btn:hover:not(:disabled) {
		background: var(--error-bg, #fef2f2);
	}

	.spinner {
		width: 14px;
		height: 14px;
		border: 2px solid var(--border-color, #e5e7eb);
		border-top-color: var(--primary, #3b82f6);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Picker Status */
	.picker-status {
		background: var(--info-bg, #eff6ff);
		border: 1px solid var(--info-border, #bfdbfe);
		border-radius: 6px;
		padding: 0.625rem 0.875rem;
		margin-bottom: 0.75rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
	}

	.picker-status.selecting {
		background: var(--info-bg, #eff6ff);
		border-color: var(--info-border, #bfdbfe);
	}

	.picker-status.importing {
		background: var(--warning-bg, #fffbeb);
		border-color: var(--warning-border, #fde68a);
	}

	.picker-status.done {
		background: var(--success-bg, #ecfdf5);
		border-color: var(--success-border, #a7f3d0);
	}

	.picker-status.error {
		background: var(--error-bg, #fef2f2);
		border-color: var(--error-border, #fecaca);
	}

	.picker-status-content {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.picker-spinner {
		width: 16px;
		height: 16px;
		border: 2px solid var(--primary-light, #93c5fd);
		border-top-color: var(--primary, #3b82f6);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	.picker-icon {
		font-size: 1rem;
	}

	.picker-message {
		font-size: 0.875rem;
		color: var(--text-secondary, #4b5563);
	}

	.picker-cancel-btn {
		padding: 0.25rem 0.625rem;
		font-size: 0.75rem;
		background: transparent;
		border: 1px solid var(--border-color, #d1d5db);
		border-radius: 4px;
		cursor: pointer;
		color: var(--text-muted, #6b7280);
	}

	.picker-cancel-btn:hover {
		background: var(--bg-secondary, #f3f4f6);
	}

	/* Import Button */
	.import-btn {
		background: var(--success-light, #d1fae5);
		border-color: var(--success-border, #a7f3d0);
		color: var(--success-text, #065f46);
	}

	.import-btn:hover:not(:disabled) {
		background: var(--success-hover, #a7f3d0);
	}

	/* Reprocess Button */
	.reprocess-btn {
		background: var(--warning-light, #fef3c7);
		border-color: var(--warning-border, #fde68a);
		color: var(--warning-text, #92400e);
	}

	.reprocess-btn:hover:not(:disabled) {
		background: var(--warning-hover, #fde68a);
	}

	/* Reprocess Status */
	.reprocess-status {
		background: var(--info-bg, #eff6ff);
		border: 1px solid var(--info-border, #bfdbfe);
		border-radius: 6px;
		padding: 0.625rem 0.875rem;
		margin-bottom: 0.75rem;
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.reprocess-status.processing {
		background: var(--warning-bg, #fffbeb);
		border-color: var(--warning-border, #fde68a);
	}

	.reprocess-status-content {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
</style>
