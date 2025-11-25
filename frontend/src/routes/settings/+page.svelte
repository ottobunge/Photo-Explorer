<script lang="ts">
	import { onMount } from 'svelte';
	import {
		settingsStore,
		AppSettingsSection,
		ModelsSection
	} from '$lib/features/settings';

	onMount(async () => {
		await settingsStore.loadSettings();
	});
</script>

<svelte:head>
	<title>Settings | Photo Explorer</title>
</svelte:head>

<div class="settings-page">
	<header class="page-header">
		<h1 class="page-title">Settings</h1>
		<p class="page-description">
			Configure AI models and application preferences.
		</p>
	</header>

	<div class="settings-content">
		<section class="settings-category">
			<h2 class="category-title">AI Models</h2>
			<p class="category-description">
				Configure and download AI models for image embeddings and face detection.
			</p>

			<ModelsSection />
		</section>

		<section class="settings-category">
			<h2 class="category-title">Preferences</h2>
			<p class="category-description">
				Customize how Photo Explorer processes your photos.
			</p>

			<AppSettingsSection />
		</section>
	</div>
</div>

<style>
	.settings-page {
		max-width: 800px;
		margin: 0 auto;
		padding: 2rem;
	}

	.page-header {
		margin-bottom: 2rem;
	}

	.page-title {
		font-size: 2rem;
		font-weight: 700;
		margin: 0 0 0.5rem;
	}

	.page-description {
		color: var(--text-muted, #6b7280);
		font-size: 1.125rem;
		margin: 0;
	}

	.settings-content {
		display: flex;
		flex-direction: column;
		gap: 3rem;
	}

	.settings-category {
		/* Wrapping section */
	}

	.category-title {
		font-size: 1.5rem;
		font-weight: 600;
		margin: 0 0 0.5rem;
	}

	.category-description {
		color: var(--text-muted, #6b7280);
		margin: 0 0 1.5rem;
	}

	@media (max-width: 640px) {
		.settings-page {
			padding: 1rem;
		}

		.page-title {
			font-size: 1.5rem;
		}

		.page-description {
			font-size: 1rem;
		}

		.category-title {
			font-size: 1.25rem;
		}
	}
</style>
