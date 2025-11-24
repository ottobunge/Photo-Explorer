<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { client, API_HOST } from '$lib/api/client';

	interface Connector {
		id: string;
		type: 'google_photos' | 'local' | 'upload';
		name: string;
		enabled: boolean;
		status: 'disconnected' | 'connected' | 'syncing' | 'error';
		config: Record<string, unknown>;
		last_sync: string | null;
		error_message: string | null;
		created_at: string;
		updated_at: string | null;
	}

	interface ConnectorsResponse {
		connectors: Connector[];
	}

	let connectors = $state<Connector[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	onMount(() => {
		void loadConnectors();
	});

	async function loadConnectors(): Promise<void> {
		loading = true;
		error = null;
		try {
			const res = await client.get<ConnectorsResponse>('/connectors');
			if (res.success && res.data) {
				connectors = res.data.connectors;
			}
		} catch (err: unknown) {
			console.error('Failed to load connectors:', err);
			error = err instanceof Error ? err.message : 'Failed to load connectors';
		} finally {
			loading = false;
		}
	}

	function getConnectorIcon(type: string): string {
		switch (type) {
			case 'google_photos':
				return '\u{1F4F7}'; // camera
			case 'local':
				return '\u{1F4C1}'; // folder
			case 'upload':
				return '\u{1F4E4}'; // inbox tray
			default:
				return '\u{1F517}'; // link
		}
	}

	function getConnectorTypeName(type: string): string {
		switch (type) {
			case 'google_photos':
				return 'Google Photos';
			case 'local':
				return 'Local Folder';
			case 'upload':
				return 'Uploads';
			default:
				return type;
		}
	}

	function getStatusColor(status: string): string {
		switch (status) {
			case 'connected':
				return 'bg-green-500';
			case 'syncing':
				return 'bg-blue-500';
			case 'error':
				return 'bg-red-500';
			default:
				return 'bg-gray-400';
		}
	}

	function navigateToConnector(id: string): void {
		void goto(`/connectors/${id}`);
	}

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return 'Never';
		return new Date(dateStr).toLocaleString();
	}
</script>

<svelte:head>
	<title>Connectors - Photo Explorer</title>
</svelte:head>

<div class="p-8">
	<header class="mb-8 flex items-center justify-between">
		<div>
			<h1 class="text-3xl font-bold text-gray-900">Connectors</h1>
			<p class="mt-2 text-gray-600">Manage photo sources and browse imported photos</p>
		</div>
		<a
			href="/settings"
			class="rounded-lg bg-blue-500 px-4 py-2 text-white hover:bg-blue-600"
		>
			+ Add Connector
		</a>
	</header>

	{#if error}
		<div class="mb-4 rounded-lg bg-red-50 p-4 text-red-700">{error}</div>
	{/if}

	{#if loading}
		<div class="py-12 text-center text-gray-500">Loading connectors...</div>
	{:else if connectors.length === 0}
		<div class="card p-12 text-center">
			<div class="mb-4 text-4xl">{'\u{1F517}'}</div>
			<p class="text-gray-500">No connectors configured yet</p>
			<p class="mt-2 text-sm text-gray-400">
				Add a connector to start importing photos from Google Photos or local folders.
			</p>
			<a
				href="/settings"
				class="mt-4 inline-block rounded-lg bg-blue-500 px-4 py-2 text-white hover:bg-blue-600"
			>
				Go to Settings
			</a>
		</div>
	{:else}
		<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
			{#each connectors as connector (connector.id)}
				<button
					onclick={() => navigateToConnector(connector.id)}
					class="group block rounded-lg border border-gray-200 bg-white p-6 text-left transition-shadow hover:shadow-md"
				>
					<div class="flex items-start gap-4">
						<div class="text-3xl">{getConnectorIcon(connector.type)}</div>
						<div class="flex-1">
							<h3 class="font-semibold text-gray-900 group-hover:text-blue-600">
								{connector.name}
							</h3>
							<p class="text-sm text-gray-500">{getConnectorTypeName(connector.type)}</p>
						</div>
						<div class="flex items-center gap-2">
							<span class={`h-2 w-2 rounded-full ${getStatusColor(connector.status)}`}></span>
							<span class="text-sm text-gray-500 capitalize">{connector.status}</span>
						</div>
					</div>

					{#if connector.error_message}
						<div class="mt-3 rounded bg-red-50 px-3 py-2 text-sm text-red-600">
							{connector.error_message}
						</div>
					{/if}

					<div class="mt-4 flex items-center justify-between text-xs text-gray-400">
						<span>Last sync: {formatDate(connector.last_sync)}</span>
						<span class="text-blue-500 group-hover:underline">Browse photos &rarr;</span>
					</div>
				</button>
			{/each}
		</div>
	{/if}
</div>
