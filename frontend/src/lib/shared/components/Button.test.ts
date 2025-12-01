import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import Button from './Button.svelte';

describe('Button', () => {
	describe('Props', () => {
		it('renders with default props', () => {
			const { container } = render(Button, {
				props: {}
			});

			const button = container.querySelector('button');
			expect(button).toBeTruthy();
			expect(button?.getAttribute('type')).toBe('button');
		});

		it('applies variant classes correctly', () => {
			const variants = ['primary', 'secondary', 'ghost', 'danger'] as const;

			variants.forEach(variant => {
				const { container } = render(Button, {
					props: { variant }
				});

				const button = container.querySelector('button');
				expect(button?.className).toContain(`btn-${variant}`);
			});
		});

		it('applies size classes correctly', () => {
			const sizes = ['sm', 'md', 'lg'] as const;

			sizes.forEach(size => {
				const { container } = render(Button, {
					props: { size }
				});

				const button = container.querySelector('button');
				expect(button?.className).toContain(`btn-${size}`);
			});
		});

		it('sets correct button type', () => {
			const types = ['button', 'submit', 'reset'] as const;

			types.forEach(type => {
				const { container } = render(Button, {
					props: { type }
				});

				const button = container.querySelector('button');
				expect(button?.getAttribute('type')).toBe(type);
			});
		});

		it('applies disabled state', () => {
			const { container } = render(Button, {
				props: { disabled: true }
			});

			const button = container.querySelector('button');
			expect(button?.disabled).toBe(true);
			expect(button?.className).toContain('disabled');
		});

		it('applies loading state', () => {
			const { container, getByText } = render(Button, {
				props: {
					loading: true,
					children: 'Submit'
				}
			});

			const button = container.querySelector('button');
			expect(button?.disabled).toBe(true);
			expect(button?.className).toContain('loading');

			// Should show loading spinner or text
			const loadingIndicator = container.querySelector('.loading-spinner');
			if (!loadingIndicator) {
				expect(getByText('Loading...')).toBeTruthy();
			}
		});

		it('applies fullWidth style', () => {
			const { container } = render(Button, {
				props: { fullWidth: true }
			});

			const button = container.querySelector('button');
			expect(button?.className).toContain('w-full');
		});

		it('applies custom className', () => {
			const { container } = render(Button, {
				props: { className: 'custom-class' }
			});

			const button = container.querySelector('button');
			expect(button?.className).toContain('custom-class');
		});
	});

	describe('User Interactions', () => {
		it('calls onclick handler when clicked', async () => {
			const handleClick = vi.fn();
			const { container } = render(Button, {
				props: {
					onclick: handleClick
				}
			});

			const button = container.querySelector('button')!;
			await fireEvent.click(button);

			expect(handleClick).toHaveBeenCalledTimes(1);
		});

		it('does not call onclick when disabled', async () => {
			const handleClick = vi.fn();
			const { container } = render(Button, {
				props: {
					onclick: handleClick,
					disabled: true
				}
			});

			const button = container.querySelector('button')!;
			await fireEvent.click(button);

			expect(handleClick).not.toHaveBeenCalled();
		});

		it('does not call onclick when loading', async () => {
			const handleClick = vi.fn();
			const { container } = render(Button, {
				props: {
					onclick: handleClick,
					loading: true
				}
			});

			const button = container.querySelector('button')!;
			await fireEvent.click(button);

			expect(handleClick).not.toHaveBeenCalled();
		});

		it('handles keyboard interactions', async () => {
			const handleClick = vi.fn();
			const { container } = render(Button, {
				props: {
					onclick: handleClick
				}
			});

			const button = container.querySelector('button')!;

			// Enter key should trigger click
			await fireEvent.keyDown(button, { key: 'Enter' });
			expect(handleClick).toHaveBeenCalledTimes(1);

			// Space key should trigger click
			await fireEvent.keyDown(button, { key: ' ' });
			expect(handleClick).toHaveBeenCalledTimes(2);
		});
	});

	describe('Rendering', () => {
		it('renders children content', () => {
			const { getByText } = render(Button, {
				props: {
					children: 'Click me!'
				}
			});

			expect(getByText('Click me!')).toBeTruthy();
		});

		it('renders with icon', () => {
			const { container } = render(Button, {
				props: {
					icon: '🚀'
				}
			});

			const icon = container.querySelector('.btn-icon');
			expect(icon?.textContent).toBe('🚀');
		});

		it('renders icon with text', () => {
			const { container, getByText } = render(Button, {
				props: {
					icon: '✨',
					children: 'Save'
				}
			});

			const icon = container.querySelector('.btn-icon');
			expect(icon?.textContent).toBe('✨');
			expect(getByText('Save')).toBeTruthy();
		});

		it('positions icon correctly', () => {
			// Icon on left (default)
			const { container: leftContainer } = render(Button, {
				props: {
					icon: '←',
					iconPosition: 'left',
					children: 'Back'
				}
			});

			const leftButton = leftContainer.querySelector('button');
			const leftIcon = leftButton?.querySelector('.btn-icon');
			expect(leftIcon).toBeTruthy();

			// Icon on right
			const { container: rightContainer } = render(Button, {
				props: {
					icon: '→',
					iconPosition: 'right',
					children: 'Next'
				}
			});

			const rightButton = rightContainer.querySelector('button');
			const rightIcon = rightButton?.querySelector('.btn-icon:last-child');
			expect(rightIcon).toBeTruthy();
		});
	});

	describe('Accessibility', () => {
		it('has proper ARIA attributes when disabled', () => {
			const { container } = render(Button, {
				props: {
					disabled: true,
					ariaLabel: 'Disabled button'
				}
			});

			const button = container.querySelector('button');
			expect(button?.getAttribute('aria-disabled')).toBe('true');
			expect(button?.getAttribute('aria-label')).toBe('Disabled button');
		});

		it('has proper ARIA attributes when loading', () => {
			const { container } = render(Button, {
				props: {
					loading: true,
					ariaLabel: 'Loading button'
				}
			});

			const button = container.querySelector('button');
			expect(button?.getAttribute('aria-busy')).toBe('true');
			expect(button?.getAttribute('aria-label')).toBe('Loading button');
		});

		it('supports aria-describedby', () => {
			const { container } = render(Button, {
				props: {
					ariaDescribedBy: 'help-text'
				}
			});

			const button = container.querySelector('button');
			expect(button?.getAttribute('aria-describedby')).toBe('help-text');
		});
	});

	describe('Edge Cases', () => {
		it('handles rapid clicks', async () => {
			const handleClick = vi.fn();
			const { container } = render(Button, {
				props: {
					onclick: handleClick
				}
			});

			const button = container.querySelector('button')!;

			// Rapid clicks
			await fireEvent.click(button);
			await fireEvent.click(button);
			await fireEvent.click(button);

			expect(handleClick).toHaveBeenCalledTimes(3);
		});

		it('handles form submission', () => {
			const handleSubmit = vi.fn((e: Event) => e.preventDefault());

			const form = document.createElement('form');
			form.addEventListener('submit', handleSubmit);
			document.body.appendChild(form);

			const { container } = render(Button, {
				props: {
					type: 'submit'
				},
				target: form
			});

			const button = container.querySelector('button')!;
			fireEvent.click(button);

			expect(handleSubmit).toHaveBeenCalled();

			document.body.removeChild(form);
		});

		it('maintains state during prop changes', async () => {
			const { container, rerender } = render(Button, {
				props: {
					variant: 'primary',
					children: 'Save'
				}
			});

			const button = container.querySelector('button');
			expect(button?.className).toContain('btn-primary');

			await rerender({
				variant: 'secondary',
				children: 'Save'
			});

			expect(button?.className).toContain('btn-secondary');
			expect(button?.className).not.toContain('btn-primary');
		});
	});
});