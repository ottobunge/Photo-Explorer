import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import Card from './Card.svelte';
import CardTest from './Card.test.svelte';

describe('Card', () => {
	describe('Props', () => {
		it('renders with default props', () => {
			const { container } = render(Card, {
				props: {}
			});

			const card = container.querySelector('.card');
			expect(card).toBeTruthy();
			expect(card?.className).toContain('card');
		});

		it('applies variant classes', () => {
			const variants = ['default', 'elevated', 'outlined', 'filled'] as const;

			variants.forEach(variant => {
				const { container } = render(Card, {
					props: { variant }
				});

				const card = container.querySelector('.card');
				expect(card?.className).toContain(`card-${variant}`);
			});
		});

		it('applies padding sizes', () => {
			const paddings = ['none', 'sm', 'md', 'lg'] as const;

			paddings.forEach(padding => {
				const { container } = render(Card, {
					props: { padding }
				});

				const card = container.querySelector('.card');
				if (padding === 'none') {
					expect(card?.className).toContain('p-0');
				} else {
					expect(card?.className).toContain(`p-${padding}`);
				}
			});
		});

		it('applies custom className', () => {
			const { container } = render(Card, {
				props: {
					className: 'custom-card-class'
				}
			});

			const card = container.querySelector('.card');
			expect(card?.className).toContain('custom-card-class');
		});

		it('renders with title', () => {
			const { getByText } = render(CardTest, {
				props: {
					title: 'Card Title',
					showCard: true
				}
			});

			expect(getByText('Card Title')).toBeTruthy();
		});

		it('renders with subtitle', () => {
			const { getByText } = render(CardTest, {
				props: {
					subtitle: 'Card subtitle',
					showCard: true
				}
			});

			expect(getByText('Card subtitle')).toBeTruthy();
		});
	});

	describe('User Interactions', () => {
		it('handles click when clickable', async () => {
			const handleClick = vi.fn();
			const { container } = render(Card, {
				props: {
					clickable: true,
					onclick: handleClick
				}
			});

			const card = container.querySelector('.card');
			expect(card?.className).toContain('clickable');

			await fireEvent.click(card!);
			expect(handleClick).toHaveBeenCalledTimes(1);
		});

		it('does not handle click when not clickable', async () => {
			const handleClick = vi.fn();
			const { container } = render(Card, {
				props: {
					clickable: false,
					onclick: handleClick
				}
			});

			const card = container.querySelector('.card');
			expect(card?.className).not.toContain('clickable');

			await fireEvent.click(card!);
			expect(handleClick).not.toHaveBeenCalled();
		});

		it('handles hover effects when hoverable', () => {
			const { container } = render(Card, {
				props: {
					hoverable: true
				}
			});

			const card = container.querySelector('.card');
			expect(card?.className).toContain('hoverable');
		});

		it('handles keyboard navigation when clickable', async () => {
			const handleClick = vi.fn();
			const { container } = render(Card, {
				props: {
					clickable: true,
					onclick: handleClick
				}
			});

			const card = container.querySelector('.card');

			// Enter key
			await fireEvent.keyDown(card!, { key: 'Enter' });
			expect(handleClick).toHaveBeenCalledTimes(1);

			// Space key
			await fireEvent.keyDown(card!, { key: ' ' });
			expect(handleClick).toHaveBeenCalledTimes(2);
		});
	});

	describe('Rendering', () => {
		it('renders children content', () => {
			const { getByText } = render(CardTest, {
				props: {
					content: 'Card content goes here',
					showCard: true
				}
			});

			expect(getByText('Card content goes here')).toBeTruthy();
		});

		it('renders header snippet', () => {
			const { getByText } = render(CardTest, {
				props: {
					headerContent: 'Header content',
					showCard: true
				}
			});

			expect(getByText('Header content')).toBeTruthy();
		});

		it('renders footer snippet', () => {
			const { getByText } = render(CardTest, {
				props: {
					footerContent: 'Footer content',
					showCard: true
				}
			});

			expect(getByText('Footer content')).toBeTruthy();
		});

		it('renders actions snippet', () => {
			const { getByText } = render(CardTest, {
				props: {
					actionsContent: 'Action buttons',
					showCard: true
				}
			});

			expect(getByText('Action buttons')).toBeTruthy();
		});

		it('renders media/image', () => {
			const { container } = render(CardTest, {
				props: {
					imageUrl: '/test-image.jpg',
					imageAlt: 'Test image',
					showCard: true
				}
			});

			const image = container.querySelector('img');
			expect(image?.src).toContain('/test-image.jpg');
			expect(image?.alt).toBe('Test image');
		});
	});

	describe('Accessibility', () => {
		it('has proper role when clickable', () => {
			const { container } = render(Card, {
				props: {
					clickable: true
				}
			});

			const card = container.querySelector('.card');
			expect(card?.getAttribute('role')).toBe('button');
			expect(card?.getAttribute('tabindex')).toBe('0');
		});

		it('has proper ARIA attributes', () => {
			const { container } = render(Card, {
				props: {
					ariaLabel: 'Product card',
					ariaDescribedBy: 'product-description'
				}
			});

			const card = container.querySelector('.card');
			expect(card?.getAttribute('aria-label')).toBe('Product card');
			expect(card?.getAttribute('aria-describedby')).toBe('product-description');
		});

		it('indicates selected state', () => {
			const { container } = render(Card, {
				props: {
					selected: true
				}
			});

			const card = container.querySelector('.card');
			expect(card?.getAttribute('aria-selected')).toBe('true');
			expect(card?.className).toContain('selected');
		});

		it('indicates disabled state', () => {
			const { container } = render(Card, {
				props: {
					disabled: true,
					clickable: true
				}
			});

			const card = container.querySelector('.card');
			expect(card?.getAttribute('aria-disabled')).toBe('true');
			expect(card?.className).toContain('disabled');
		});
	});

	describe('Edge Cases', () => {
		it('handles loading state', () => {
			const { container } = render(Card, {
				props: {
					loading: true
				}
			});

			const card = container.querySelector('.card');
			expect(card?.className).toContain('loading');

			const skeleton = container.querySelector('.skeleton');
			if (!skeleton) {
				const spinner = container.querySelector('.loading-spinner');
				expect(spinner).toBeTruthy();
			}
		});

		it('handles error state', () => {
			const { container } = render(Card, {
				props: {
					error: true,
					errorMessage: 'Failed to load content'
				}
			});

			const card = container.querySelector('.card');
			expect(card?.className).toContain('error');

			const errorElement = container.querySelector('.error-message');
			expect(errorElement?.textContent).toContain('Failed to load content');
		});

		it('maintains state during prop changes', async () => {
			const { container, rerender } = render(Card, {
				props: {
					variant: 'default'
				}
			});

			const card = container.querySelector('.card');
			expect(card?.className).toContain('card-default');

			await rerender({
				variant: 'elevated'
			});

			expect(card?.className).toContain('card-elevated');
			expect(card?.className).not.toContain('card-default');
		});

		it('handles complex nested content', () => {
			const { container } = render(CardTest, {
				props: {
					showCard: true,
					complexContent: true
				}
			});

			// Check that nested elements render correctly
			const nestedCards = container.querySelectorAll('.card .card');
			expect(nestedCards.length).toBeGreaterThan(0);
		});
	});
});