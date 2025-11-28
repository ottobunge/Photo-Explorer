import type { Meta, StoryObj } from '@storybook/svelte';
import EmptyState from './EmptyState.svelte';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import Button from './Button.svelte';

/**
 * EmptyState component displays a placeholder when there's no content to show.
 *
 * ## Usage
 * ```svelte
 * <EmptyState
 *   icon="📷"
 *   title="No photos yet"
 *   description="Upload your first photo to get started"
 * >
 *   {#snippet action()}
 *     <Button>Upload Photo</Button>
 *   {/snippet}
 * </EmptyState>
 * ```
 */
// @ts-ignore - Svelte 5 component type incompatibility with Storybook
const meta = {
	title: 'Shared/EmptyState',
	component: EmptyState,
	tags: ['autodocs'],
	argTypes: {
		icon: {
			control: 'text',
			description: 'Icon or emoji to display'
		},
		title: {
			control: 'text',
			description: 'Title text'
		},
		description: {
			control: 'text',
			description: 'Description text'
		},
		class: {
			control: 'text',
			description: 'Additional CSS classes'
		}
	}
} satisfies Meta<EmptyState>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Default empty state
 */
export const Default: Story = {
	args: {
		icon: '📭',
		title: 'No items found',
		description: ''
	}
};

/**
 * No photos state
 */
export const NoPhotos: Story = {
	args: {
		icon: '📷',
		title: 'No photos yet',
		description: 'Upload your first photo to get started with your collection.'
	}
};

/**
 * No search results state
 */
export const NoSearchResults: Story = {
	args: {
		icon: '🔍',
		title: 'No results found',
		description: 'Try adjusting your search terms or filters.'
	}
};

/**
 * No connectors state
 */
export const NoConnectors: Story = {
	args: {
		icon: '🔌',
		title: 'No connectors configured',
		description: 'Connect a photo source to start syncing your photos.'
	}
};

/**
 * No albums state
 */
export const NoAlbums: Story = {
	args: {
		icon: '📁',
		title: 'No albums yet',
		description: 'Create your first album to organize your photos.'
	}
};

/**
 * No faces state
 */
export const NoFaces: Story = {
	args: {
		icon: '👤',
		title: 'No faces detected',
		description: 'Upload photos with people to start organizing by faces.'
	}
};

/**
 * Empty state with action button
 */
export const WithAction: Story = {
	render: () => ({
		Component: EmptyState,
		template: `
			<EmptyState
				icon="📷"
				title="No photos yet"
				description="Upload your first photo to get started with your collection."
			>
				{#snippet action()}
					<Button variant="primary">Upload Photos</Button>
				{/snippet}
			</EmptyState>
		`
	})
};

/**
 * Empty state with multiple actions
 */
export const WithMultipleActions: Story = {
	render: () => ({
		Component: EmptyState,
		template: `
			<EmptyState
				icon="🔌"
				title="No connectors configured"
				description="Connect a photo source to start syncing your photos automatically."
			>
				{#snippet action()}
					<div style="display: flex; gap: 0.5rem; justify-content: center;">
						<Button variant="primary">Add Connector</Button>
						<Button variant="secondary">Learn More</Button>
					</div>
				{/snippet}
			</EmptyState>
		`
	})
};

/**
 * Empty state without icon
 */
export const NoIcon: Story = {
	args: {
		icon: '',
		title: 'Nothing to see here',
		description: 'This empty state has no icon.'
	}
};

/**
 * Empty state with minimal text
 */
export const Minimal: Story = {
	args: {
		icon: '🤷',
		title: 'Nothing here',
		description: ''
	}
};

/**
 * All empty state variations
 */
export const AllVariations: Story = {
	render: () => ({
		Component: EmptyState,
		template: `
			<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1rem;">
				<EmptyState icon="📷" title="No photos" />
				<EmptyState icon="🔍" title="No results" />
				<EmptyState icon="📁" title="No albums" />
				<EmptyState icon="👤" title="No faces" />
				<EmptyState icon="🔌" title="No connectors" />
				<EmptyState icon="⚙️" title="No settings" />
			</div>
		`
	})
};
