<script lang="ts">
	/**
	 * Status badge component for displaying connection/sync status
	 * Provides consistent status indicators across the application
	 */
	export type StatusType = 'connected' | 'disconnected' | 'syncing' | 'error' | 'success' | 'warning' | 'info';

	interface Props {
		/** The status type to display */
		status: StatusType;
		/** Optional label text (defaults to status) */
		label?: string;
		/** Whether to show the status dot */
		showDot?: boolean;
		/** Additional CSS classes */
		class?: string;
	}

	let {
		status,
		label = status.charAt(0).toUpperCase() + status.slice(1),
		showDot = true,
		class: className = ''
	}: Props = $props();

	function getStatusColor(status: StatusType): string {
		switch (status) {
			case 'connected':
			case 'success':
				return 'bg-green-500';
			case 'syncing':
			case 'info':
				return 'bg-blue-500';
			case 'warning':
				return 'bg-yellow-500';
			case 'error':
				return 'bg-red-500';
			case 'disconnected':
			default:
				return 'bg-gray-400';
		}
	}

	let statusColor = $derived(getStatusColor(status));
</script>

<div class="status-badge {className}">
	{#if showDot}
		<span class="status-dot {statusColor}"></span>
	{/if}
	<span class="status-label">{label}</span>
</div>

<style>
	.status-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		color: var(--text-muted, #6b7280);
	}

	.status-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.status-label {
		white-space: nowrap;
	}

	/* Color variants */
	.bg-green-500 {
		background-color: #10b981;
	}

	.bg-blue-500 {
		background-color: #3b82f6;
	}

	.bg-yellow-500 {
		background-color: #f59e0b;
	}

	.bg-red-500 {
		background-color: #ef4444;
	}

	.bg-gray-400 {
		background-color: #9ca3af;
	}
</style>
