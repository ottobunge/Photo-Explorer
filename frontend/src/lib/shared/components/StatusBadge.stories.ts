import type { Meta, StoryObj } from '@storybook/svelte';
import StatusBadge from './StatusBadge.svelte';

/**
 * StatusBadge component displays connection/sync status with consistent indicators.
 *
 * ## Usage
 * ```svelte
 * <StatusBadge status="connected" />
 * <StatusBadge status="syncing" label="Syncing photos..." />
 * <StatusBadge status="error" showDot={false} />
 * ```
 */
// @ts-ignore - Svelte 5 component type incompatibility with Storybook
const meta = {
	title: 'Shared/StatusBadge',
	component: StatusBadge,
	tags: ['autodocs'],
	argTypes: {
		status: {
			control: 'select',
			options: ['connected', 'disconnected', 'syncing', 'error', 'success', 'warning', 'info'],
			description: 'The status type to display'
		},
		label: {
			control: 'text',
			description: 'Optional label text (defaults to status)'
		},
		showDot: {
			control: 'boolean',
			description: 'Whether to show the status dot'
		},
		class: {
			control: 'text',
			description: 'Additional CSS classes'
		}
	}
} satisfies Meta<StatusBadge>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Connected status (green)
 */
export const Connected: Story = {
	args: {
		status: 'connected'
	}
};

/**
 * Disconnected status (gray)
 */
export const Disconnected: Story = {
	args: {
		status: 'disconnected'
	}
};

/**
 * Syncing status (blue)
 */
export const Syncing: Story = {
	args: {
		status: 'syncing',
		label: 'Syncing photos...'
	}
};

/**
 * Error status (red)
 */
export const Error: Story = {
	args: {
		status: 'error',
		label: 'Connection failed'
	}
};

/**
 * Success status (green)
 */
export const Success: Story = {
	args: {
		status: 'success',
		label: 'Sync complete'
	}
};

/**
 * Warning status (yellow)
 */
export const Warning: Story = {
	args: {
		status: 'warning',
		label: 'Limited functionality'
	}
};

/**
 * Info status (blue)
 */
export const Info: Story = {
	args: {
		status: 'info',
		label: 'Configuration needed'
	}
};

/**
 * Status badge without dot
 */
export const NoDot: Story = {
	args: {
		status: 'connected',
		showDot: false,
		label: 'Google Photos'
	}
};

/**
 * All status types side by side
 */
export const AllStatuses: Story = {
	render: () => ({
		Component: StatusBadge,
		template: `
			<div style="display: flex; flex-direction: column; gap: 1rem;">
				<StatusBadge status="connected" />
				<StatusBadge status="disconnected" />
				<StatusBadge status="syncing" />
				<StatusBadge status="error" />
				<StatusBadge status="success" />
				<StatusBadge status="warning" />
				<StatusBadge status="info" />
			</div>
		`
	})
};

/**
 * Custom labels
 */
export const CustomLabels: Story = {
	render: () => ({
		Component: StatusBadge,
		template: `
			<div style="display: flex; flex-direction: column; gap: 1rem;">
				<StatusBadge status="connected" label="Google Photos Connected" />
				<StatusBadge status="syncing" label="Syncing 1,234 photos..." />
				<StatusBadge status="error" label="Authentication failed" />
				<StatusBadge status="success" label="Upload complete (50 photos)" />
				<StatusBadge status="warning" label="Storage almost full" />
			</div>
		`
	})
};
