<script lang="ts">
	import { onMount } from 'svelte';
	import { settingsStore } from '../stores/settings.svelte';
	import type { HFModel, DownloadProgress } from '../types';

	let searchQuery = '';
	let searchResults: HFModel[] = [];
	let searching = false;
	let error: string | null = null;

	// Model lookup modal
	let showLookupModal = false;
	let lookupModelId = '';
	let lookupResult: HFModel | null = null;
	let lookingUp = false;

	// Download tracking
	let downloadingModels = new Map<string, DownloadProgress>();

	onMount(async (): Promise<void> => {
		await Promise.all([
			settingsStore.loadActiveModels(),
			settingsStore.loadDownloadedModels(),
			settingsStore.loadRecommendedModels()
		]);
	});

	async function handleSearch(): Promise<void> {
		if (!searchQuery.trim()) {return;}

		searching = true;
		error = null;

		try {
			searchResults = await settingsStore.searchModels(searchQuery);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Search failed';
		} finally {
			searching = false;
		}
	}

	function openLookupModal(): void {
		lookupModelId = '';
		lookupResult = null;
		showLookupModal = true;
	}

	async function handleLookup(): Promise<void> {
		if (!lookupModelId.trim()) {return;}

		lookingUp = true;
		error = null;

		try {
			lookupResult = await settingsStore.getModelInfo(lookupModelId);
			if (!lookupResult) {
				error = `Model not found: ${lookupModelId}`;
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Lookup failed';
		} finally {
			lookingUp = false;
		}
	}

	async function downloadModel(modelId: string): Promise<void> {
		try {
			const progress = await settingsStore.downloadModel(modelId);
			downloadingModels.set(modelId, progress);
			downloadingModels = downloadingModels;

			// Poll for progress
			if (progress.status === 'downloading') {
				pollProgress(modelId);
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Download failed';
		}
	}

	function pollProgress(modelId: string): void {
		const interval = setInterval(() => {
			settingsStore.getDownloadProgress(modelId)
				.then((progress) => {
					downloadingModels.set(modelId, progress);
					downloadingModels = downloadingModels;

					if (progress.status === 'completed' || progress.status === 'failed') {
						clearInterval(interval);
						if (progress.status === 'completed') {
							void settingsStore.loadDownloadedModels();
						}
					}
				})
				.catch(() => {
					clearInterval(interval);
				});
		}, 2000);
	}

	async function deleteModel(modelId: string): Promise<void> {
		if (!confirm(`Delete downloaded model: ${modelId}?`)) {return;}

		try {
			await settingsStore.deleteModel(modelId);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Delete failed';
		}
	}

	function formatBytes(bytes: number): string {
		if (bytes === 0) {return '0 B';}
		const k = 1024;
		const sizes = ['B', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
	}

	function formatNumber(num: number): string {
		if (num >= 1000000) {return (num / 1000000).toFixed(1) + 'M';}
		if (num >= 1000) {return (num / 1000).toFixed(1) + 'K';}
		return num.toString();
	}

	function getModelStatus(modelId: string): 'downloaded' | 'downloading' | 'not_downloaded' {
		if (settingsStore.downloadedModels.includes(modelId)) {return 'downloaded';}
		if (downloadingModels.has(modelId)) {return 'downloading';}
		return 'not_downloaded';
	}

	function getProgress(modelId: string): DownloadProgress | undefined {
		return downloadingModels.get(modelId);
	}
</script>

{#snippet circularProgress(progress: number, size: number = 32)}
	{@const strokeWidth = 3}
	{@const radius = (size - strokeWidth) / 2}
	{@const circumference = 2 * Math.PI * radius}
	{@const offset = circumference - (progress / 100) * circumference}
	<div class="circular-progress" style="width: {size}px; height: {size}px;">
		<svg width={size} height={size}>
			<circle
				cx={size / 2}
				cy={size / 2}
				r={radius}
				fill="none"
				stroke="var(--border-color, #e5e7eb)"
				stroke-width={strokeWidth}
			/>
			<circle
				cx={size / 2}
				cy={size / 2}
				r={radius}
				fill="none"
				stroke="var(--primary, #3b82f6)"
				stroke-width={strokeWidth}
				stroke-linecap="round"
				stroke-dasharray={circumference}
				stroke-dashoffset={offset}
				transform="rotate(-90 {size / 2} {size / 2})"
				class="progress-circle"
			/>
		</svg>
		<span class="progress-text">{Math.round(progress)}%</span>
	</div>
{/snippet}

<section class="settings-section">
	<div class="section-header">
		<h2 class="section-title">
			<span class="section-icon">🤖</span>
			AI Models
		</h2>
		<p class="section-description">
			Configure AI models for image embeddings and face detection. Models are downloaded from Hugging Face.
		</p>
	</div>

	{#if error}
		<div class="error-banner">
			<span class="error-icon">⚠️</span>
			<span>{error}</span>
			<button class="dismiss-btn" on:click={() => (error = null)}>×</button>
		</div>
	{/if}

	<!-- Active Models -->
	{#if settingsStore.activeModels}
		<div class="active-models">
			<h3>Active Models</h3>
			<div class="model-cards">
				<div class="model-card">
					<div class="model-header">
						<span class="model-icon">🖼️</span>
						<div class="model-info">
							<h4>Image Embeddings (CLIP)</h4>
							<p>{settingsStore.activeModels.clip_model || 'Not configured'}</p>
						</div>
						<div class="model-status">
							{#if settingsStore.activeModels.clip_status === 'downloaded'}
								<span class="status-badge ready">Ready</span>
							{:else if settingsStore.activeModels.clip_status === 'auto_download'}
								<span class="status-badge auto" title="Will download automatically on first use">Auto</span>
							{:else if getModelStatus(settingsStore.activeModels.clip_model) === 'downloading'}
								{@const progress = getProgress(settingsStore.activeModels.clip_model)}
								<!-- eslint-disable-next-line @typescript-eslint/no-confusing-void-expression -->
								{@render circularProgress(progress?.progress ?? 0, 36)}
							{:else}
								<button class="download-btn small" on:click={() => { void downloadModel(settingsStore.activeModels.clip_model); }}>
									Download
								</button>
							{/if}
						</div>
					</div>
				</div>

				<div class="model-card">
					<div class="model-header">
						<span class="model-icon">👤</span>
						<div class="model-info">
							<h4>Face Detection</h4>
							<p>{settingsStore.activeModels.face_model || 'Not configured'}</p>
						</div>
						<div class="model-status">
							{#if settingsStore.activeModels.face_status === 'downloaded'}
								<span class="status-badge ready">Ready</span>
							{:else if settingsStore.activeModels.face_status === 'auto_download'}
								<span class="status-badge auto" title="Will download automatically on first use">Auto</span>
							{:else if getModelStatus(settingsStore.activeModels.face_model) === 'downloading'}
								{@const progress = getProgress(settingsStore.activeModels.face_model)}
								<!-- eslint-disable-next-line @typescript-eslint/no-confusing-void-expression -->
								{@render circularProgress(progress?.progress ?? 0, 36)}
							{:else}
								<span class="status-badge pending">Pending</span>
							{/if}
						</div>
					</div>
				</div>
			</div>
		</div>
	{/if}

	<!-- Model Browser -->
	<div class="model-browser">
		<h3>Browse & Download Models</h3>

		<div class="browser-actions">
			<div class="search-box">
				<input
					type="text"
					placeholder="Search Hugging Face models..."
					bind:value={searchQuery}
					on:keydown={(e) => e.key === 'Enter' && handleSearch()}
				/>
				<button on:click={handleSearch} disabled={searching}>
					{searching ? '...' : '🔍'}
				</button>
			</div>

			<button class="lookup-btn" on:click={openLookupModal}>
				📥 Lookup by ID
			</button>
		</div>

		<!-- Search Results -->
		{#if searchResults.length > 0}
			<div class="search-results">
				<h4>Search Results</h4>
				{#each searchResults as model (model.model_id)}
					<div class="result-card">
						<div class="result-info">
							<span class="result-name">{model.model_id}</span>
							{#if model.pipeline_tag}
								<span class="result-tag">{model.pipeline_tag}</span>
							{/if}
							<div class="result-stats">
								<span>⬇️ {formatNumber(model.downloads)}</span>
								<span>❤️ {formatNumber(model.likes)}</span>
								{#if model.size_mb}
									<span>💾 {model.size_mb.toFixed(0)} MB</span>
								{/if}
							</div>
						</div>
						<div class="result-actions">
							{#if getModelStatus(model.model_id) === 'downloaded'}
								<span class="downloaded-badge">✓ Downloaded</span>
							{:else if getModelStatus(model.model_id) === 'downloading'}
								{@const progress = getProgress(model.model_id)}
								<div class="download-progress-inline">
									<!-- eslint-disable-next-line @typescript-eslint/no-confusing-void-expression -->
									{@render circularProgress(progress?.progress ?? 0, 28)}
									{#if progress?.current_file}
										<span class="current-file" title={progress.current_file}>
											{progress.current_file.split('/').pop()}
										</span>
									{/if}
								</div>
							{:else}
								<button class="download-btn" on:click={() => downloadModel(model.model_id)}>
									Download
								</button>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		{/if}

		<!-- Recommended Models -->
		{#if Object.keys(settingsStore.recommendedModels).length > 0}
			<div class="recommended-models">
				<h4>Recommended Models</h4>
				{#each Object.entries(settingsStore.recommendedModels) as [task, models]}
					<div class="task-group">
						<h5>{task.replace(/-/g, ' ')}</h5>
						<div class="model-list">
							{#each models as model (model.model_id)}
								<div class="model-item">
									<span class="model-name">{model.model_id}</span>
									{#if getModelStatus(model.model_id) === 'downloaded'}
										<span class="status-icon downloaded">✓</span>
									{:else if getModelStatus(model.model_id) === 'downloading'}
										{@const progress = getProgress(model.model_id)}
										<!-- eslint-disable-next-line @typescript-eslint/no-confusing-void-expression -->
										{@render circularProgress(progress?.progress ?? 0, 24)}
									{:else}
										<button class="mini-download-btn" on:click={() => downloadModel(model.model_id)}>
											⬇️
										</button>
									{/if}
								</div>
							{/each}
						</div>
					</div>
				{/each}
			</div>
		{/if}

		<!-- Downloaded Models -->
		{#if settingsStore.downloadedModels.length > 0}
			<div class="downloaded-models">
				<h4>Downloaded Models</h4>
				{#each settingsStore.downloadedModels as modelId}
					<div class="downloaded-item">
						<span class="model-name">{modelId}</span>
						<button class="delete-btn" on:click={() => deleteModel(modelId)}>
							🗑️
						</button>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</section>

<!-- Lookup Modal -->
{#if showLookupModal}
	<div class="modal-overlay" on:click={() => (showLookupModal = false)} on:keydown={(e) => e.key === 'Escape' && (showLookupModal = false)} role="button" tabindex="0">
		<div class="modal" on:click|stopPropagation on:keydown|stopPropagation role="dialog" aria-modal="true" aria-labelledby="lookup-modal-title" tabindex="-1">
			<div class="modal-header">
				<h3 id="lookup-modal-title">Lookup Model by ID</h3>
				<button class="close-btn" on:click={() => (showLookupModal = false)}>×</button>
			</div>

			<div class="modal-body">
				<p class="modal-hint">Enter a Hugging Face model ID (e.g., <code>openai/clip-vit-base-patch32</code>)</p>

				<div class="lookup-input">
					<input
						type="text"
						placeholder="author/model-name"
						bind:value={lookupModelId}
						on:keydown={(e) => e.key === 'Enter' && handleLookup()}
					/>
					<button on:click={handleLookup} disabled={lookingUp}>
						{lookingUp ? 'Looking up...' : 'Lookup'}
					</button>
				</div>

				{#if lookupResult}
					<div class="lookup-result">
						<h4>{lookupResult.model_id}</h4>
						<div class="result-details">
							{#if lookupResult.pipeline_tag}
								<p><strong>Task:</strong> {lookupResult.pipeline_tag}</p>
							{/if}
							{#if lookupResult.library_name}
								<p><strong>Library:</strong> {lookupResult.library_name}</p>
							{/if}
							<p><strong>Downloads:</strong> {formatNumber(lookupResult.downloads)}</p>
							<p><strong>Likes:</strong> {formatNumber(lookupResult.likes)}</p>
							{#if lookupResult.size_mb}
								<p><strong>Size:</strong> {lookupResult.size_mb.toFixed(0)} MB</p>
							{/if}
							{#if lookupResult.files.length > 0}
								<p><strong>Files:</strong> {lookupResult.files.length}</p>
								<details>
									<summary>View files</summary>
									<ul class="file-list">
										{#each lookupResult.files.slice(0, 20) as file}
											<li>{file}</li>
										{/each}
										{#if lookupResult.files.length > 20}
											<li>... and {lookupResult.files.length - 20} more</li>
										{/if}
									</ul>
								</details>
							{/if}
						</div>

						<div class="lookup-actions">
							{#if getModelStatus(lookupResult.model_id) === 'downloaded'}
								<span class="downloaded-badge">✓ Already Downloaded</span>
							{:else if getModelStatus(lookupResult.model_id) === 'downloading'}
								{@const progress = getProgress(lookupResult.model_id)}
								<div class="download-progress-modal">
									<!-- eslint-disable-next-line @typescript-eslint/no-confusing-void-expression -->
									{@render circularProgress(progress?.progress ?? 0, 48)}
									<div class="progress-details">
										<span class="progress-label">Downloading...</span>
										{#if progress?.current_file}
											<span class="current-file">{progress.current_file.split('/').pop()}</span>
										{/if}
										{#if progress !== undefined}
											<span class="progress-bytes">
												{formatBytes(progress.downloaded_bytes)} / {formatBytes(progress.total_bytes)}
											</span>
										{/if}
									</div>
								</div>
							{:else}
								<button class="download-btn primary" on:click={() => lookupResult && downloadModel(lookupResult.model_id)}>
									Download Model
								</button>
							{/if}
						</div>
					</div>
				{/if}
			</div>
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
		cursor: pointer;
		font-size: 1.25rem;
	}

	/* Active Models */
	.active-models {
		margin-bottom: 1.5rem;
	}

	.active-models h3 {
		font-size: 1rem;
		margin: 0 0 0.75rem;
	}

	.model-cards {
		display: grid;
		gap: 1rem;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
	}

	.model-card {
		background: var(--bg-secondary, #f9fafb);
		border-radius: 8px;
		padding: 1rem;
	}

	.model-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.model-icon {
		font-size: 1.5rem;
	}

	.model-info {
		flex: 1;
	}

	.model-info h4 {
		margin: 0;
		font-size: 0.875rem;
		font-weight: 600;
	}

	.model-info p {
		margin: 0;
		font-size: 0.75rem;
		color: var(--text-muted, #6b7280);
		font-family: monospace;
	}

	.status-badge {
		font-size: 0.75rem;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		background: var(--warning-bg, #fef3c7);
		color: var(--warning-text, #92400e);
	}

	.status-badge.ready {
		background: var(--success-bg, #d1fae5);
		color: var(--success-text, #065f46);
	}

	.status-badge.auto {
		background: var(--info-bg, #dbeafe);
		color: var(--info-text, #1e40af);
	}

	.status-badge.pending {
		background: var(--bg-tertiary, #f3f4f6);
		color: var(--text-muted, #6b7280);
	}

	/* Model Browser */
	.model-browser h3 {
		font-size: 1rem;
		margin: 0 0 1rem;
	}

	.browser-actions {
		display: flex;
		gap: 1rem;
		margin-bottom: 1rem;
		flex-wrap: wrap;
	}

	.search-box {
		flex: 1;
		min-width: 250px;
		display: flex;
	}

	.search-box input {
		flex: 1;
		padding: 0.625rem;
		border: 1px solid var(--border-color, #e5e7eb);
		border-radius: 6px 0 0 6px;
		font-size: 0.875rem;
	}

	.search-box button {
		padding: 0.625rem 1rem;
		background: var(--primary, #3b82f6);
		color: white;
		border: none;
		border-radius: 0 6px 6px 0;
		cursor: pointer;
	}

	.lookup-btn {
		padding: 0.625rem 1rem;
		background: var(--bg-secondary, #f9fafb);
		border: 1px solid var(--border-color, #e5e7eb);
		border-radius: 6px;
		cursor: pointer;
		font-size: 0.875rem;
	}

	/* Search Results */
	.search-results, .recommended-models, .downloaded-models {
		margin-top: 1.5rem;
	}

	.search-results h4, .recommended-models h4, .downloaded-models h4 {
		font-size: 0.875rem;
		margin: 0 0 0.75rem;
		color: var(--text-muted, #6b7280);
	}

	.result-card {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem;
		background: var(--bg-secondary, #f9fafb);
		border-radius: 6px;
		margin-bottom: 0.5rem;
	}

	.result-name {
		font-family: monospace;
		font-size: 0.875rem;
	}

	.result-tag {
		font-size: 0.75rem;
		padding: 0.125rem 0.375rem;
		background: var(--primary-light, #dbeafe);
		color: var(--primary, #3b82f6);
		border-radius: 4px;
		margin-left: 0.5rem;
	}

	.result-stats {
		display: flex;
		gap: 0.75rem;
		font-size: 0.75rem;
		color: var(--text-muted, #6b7280);
		margin-top: 0.25rem;
	}

	.download-btn {
		padding: 0.375rem 0.75rem;
		background: var(--primary, #3b82f6);
		color: white;
		border: none;
		border-radius: 4px;
		font-size: 0.75rem;
		cursor: pointer;
	}

	.download-btn.primary {
		padding: 0.625rem 1.25rem;
		font-size: 0.875rem;
	}

	.downloaded-badge {
		font-size: 0.75rem;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		background: var(--success-bg, #d1fae5);
		color: var(--success-text, #065f46);
	}

	/* Task Groups */
	.task-group {
		margin-bottom: 1rem;
	}

	.task-group h5 {
		font-size: 0.75rem;
		text-transform: uppercase;
		color: var(--text-muted, #6b7280);
		margin: 0 0 0.5rem;
	}

	.model-list {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.model-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.5rem 0.75rem;
		background: var(--bg-secondary, #f9fafb);
		border-radius: 4px;
	}

	.model-item .model-name {
		font-family: monospace;
		font-size: 0.8125rem;
	}

	.mini-download-btn {
		background: none;
		border: none;
		cursor: pointer;
		font-size: 1rem;
	}

	.status-icon {
		font-size: 0.875rem;
	}

	.status-icon.downloaded {
		color: var(--success-text, #065f46);
	}

	/* Downloaded Models */
	.downloaded-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.5rem 0.75rem;
		background: var(--bg-secondary, #f9fafb);
		border-radius: 4px;
		margin-bottom: 0.25rem;
	}

	.delete-btn {
		background: none;
		border: none;
		cursor: pointer;
		opacity: 0.5;
	}

	.delete-btn:hover {
		opacity: 1;
	}

	/* Modal */
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
		max-width: 500px;
		max-height: 90vh;
		overflow-y: auto;
	}

	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem 1.5rem;
		border-bottom: 1px solid var(--border-color, #e5e7eb);
	}

	.modal-header h3 {
		margin: 0;
		font-size: 1.125rem;
	}

	.close-btn {
		background: none;
		border: none;
		font-size: 1.5rem;
		cursor: pointer;
		color: var(--text-muted, #6b7280);
	}

	.modal-body {
		padding: 1.5rem;
	}

	.modal-hint {
		font-size: 0.875rem;
		color: var(--text-muted, #6b7280);
		margin: 0 0 1rem;
	}

	.modal-hint code {
		background: var(--bg-secondary, #f9fafb);
		padding: 0.125rem 0.375rem;
		border-radius: 3px;
		font-size: 0.8125rem;
	}

	.lookup-input {
		display: flex;
		margin-bottom: 1rem;
	}

	.lookup-input input {
		flex: 1;
		padding: 0.625rem;
		border: 1px solid var(--border-color, #e5e7eb);
		border-radius: 6px 0 0 6px;
	}

	.lookup-input button {
		padding: 0.625rem 1rem;
		background: var(--primary, #3b82f6);
		color: white;
		border: none;
		border-radius: 0 6px 6px 0;
		cursor: pointer;
	}

	.lookup-result {
		background: var(--bg-secondary, #f9fafb);
		border-radius: 8px;
		padding: 1rem;
	}

	.lookup-result h4 {
		margin: 0 0 0.75rem;
		font-family: monospace;
	}

	.result-details p {
		margin: 0.25rem 0;
		font-size: 0.875rem;
	}

	.file-list {
		font-size: 0.75rem;
		font-family: monospace;
		max-height: 150px;
		overflow-y: auto;
		margin: 0.5rem 0;
		padding-left: 1.25rem;
	}

	.lookup-actions {
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid var(--border-color, #e5e7eb);
	}

	/* Circular Progress */
	.circular-progress {
		position: relative;
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}

	.circular-progress svg {
		display: block;
	}

	.circular-progress .progress-circle {
		transition: stroke-dashoffset 0.3s ease;
	}

	.circular-progress .progress-text {
		position: absolute;
		font-size: 0.5em;
		font-weight: 600;
		color: var(--text-primary, #1f2937);
	}

	/* Download progress inline (in search results) */
	.download-progress-inline {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.download-progress-inline .current-file {
		font-size: 0.625rem;
		color: var(--text-muted, #6b7280);
		max-width: 100px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	/* Download progress modal (in lookup modal) */
	.download-progress-modal {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 0.5rem;
	}

	.download-progress-modal .progress-details {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.download-progress-modal .progress-label {
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--text-primary, #1f2937);
	}

	.download-progress-modal .current-file {
		font-size: 0.75rem;
		color: var(--text-muted, #6b7280);
		font-family: monospace;
	}

	.download-progress-modal .progress-bytes {
		font-size: 0.75rem;
		color: var(--text-muted, #6b7280);
	}

	/* Model status in active models */
	.model-status {
		display: flex;
		align-items: center;
	}

	/* Small download button */
	.download-btn.small {
		padding: 0.25rem 0.625rem;
		font-size: 0.75rem;
	}
</style>
