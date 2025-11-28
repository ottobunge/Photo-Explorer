import type { Meta, StoryObj } from '@storybook/svelte';
import Button from './Button.svelte';

/**
 * Button component provides consistent styling and behavior across all button interactions.
 *
 * ## Usage
 * ```svelte
 * <Button variant="primary" size="md" on:click={handleClick}>
 *   Click me
 * </Button>
 * ```
 */
// @ts-ignore - Svelte 5 component type incompatibility with Storybook
const meta = {
	title: 'Shared/Button',
	component: Button,
	tags: ['autodocs'],
	argTypes: {
		variant: {
			control: 'select',
			options: ['primary', 'secondary', 'ghost'],
			description: 'Visual style variant of the button'
		},
		size: {
			control: 'select',
			options: ['sm', 'md', 'lg'],
			description: 'Size of the button'
		},
		disabled: {
			control: 'boolean',
			description: 'Whether the button is disabled'
		},
		type: {
			control: 'select',
			options: ['button', 'submit', 'reset'],
			description: 'HTML button type attribute'
		}
	}
} satisfies Meta<Button>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Primary button is used for main actions
 */
export const Primary: Story = {
	args: {
		variant: 'primary',
		size: 'md'
	},
	render: (args) => ({
		Component: Button,
		props: args,
		slots: {
			default: 'Primary Button'
		}
	})
};

/**
 * Secondary button is used for secondary actions
 */
export const Secondary: Story = {
	args: {
		variant: 'secondary',
		size: 'md'
	},
	render: (args) => ({
		Component: Button,
		props: args,
		slots: {
			default: 'Secondary Button'
		}
	})
};

/**
 * Ghost button is used for tertiary actions with minimal visual weight
 */
export const Ghost: Story = {
	args: {
		variant: 'ghost',
		size: 'md'
	},
	render: (args) => ({
		Component: Button,
		props: args,
		slots: {
			default: 'Ghost Button'
		}
	})
};

/**
 * Small size button
 */
export const Small: Story = {
	args: {
		variant: 'primary',
		size: 'sm'
	},
	render: (args) => ({
		Component: Button,
		props: args,
		slots: {
			default: 'Small Button'
		}
	})
};

/**
 * Medium size button (default)
 */
export const Medium: Story = {
	args: {
		variant: 'primary',
		size: 'md'
	},
	render: (args) => ({
		Component: Button,
		props: args,
		slots: {
			default: 'Medium Button'
		}
	})
};

/**
 * Large size button
 */
export const Large: Story = {
	args: {
		variant: 'primary',
		size: 'lg'
	},
	render: (args) => ({
		Component: Button,
		props: args,
		slots: {
			default: 'Large Button'
		}
	})
};

/**
 * Disabled button state
 */
export const Disabled: Story = {
	args: {
		variant: 'primary',
		size: 'md',
		disabled: true
	},
	render: (args) => ({
		Component: Button,
		props: args,
		slots: {
			default: 'Disabled Button'
		}
	})
};

/**
 * All button variants side by side
 */
export const AllVariants: Story = {
	render: () => ({
		Component: Button,
		template: `
			<div style="display: flex; gap: 1rem; align-items: center;">
				<Button variant="primary">Primary</Button>
				<Button variant="secondary">Secondary</Button>
				<Button variant="ghost">Ghost</Button>
			</div>
		`
	})
};

/**
 * All button sizes side by side
 */
export const AllSizes: Story = {
	render: () => ({
		Component: Button,
		template: `
			<div style="display: flex; gap: 1rem; align-items: center;">
				<Button size="sm">Small</Button>
				<Button size="md">Medium</Button>
				<Button size="lg">Large</Button>
			</div>
		`
	})
};
