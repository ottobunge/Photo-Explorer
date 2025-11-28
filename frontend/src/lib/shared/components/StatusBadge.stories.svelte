<script module lang="ts">
	import { defineMeta } from '@storybook/addon-svelte-csf';
	import StatusBadge from './StatusBadge.svelte';

	const { Story } = defineMeta({
		title: 'Shared/StatusBadge',
		component: StatusBadge,
		tags: ['autodocs'],
		argTypes: {
			status: {
				control: 'select',
				options: ['connected', 'disconnected', 'syncing', 'error', 'success', 'warning', 'info'],
				description: 'Status type'
			},
			label: {
				control: 'text',
				description: 'Label text'
			},
			showDot: {
				control: 'boolean',
				description: 'Show status dot indicator'
			},
			class: {
				control: 'text',
				description: 'Additional CSS classes'
			}
		}
	});
</script>

<!--
@component
StatusBadge component displays status indicators.

## Usage
```svelte
<StatusBadge status="success" label="Active" showDot={true} />
```
-->

<!-- Success status -->
<Story name="Success" args={{ status: 'success', label: 'Active', showDot: true }} />

<!-- Error status -->
<Story name="Error" args={{ status: 'error', label: 'Failed', showDot: true }} />

<!-- Warning status -->
<Story name="Warning" args={{ status: 'warning', label: 'Pending', showDot: true }} />

<!-- Info status -->
<Story name="Info" args={{ status: 'info', label: 'Processing', showDot: true }} />

<!-- Syncing status -->
<Story name="Syncing" args={{ status: 'syncing', label: 'Syncing', showDot: true }} />

<!-- Without dot -->
<Story name="WithoutDot" args={{ status: 'success', label: 'Connected', showDot: false }} />

<!-- All statuses -->
<Story name="AllStatuses" asChild>
	<div style="display: flex; flex-direction: column; gap: 1rem;">
		<div style="display: flex; gap: 1rem; align-items: center;">
			<StatusBadge status="success" label="Success" showDot={true} />
			<StatusBadge status="error" label="Error" showDot={true} />
			<StatusBadge status="warning" label="Warning" showDot={true} />
			<StatusBadge status="info" label="Info" showDot={true} />
			<StatusBadge status="syncing" label="Syncing" showDot={true} />
		</div>
		<div style="display: flex; gap: 1rem; align-items: center;">
			<StatusBadge status="success" label="Success" showDot={false} />
			<StatusBadge status="error" label="Error" showDot={false} />
			<StatusBadge status="warning" label="Warning" showDot={false} />
			<StatusBadge status="info" label="Info" showDot={false} />
			<StatusBadge status="syncing" label="Syncing" showDot={false} />
		</div>
	</div>
</Story>

<!-- In a card -->
<Story name="InCard" asChild>
	<div
		style="padding: 1.5rem; border: 1px solid #e5e7eb; border-radius: 12px; background: white; max-width: 400px;"
	>
		<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
			<h3 style="margin: 0; font-size: 1.125rem; font-weight: 600;">Google Photos</h3>
			<StatusBadge status="success" label="Connected" showDot={true} />
		</div>
		<p style="margin: 0; color: #6b7280; font-size: 0.875rem;">
			Last synced: 2 minutes ago
		</p>
	</div>
</Story>
