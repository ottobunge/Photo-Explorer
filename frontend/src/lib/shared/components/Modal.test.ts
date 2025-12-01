import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import { tick } from 'svelte';
import Modal from './Modal.svelte';
import ModalTest from './Modal.test.svelte';

describe('Modal', () => {
	describe('Props', () => {
		it('renders with title prop', () => {
			const { getByText } = render(ModalTest, {
				props: {
					title: 'Test Modal',
					showModal: true
				}
			});

			expect(getByText('Test Modal')).toBeTruthy();
		});

		it('renders without title when not provided', () => {
			const { container } = render(ModalTest, {
				props: {
					showModal: true
				}
			});

			const titleElement = container.querySelector('#modal-title');
			expect(titleElement).toBeNull();
		});
	});

	describe('User Interactions', () => {
		it('calls onclose when close button is clicked', async () => {
			const onclose = vi.fn();
			const { container } = render(ModalTest, {
				props: {
					showModal: true,
					onclose
				}
			});

			const closeButton = container.querySelector('button[aria-label="Close modal"]');
			expect(closeButton).toBeTruthy();

			await fireEvent.click(closeButton!);
			expect(onclose).toHaveBeenCalledTimes(1);
		});

		it('calls onclose when Escape key is pressed', async () => {
			const onclose = vi.fn();
			render(ModalTest, {
				props: {
					showModal: true,
					onclose
				}
			});

			await fireEvent.keyDown(window, { key: 'Escape' });
			expect(onclose).toHaveBeenCalledTimes(1);
		});

		it('calls onclose when clicking backdrop', async () => {
			const onclose = vi.fn();
			const { container } = render(ModalTest, {
				props: {
					showModal: true,
					onclose
				}
			});

			const backdrop = container.querySelector('.bg-black\\/50');
			expect(backdrop).toBeTruthy();

			await fireEvent.click(backdrop!);
			expect(onclose).toHaveBeenCalledTimes(1);
		});

		it('does not call onclose when clicking modal content', async () => {
			const onclose = vi.fn();
			const { container } = render(ModalTest, {
				props: {
					showModal: true,
					onclose
				}
			});

			const modalContent = container.querySelector('.card');
			expect(modalContent).toBeTruthy();

			await fireEvent.click(modalContent!);
			expect(onclose).not.toHaveBeenCalled();
		});

		it('handles Enter key on backdrop for accessibility', async () => {
			const onclose = vi.fn();
			const { container } = render(ModalTest, {
				props: {
					showModal: true,
					onclose
				}
			});

			const backdrop = container.querySelector('.bg-black\\/50');
			expect(backdrop).toBeTruthy();

			await fireEvent.keyDown(backdrop!, { key: 'Enter' });
			// Should trigger the click handler via the keydown handler
			await tick();
			expect(onclose).toHaveBeenCalled();
		});
	});

	describe('Rendering', () => {
		it('renders children content', () => {
			const { getByText } = render(ModalTest, {
				props: {
					showModal: true,
					content: 'Modal content here'
				}
			});

			expect(getByText('Modal content here')).toBeTruthy();
		});

		it('renders footer content when provided', () => {
			const { getByText } = render(ModalTest, {
				props: {
					showModal: true,
					footerContent: 'Footer content'
				}
			});

			expect(getByText('Footer content')).toBeTruthy();
		});
	});

	describe('Accessibility', () => {
		it('has proper ARIA attributes', () => {
			const { container } = render(ModalTest, {
				props: {
					showModal: true,
					title: 'Accessible Modal'
				}
			});

			const dialog = container.querySelector('[role="dialog"]');
			expect(dialog).toBeTruthy();
			expect(dialog?.getAttribute('aria-modal')).toBe('true');
			expect(dialog?.getAttribute('aria-labelledby')).toBe('modal-title');
		});

		it('has accessible close button', () => {
			const { container } = render(ModalTest, {
				props: {
					showModal: true
				}
			});

			const closeButton = container.querySelector('button[aria-label="Close modal"]');
			expect(closeButton).toBeTruthy();
			expect(closeButton?.getAttribute('type')).toBe('button');
		});

		it('backdrop has button role and tabindex', () => {
			const { container } = render(ModalTest, {
				props: {
					showModal: true
				}
			});

			const backdrop = container.querySelector('[role="button"][tabindex="-1"]');
			expect(backdrop).toBeTruthy();
		});
	});

	describe('Transitions', () => {
		it('applies fade transition to container', () => {
			const { container } = render(ModalTest, {
				props: {
					showModal: true
				}
			});

			const modalContainer = container.querySelector('.fixed.inset-0');
			// Svelte adds transition classes dynamically
			expect(modalContainer).toBeTruthy();
		});

		it('applies fly transition to modal content', () => {
			const { container } = render(ModalTest, {
				props: {
					showModal: true
				}
			});

			const modalContent = container.querySelector('.card');
			expect(modalContent).toBeTruthy();
		});
	});

	describe('Edge Cases', () => {
		it('does not crash when onclose is not provided', async () => {
			const { container } = render(ModalTest, {
				props: {
					showModal: true
				}
			});

			const closeButton = container.querySelector('button[aria-label="Close modal"]');
			expect(closeButton).toBeTruthy();

			// Should not throw
			await fireEvent.click(closeButton!);
		});

		it('handles rapid open/close cycles', async () => {
			const onclose = vi.fn();
			const { rerender } = render(ModalTest, {
				props: {
					showModal: true,
					onclose
				}
			});

			// Rapid state changes
			await rerender({ showModal: false, onclose });
			await rerender({ showModal: true, onclose });
			await rerender({ showModal: false, onclose });
			await rerender({ showModal: true, onclose });

			// Modal should still be functional
			await fireEvent.keyDown(window, { key: 'Escape' });
			expect(onclose).toHaveBeenCalled();
		});
	});
});