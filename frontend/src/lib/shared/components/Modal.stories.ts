import type { Meta, StoryObj } from '@storybook/svelte';
import Modal from './Modal.svelte';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import Button from './Button.svelte';

/**
 * Modal component provides a dialog overlay for focused interactions.
 *
 * ## Usage
 * ```svelte
 * {#if showModal}
 *   <Modal title="Confirm Action" on:close={() => showModal = false}>
 *     <p>Are you sure you want to proceed?</p>
 *     <div style="display: flex; gap: 0.5rem; margin-top: 1rem;">
 *       <Button variant="primary">Confirm</Button>
 *       <Button variant="secondary" on:click={() => showModal = false}>Cancel</Button>
 *     </div>
 *   </Modal>
 * {/if}
 * ```
 */
// @ts-ignore - Svelte 5 component type incompatibility with Storybook
const meta = {
	title: 'Shared/Modal',
	component: Modal,
	tags: ['autodocs'],
	argTypes: {
		title: {
			control: 'text',
			description: 'Modal title (optional)'
		}
	},
	parameters: {
		// Increase delay to allow transitions to complete
		chromatic: { delay: 300 }
	}
} satisfies Meta<Modal>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Basic modal with title
 */
export const Default: Story = {
	args: {
		title: 'Modal Title'
	},
	render: (args) => ({
		Component: Modal,
		props: args,
		slots: {
			default: '<p style="margin: 0;">This is the modal content.</p>'
		}
	})
};

/**
 * Modal without title
 */
export const NoTitle: Story = {
	args: {
		title: ''
	},
	render: (args) => ({
		Component: Modal,
		props: args,
		slots: {
			default: `
				<h3 style="margin: 0 0 1rem; font-size: 1.25rem; font-weight: 600;">Custom Content</h3>
				<p style="margin: 0; color: #6b7280;">Modal without a title prop, using custom content instead.</p>
			`
		}
	})
};

/**
 * Confirmation dialog pattern
 */
export const Confirmation: Story = {
	args: {
		title: 'Confirm Deletion'
	},
	render: (args) => ({
		Component: Modal,
		props: args,
		slots: {
			default: `
				<p style="margin: 0 0 1.5rem; color: #6b7280;">
					Are you sure you want to delete this photo? This action cannot be undone.
				</p>
				<div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
					<Button variant="secondary">Cancel</Button>
					<Button variant="primary">Delete</Button>
				</div>
			`
		}
	})
};

/**
 * Form in modal
 */
export const FormModal: Story = {
	args: {
		title: 'Create Album'
	},
	render: (args) => ({
		Component: Modal,
		props: args,
		slots: {
			default: `
				<form style="display: flex; flex-direction: column; gap: 1rem;">
					<div>
						<label style="display: block; margin-bottom: 0.5rem; font-weight: 500; color: #374151;">
							Album Name
						</label>
						<input
							type="text"
							placeholder="Enter album name"
							style="width: 100%; padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 6px;"
						/>
					</div>
					<div>
						<label style="display: block; margin-bottom: 0.5rem; font-weight: 500; color: #374151;">
							Description
						</label>
						<textarea
							placeholder="Enter description (optional)"
							rows="3"
							style="width: 100%; padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 6px; resize: vertical;"
						></textarea>
					</div>
					<div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 0.5rem;">
						<Button variant="secondary">Cancel</Button>
						<Button variant="primary" type="submit">Create Album</Button>
					</div>
				</form>
			`
		}
	})
};

/**
 * Modal with long content
 */
export const LongContent: Story = {
	args: {
		title: 'Terms and Conditions'
	},
	render: (args) => ({
		Component: Modal,
		props: args,
		slots: {
			default: `
				<div style="max-height: 400px; overflow-y: auto; color: #6b7280;">
					<p style="margin: 0 0 1rem;">Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
					<p style="margin: 0 0 1rem;">Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.</p>
					<p style="margin: 0 0 1rem;">Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.</p>
					<p style="margin: 0 0 1rem;">Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
					<p style="margin: 0 0 1rem;">Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
					<p style="margin: 0 0 1rem;">Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.</p>
				</div>
				<div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #e5e7eb;">
					<Button variant="secondary">Decline</Button>
					<Button variant="primary">Accept</Button>
				</div>
			`
		}
	})
};

/**
 * Success message modal
 */
export const Success: Story = {
	args: {
		title: 'Success!'
	},
	render: (args) => ({
		Component: Modal,
		props: args,
		slots: {
			default: `
				<div style="text-align: center;">
					<div style="font-size: 3rem; margin-bottom: 1rem;">✅</div>
					<p style="margin: 0 0 1.5rem; color: #6b7280;">
						Your photos have been uploaded successfully!
					</p>
					<Button variant="primary">Continue</Button>
				</div>
			`
		}
	})
};

/**
 * Error message modal
 */
export const Error: Story = {
	args: {
		title: 'Error'
	},
	render: (args) => ({
		Component: Modal,
		props: args,
		slots: {
			default: `
				<div style="text-align: center;">
					<div style="font-size: 3rem; margin-bottom: 1rem;">❌</div>
					<p style="margin: 0 0 1.5rem; color: #6b7280;">
						Failed to connect to Google Photos. Please check your credentials and try again.
					</p>
					<div style="display: flex; gap: 0.5rem; justify-content: center;">
						<Button variant="secondary">Cancel</Button>
						<Button variant="primary">Retry</Button>
					</div>
				</div>
			`
		}
	})
};

/**
 * Modal with image
 */
export const WithImage: Story = {
	args: {
		title: 'Photo Details'
	},
	render: (args) => ({
		Component: Modal,
		props: args,
		slots: {
			default: `
				<div>
					<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); height: 200px; border-radius: 8px; margin-bottom: 1rem;"></div>
					<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1rem; font-size: 0.875rem;">
						<div>
							<div style="color: #9ca3af; margin-bottom: 0.25rem;">Filename</div>
							<div style="color: #1f2937; font-weight: 500;">IMG_1234.jpg</div>
						</div>
						<div>
							<div style="color: #9ca3af; margin-bottom: 0.25rem;">Size</div>
							<div style="color: #1f2937; font-weight: 500;">2.4 MB</div>
						</div>
						<div>
							<div style="color: #9ca3af; margin-bottom: 0.25rem;">Date</div>
							<div style="color: #1f2937; font-weight: 500;">2024-01-15</div>
						</div>
						<div>
							<div style="color: #9ca3af; margin-bottom: 0.25rem;">Resolution</div>
							<div style="color: #1f2937; font-weight: 500;">4032 × 3024</div>
						</div>
					</div>
					<div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
						<Button variant="secondary">Close</Button>
						<Button variant="primary">Download</Button>
					</div>
				</div>
			`
		}
	})
};
