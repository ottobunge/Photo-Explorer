import type { Meta, StoryObj } from '@storybook/svelte';
import LoadingSpinner from './LoadingSpinner.svelte';

/**
 * LoadingSpinner component displays an animated loading indicator.
 *
 * ## Usage
 * ```svelte
 * <LoadingSpinner size="md" />
 * ```
 */
// @ts-ignore - Svelte 5 component type incompatibility with Storybook
const meta = {
	title: 'Shared/LoadingSpinner',
	component: LoadingSpinner,
	tags: ['autodocs'],
	argTypes: {
		size: {
			control: 'select',
			options: ['sm', 'md', 'lg'],
			description: 'Size of the spinner'
		}
	}
} satisfies Meta<LoadingSpinner>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Default medium size spinner
 */
export const Default: Story = {
	args: {
		size: 'md'
	}
};

/**
 * Small spinner for inline loading states
 */
export const Small: Story = {
	args: {
		size: 'sm'
	}
};

/**
 * Medium spinner (default)
 */
export const Medium: Story = {
	args: {
		size: 'md'
	}
};

/**
 * Large spinner for full-page loading states
 */
export const Large: Story = {
	args: {
		size: 'lg'
	}
};

/**
 * All sizes side by side
 */
export const AllSizes: Story = {
	render: () => ({
		Component: LoadingSpinner,
		template: `
			<div style="display: flex; gap: 2rem; align-items: center;">
				<div style="text-align: center;">
					<LoadingSpinner size="sm" />
					<div style="margin-top: 0.5rem; font-size: 0.75rem; color: #6b7280;">Small</div>
				</div>
				<div style="text-align: center;">
					<LoadingSpinner size="md" />
					<div style="margin-top: 0.5rem; font-size: 0.75rem; color: #6b7280;">Medium</div>
				</div>
				<div style="text-align: center;">
					<LoadingSpinner size="lg" />
					<div style="margin-top: 0.5rem; font-size: 0.75rem; color: #6b7280;">Large</div>
				</div>
			</div>
		`
	})
};

/**
 * Spinner centered in a container (common pattern)
 */
export const Centered: Story = {
	args: {
		size: 'lg'
	},
	decorators: [
		() => ({
			template: `
				<div style="display: flex; align-items: center; justify-content: center; height: 200px; background: #f9fafb; border-radius: 8px;">
					<story />
				</div>
			`
		})
	]
};
