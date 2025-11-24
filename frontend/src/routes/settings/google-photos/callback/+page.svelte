<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { settingsStore } from '$lib/features/settings';

	let status: 'loading' | 'success' | 'error' = 'loading';
	let errorMessage = '';

	onMount(async () => {
		const code = $page.url.searchParams.get('code');
		const error = $page.url.searchParams.get('error');

		if (error) {
			status = 'error';
			errorMessage = $page.url.searchParams.get('error_description') || 'Authorization was denied';
			return;
		}

		if (!code) {
			status = 'error';
			errorMessage = 'No authorization code received';
			return;
		}

		try {
			await settingsStore.handleGooglePhotosCallback(code);
			status = 'success';

			// Redirect to settings after a brief delay
			setTimeout(() => {
				goto('/settings');
			}, 2000);
		} catch (err) {
			status = 'error';
			errorMessage = err instanceof Error ? err.message : 'Failed to complete authorization';
		}
	});
</script>

<svelte:head>
	<title>Connecting Google Photos | Photo Explorer</title>
</svelte:head>

<div class="callback-page">
	<div class="callback-card">
		{#if status === 'loading'}
			<div class="status-icon loading">
				<div class="spinner"></div>
			</div>
			<h1>Connecting to Google Photos</h1>
			<p>Please wait while we complete the authorization...</p>
		{:else if status === 'success'}
			<div class="status-icon success">
				<svg viewBox="0 0 24 24" width="48" height="48">
					<path
						fill="currentColor"
						d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"
					/>
				</svg>
			</div>
			<h1>Successfully Connected!</h1>
			<p>Your Google Photos account has been linked. Redirecting to settings...</p>
		{:else}
			<div class="status-icon error">
				<svg viewBox="0 0 24 24" width="48" height="48">
					<path
						fill="currentColor"
						d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"
					/>
				</svg>
			</div>
			<h1>Connection Failed</h1>
			<p class="error-text">{errorMessage}</p>
			<a href="/settings" class="back-link">Back to Settings</a>
		{/if}
	</div>
</div>

<style>
	.callback-page {
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem;
		background: var(--bg-primary, #f9fafb);
	}

	.callback-card {
		background: var(--card-bg, #ffffff);
		border: 1px solid var(--border-color, #e5e7eb);
		border-radius: 16px;
		padding: 3rem;
		text-align: center;
		max-width: 400px;
		width: 100%;
	}

	.status-icon {
		width: 80px;
		height: 80px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		margin: 0 auto 1.5rem;
	}

	.status-icon.loading {
		background: var(--bg-secondary, #f3f4f6);
	}

	.status-icon.success {
		background: var(--success-bg, #dcfce7);
		color: var(--success-text, #16a34a);
	}

	.status-icon.error {
		background: var(--error-bg, #fef2f2);
		color: var(--error-text, #dc2626);
	}

	.spinner {
		width: 40px;
		height: 40px;
		border: 4px solid var(--border-color, #e5e7eb);
		border-top-color: var(--primary, #3b82f6);
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	h1 {
		font-size: 1.5rem;
		font-weight: 600;
		margin: 0 0 0.75rem;
	}

	p {
		color: var(--text-muted, #6b7280);
		margin: 0;
	}

	.error-text {
		color: var(--error-text, #dc2626);
		margin-bottom: 1.5rem;
	}

	.back-link {
		display: inline-block;
		padding: 0.75rem 1.5rem;
		background: var(--primary, #3b82f6);
		color: white;
		text-decoration: none;
		border-radius: 8px;
		font-weight: 500;
	}

	.back-link:hover {
		background: var(--primary-dark, #2563eb);
	}
</style>
