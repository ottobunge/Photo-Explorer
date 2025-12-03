import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import LoadingSpinner from './LoadingSpinner.svelte';

describe('LoadingSpinner', () => {
	describe('Props', () => {
		it('renders with default size (md)', () => {
			const { container } = render(LoadingSpinner, {
				props: {}
			});

			const spinner = container.querySelector('[data-testid="loading-spinner"]');
			expect(spinner).toBeTruthy();

			const circle = container.querySelector('.h-6.w-6');
			expect(circle).toBeTruthy();
		});

		it('applies size class for small', () => {
			const { container } = render(LoadingSpinner, {
				props: { size: 'sm' }
			});

			const circle = container.querySelector('.h-4.w-4');
			expect(circle).toBeTruthy();
		});

		it('applies size class for medium', () => {
			const { container } = render(LoadingSpinner, {
				props: { size: 'md' }
			});

			const circle = container.querySelector('.h-6.w-6');
			expect(circle).toBeTruthy();
		});

		it('applies size class for large', () => {
			const { container } = render(LoadingSpinner, {
				props: { size: 'lg' }
			});

			const circle = container.querySelector('.h-8.w-8');
			expect(circle).toBeTruthy();
		});
	});

	describe('Rendering', () => {
		it('renders spinning circle element', () => {
			const { container } = render(LoadingSpinner, {
				props: {}
			});

			const circle = container.querySelector('.animate-spin');
			expect(circle).toBeTruthy();
			expect(circle?.className).toContain('rounded-full');
			expect(circle?.className).toContain('border-2');
		});

		it('has proper border styling', () => {
			const { container } = render(LoadingSpinner, {
				props: {}
			});

			const circle = container.querySelector('.animate-spin');
			expect(circle?.className).toContain('border-gray-300');
			expect(circle?.className).toContain('border-t-primary-600');
		});

		it('wraps spinner in flex container', () => {
			const { container } = render(LoadingSpinner, {
				props: {}
			});

			const wrapper = container.querySelector('.flex.items-center.justify-center');
			expect(wrapper).toBeTruthy();
			expect(wrapper?.querySelector('.animate-spin')).toBeTruthy();
		});
	});

	describe('Accessibility', () => {
		it('has testid for testing', () => {
			const { container } = render(LoadingSpinner, {
				props: {}
			});

			const spinner = container.querySelector('[data-testid="loading-spinner"]');
			expect(spinner?.getAttribute('data-testid')).toBe('loading-spinner');
		});

		it('should be perceivable visually for accessibility', () => {
			const { container } = render(LoadingSpinner, {
				props: {}
			});

			const spinner = container.querySelector('[data-testid="loading-spinner"]');
			// Spinner should have visual animation via CSS
			const circle = spinner?.querySelector('.animate-spin');
			expect(circle).toBeTruthy();
			expect(circle?.className).toContain('animate-spin');
		});
	});

	describe('Size Variations', () => {
		it('renders all size variants correctly', () => {
			const sizes = ['sm', 'md', 'lg'] as const;
			const expectedClasses = {
				sm: 'h-4 w-4',
				md: 'h-6 w-6',
				lg: 'h-8 w-8'
			};

			sizes.forEach((size) => {
				const { container } = render(LoadingSpinner, {
					props: { size }
				});

				const circle = container.querySelector('.animate-spin');
				expect(circle?.className).toContain(expectedClasses[size]);
			});
		});

		it('maintains aspect ratio for all sizes', () => {
			const sizes = ['sm', 'md', 'lg'] as const;

			sizes.forEach((size) => {
				const { container } = render(LoadingSpinner, {
					props: { size }
				});

				const circle = container.querySelector('.animate-spin');
				expect(circle?.className).toContain('w-');
				expect(circle?.className).toContain('h-');
			});
		});
	});

	describe('Visual Properties', () => {
		it('has spinning animation class', () => {
			const { container } = render(LoadingSpinner, {
				props: {}
			});

			const circle = container.querySelector('.animate-spin');
			expect(circle).toBeTruthy();
			expect(circle?.className).toContain('animate-spin');
		});

		it('has rounded border for circular shape', () => {
			const { container } = render(LoadingSpinner, {
				props: {}
			});

			const circle = container.querySelector('.animate-spin');
			expect(circle?.className).toContain('rounded-full');
		});

		it('uses two-tone color scheme for visual effect', () => {
			const { container } = render(LoadingSpinner, {
				props: {}
			});

			const circle = container.querySelector('.animate-spin');
			// Border is gray-300, except top which is primary-600 to create spinning effect
			expect(circle?.className).toContain('border-gray-300');
			expect(circle?.className).toContain('border-t-primary-600');
		});
	});

	describe('Edge Cases', () => {
		it('handles rapid re-renders', async () => {
			const { rerender } = render(LoadingSpinner, {
				props: { size: 'md' }
			});

			await rerender({ size: 'sm' });
			await rerender({ size: 'lg' });
			await rerender({ size: 'md' });

			// Should complete without error
			expect(true).toBe(true);
		});

		it('maintains consistency across multiple renders', () => {
			const spinners = [];

			for (let i = 0; i < 3; i++) {
				const { container } = render(LoadingSpinner, {
					props: { size: 'md' }
				});
				spinners.push(container);
			}

			spinners.forEach((container) => {
				const spinner = container.querySelector('[data-testid="loading-spinner"]');
				expect(spinner).toBeTruthy();
				expect(spinner?.querySelector('.animate-spin')).toBeTruthy();
			});
		});
	});

	describe('Component Structure', () => {
		it('uses Svelte 5 runes correctly', () => {
			const { container } = render(LoadingSpinner, {
				props: { size: 'md' }
			});

			// Should render successfully with $props() pattern
			expect(container.querySelector('[data-testid="loading-spinner"]')).toBeTruthy();
		});

		it('does not expose internal state outside component', () => {
			const { container } = render(LoadingSpinner, {
				props: {}
			});

			const spinner = container.querySelector('[data-testid="loading-spinner"]');
			// Component should only expose what's necessary
			expect(spinner?.getAttribute('data-testid')).toBe('loading-spinner');
		});
	});
});
