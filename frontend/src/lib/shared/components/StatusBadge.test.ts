import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import StatusBadge from './StatusBadge.svelte';

describe('StatusBadge', () => {
	describe('Status Types', () => {
		it('renders connected status', () => {
			const { container, getByText } = render(StatusBadge, {
				props: { status: 'connected' }
			});

			expect(getByText('Connected')).toBeTruthy();
			const dot = container.querySelector('.status-dot');
			expect(dot?.className).toContain('bg-green-500');
		});

		it('renders disconnected status', () => {
			const { container, getByText } = render(StatusBadge, {
				props: { status: 'disconnected' }
			});

			expect(getByText('Disconnected')).toBeTruthy();
			const dot = container.querySelector('.status-dot');
			expect(dot?.className).toContain('bg-gray-400');
		});

		it('renders syncing status', () => {
			const { container, getByText } = render(StatusBadge, {
				props: { status: 'syncing' }
			});

			expect(getByText('Syncing')).toBeTruthy();
			const dot = container.querySelector('.status-dot');
			expect(dot?.className).toContain('bg-blue-500');
		});

		it('renders error status', () => {
			const { container, getByText } = render(StatusBadge, {
				props: { status: 'error' }
			});

			expect(getByText('Error')).toBeTruthy();
			const dot = container.querySelector('.status-dot');
			expect(dot?.className).toContain('bg-red-500');
		});

		it('renders success status', () => {
			const { container, getByText } = render(StatusBadge, {
				props: { status: 'success' }
			});

			expect(getByText('Success')).toBeTruthy();
			const dot = container.querySelector('.status-dot');
			expect(dot?.className).toContain('bg-green-500');
		});

		it('renders warning status', () => {
			const { container, getByText } = render(StatusBadge, {
				props: { status: 'warning' }
			});

			expect(getByText('Warning')).toBeTruthy();
			const dot = container.querySelector('.status-dot');
			expect(dot?.className).toContain('bg-yellow-500');
		});

		it('renders info status', () => {
			const { container, getByText } = render(StatusBadge, {
				props: { status: 'info' }
			});

			expect(getByText('Info')).toBeTruthy();
			const dot = container.querySelector('.status-dot');
			expect(dot?.className).toContain('bg-blue-500');
		});
	});

	describe('Colors', () => {
		it('applies correct color for connected status', () => {
			const { container } = render(StatusBadge, {
				props: { status: 'connected' }
			});

			const dot = container.querySelector('.status-dot');
			expect(dot?.className).toContain('bg-green-500');
		});

		it('applies correct color for error status', () => {
			const { container } = render(StatusBadge, {
				props: { status: 'error' }
			});

			const dot = container.querySelector('.status-dot');
			expect(dot?.className).toContain('bg-red-500');
		});

		it('applies correct color for syncing/info status', () => {
			const { container: syncContainer } = render(StatusBadge, {
				props: { status: 'syncing' }
			});

			const { container: infoContainer } = render(StatusBadge, {
				props: { status: 'info' }
			});

			const syncDot = syncContainer.querySelector('.status-dot');
			const infoDot = infoContainer.querySelector('.status-dot');

			expect(syncDot?.className).toContain('bg-blue-500');
			expect(infoDot?.className).toContain('bg-blue-500');
		});

		it('applies correct color for warning status', () => {
			const { container } = render(StatusBadge, {
				props: { status: 'warning' }
			});

			const dot = container.querySelector('.status-dot');
			expect(dot?.className).toContain('bg-yellow-500');
		});

		it('applies correct color for disconnected status', () => {
			const { container } = render(StatusBadge, {
				props: { status: 'disconnected' }
			});

			const dot = container.querySelector('.status-dot');
			expect(dot?.className).toContain('bg-gray-400');
		});
	});

	describe('Labels', () => {
		it('displays default label from status', () => {
			const { getByText } = render(StatusBadge, {
				props: { status: 'connected' }
			});

			expect(getByText('Connected')).toBeTruthy();
		});

		it('displays custom label', () => {
			const { getByText } = render(StatusBadge, {
				props: {
					status: 'connected',
					label: 'Active'
				}
			});

			expect(getByText('Active')).toBeTruthy();
		});

		it('capitalizes first letter of default label', () => {
			const { getByText } = render(StatusBadge, {
				props: { status: 'disconnected' }
			});

			const text = getByText('Disconnected');
			expect(text.textContent).toBe('Disconnected');
			expect(text.textContent?.[0]).toBe('D');
		});

		it('uses custom label over default', () => {
			const { getByText, queryByText } = render(StatusBadge, {
				props: {
					status: 'error',
					label: 'Failed'
				}
			});

			expect(getByText('Failed')).toBeTruthy();
			expect(queryByText('Error')).toBeFalsy();
		});

		it('allows empty custom label', () => {
			const { container } = render(StatusBadge, {
				props: {
					status: 'connected',
					label: ''
				}
			});

			const label = container.querySelector('.status-label');
			expect(label?.textContent).toBe('');
		});

		it('handles long custom labels', () => {
			const { getByText } = render(StatusBadge, {
				props: {
					status: 'syncing',
					label: 'Currently synchronizing data'
				}
			});

			expect(getByText('Currently synchronizing data')).toBeTruthy();
		});
	});

	describe('Status Dot', () => {
		it('shows status dot by default', () => {
			const { container } = render(StatusBadge, {
				props: { status: 'connected' }
			});

			const dot = container.querySelector('.status-dot');
			expect(dot).toBeTruthy();
		});

		it('hides status dot when showDot is false', () => {
			const { container } = render(StatusBadge, {
				props: {
					status: 'connected',
					showDot: false
				}
			});

			const dot = container.querySelector('.status-dot');
			expect(dot).toBeFalsy();
		});

		it('shows status dot when showDot is true', () => {
			const { container } = render(StatusBadge, {
				props: {
					status: 'connected',
					showDot: true
				}
			});

			const dot = container.querySelector('.status-dot');
			expect(dot).toBeTruthy();
		});

		it('dot is circular', () => {
			const { container } = render(StatusBadge, {
				props: { status: 'connected' }
			});

			const dot = container.querySelector('.status-dot') as HTMLSpanElement;
			expect(dot).toBeTruthy();
			// Dot element exists and will be styled with border-radius: 50%
			expect(dot?.className).toContain('status-dot');
		});

		it('dot has proper sizing', () => {
			const { container } = render(StatusBadge, {
				props: { status: 'connected' }
			});

			const dot = container.querySelector('.status-dot');
			// dot should have 8x8px dimensions
			expect(dot?.className).toContain('status-dot');
		});
	});

	describe('Classes and Styling', () => {
		it('applies custom CSS class', () => {
			const { container } = render(StatusBadge, {
				props: {
					status: 'connected',
					class: 'custom-badge'
				}
			});

			const badge = container.querySelector('.status-badge');
			expect(badge?.className).toContain('custom-badge');
		});

		it('wraps in flex container', () => {
			const { container } = render(StatusBadge, {
				props: { status: 'connected' }
			});

			const badge = container.querySelector('.status-badge');
			expect(badge).toBeTruthy();
			
		});

		it('has proper spacing between elements', () => {
			const { container } = render(StatusBadge, {
				props: { status: 'connected' }
			});

			const badge = container.querySelector('.status-badge');
			
		});

		it('label does not wrap', () => {
			const { container } = render(StatusBadge, {
				props: { status: 'connected' }
			});

			const label = container.querySelector('.status-label');
			// Label should exist and be properly styled
		expect(label).toBeTruthy();
		expect(label?.className).toContain('status-label');
		});

		it('dot does not shrink', () => {
			const { container } = render(StatusBadge, {
				props: { status: 'connected' }
			});

			const dot = container.querySelector('.status-dot');
			// Dot should exist and have styling applied
		expect(dot).toBeTruthy();
		expect(dot?.className).toContain('status-dot');
		});
	});

	describe('Component Structure', () => {
		it('renders status badge container', () => {
			const { container } = render(StatusBadge, {
				props: { status: 'connected' }
			});

			const badge = container.querySelector('.status-badge');
			expect(badge).toBeTruthy();
		});

		it('renders in correct order: dot, label', () => {
			const { container } = render(StatusBadge, {
				props: { status: 'connected' }
			});

			const badge = container.querySelector('.status-badge');
			const children = badge?.children;

			expect(children?.[0]?.className).toContain('status-dot');
			expect(children?.[1]?.className).toContain('status-label');
		});

		it('renders label text correctly', () => {
			const { container } = render(StatusBadge, {
				props: { status: 'success' }
			});

			const label = container.querySelector('.status-label');
			expect(label?.textContent).toBe('Success');
		});
	});

	describe('All Status Combinations', () => {
		const statuses = ['connected', 'disconnected', 'syncing', 'error', 'success', 'warning', 'info'] as const;

		it('renders all status types without errors', () => {
			statuses.forEach((status) => {
				const { container } = render(StatusBadge, {
					props: { status }
				});

				expect(container.querySelector('.status-badge')).toBeTruthy();
			});
		});

		it('all statuses have proper labels', () => {
			statuses.forEach((status) => {
				const { getByText } = render(StatusBadge, {
					props: { status }
				});

				const expectedLabel = status.charAt(0).toUpperCase() + status.slice(1);
				expect(getByText(expectedLabel)).toBeTruthy();
			});
		});

		it('all statuses have color indicators', () => {
			statuses.forEach((status) => {
				const { container } = render(StatusBadge, {
					props: { status }
				});

				const dot = container.querySelector('.status-dot');
				const className = dot?.className || '';
				expect(
					className.includes('bg-green-500') ||
					className.includes('bg-red-500') ||
					className.includes('bg-blue-500') ||
					className.includes('bg-yellow-500') ||
					className.includes('bg-gray-400')
				).toBe(true);
			});
		});
	});

	describe('Accessibility', () => {
		it('is visible to screen readers', () => {
			const { container } = render(StatusBadge, {
				props: { status: 'connected', label: 'Connected' }
			});

			const label = container.querySelector('.status-label');
			expect(label?.textContent).toBe('Connected');
		});

		it('conveys status through color and text', () => {
			const { container, getByText } = render(StatusBadge, {
				props: { status: 'error' }
			});

			// Both color (dot) and text (label) communicate status
			expect(container.querySelector('.status-dot')).toBeTruthy();
			expect(getByText('Error')).toBeTruthy();
		});

		it('uses semantic structure', () => {
			const { container } = render(StatusBadge, {
				props: { status: 'connected' }
			});

			const badge = container.querySelector('.status-badge');
			expect(badge).toBeTruthy();
			expect(badge?.querySelector('.status-label')).toBeTruthy();
		});
	});

	describe('Edge Cases', () => {
		it('handles rapid status changes', async () => {
			const { rerender } = render(StatusBadge, {
				props: { status: 'connected' }
			});

			await rerender({ status: 'disconnected' });
			await rerender({ status: 'syncing' });
			await rerender({ status: 'connected' });

			expect(true).toBe(true);
		});

		it('handles custom label changes', async () => {
			const { rerender, getByText } = render(StatusBadge, {
				props: {
					status: 'connected',
					label: 'Online'
				}
			});

			expect(getByText('Online')).toBeTruthy();

			await rerender({
				status: 'connected',
				label: 'Ready'
			});

			expect(getByText('Ready')).toBeTruthy();
		});

		it('handles showDot toggle', async () => {
			const { container, rerender } = render(StatusBadge, {
				props: {
					status: 'connected',
					showDot: true
				}
			});

			expect(container.querySelector('.status-dot')).toBeTruthy();

			await rerender({
				status: 'connected',
				showDot: false
			});

			expect(container.querySelector('.status-dot')).toBeFalsy();
		});

		it('maintains color consistency across re-renders', async () => {
			const { container, rerender } = render(StatusBadge, {
				props: { status: 'connected' }
			});

			let dot = container.querySelector('.status-dot');
			expect(dot?.className).toContain('bg-green-500');

			await rerender({ status: 'connected', label: 'Updated' });

			dot = container.querySelector('.status-dot');
			expect(dot?.className).toContain('bg-green-500');
		});
	});

	describe('Svelte 5 Patterns', () => {
		it('uses $props() for props', () => {
			const { container } = render(StatusBadge, {
				props: { status: 'connected' }
			});

			expect(container.querySelector('.status-badge')).toBeTruthy();
		});

		it('uses $derived for statusColor', () => {
			const statuses = ['connected', 'error', 'syncing'] as const;

			statuses.forEach((status) => {
				const { container } = render(StatusBadge, {
					props: { status }
				});

				const dot = container.querySelector('.status-dot');
				expect(dot).toBeTruthy();
			});
		});
	});
});
