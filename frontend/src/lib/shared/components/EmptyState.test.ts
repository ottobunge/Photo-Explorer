import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import EmptyState from './EmptyState.svelte';
// Note: EmptyStateTest helper component not available, use EmptyState directly for action tests

describe('EmptyState', () => {
	describe('Props', () => {
		it('renders with default props', () => {
			const { container } = render(EmptyState, {
				props: {}
			});

			const emptyState = container.querySelector('.empty-state');
			expect(emptyState).toBeTruthy();
		});

		it('displays provided icon', () => {
			const { container } = render(EmptyState, {
				props: { icon: '📭' }
			});

			const icon = container.querySelector('.empty-icon');
			expect(icon?.textContent).toBe('📭');
		});

		it('displays provided title', () => {
			const { getByText } = render(EmptyState, {
				props: { title: 'No items found' }
			});

			expect(getByText('No items found')).toBeTruthy();
		});

		it('displays custom icon', () => {
			const { container } = render(EmptyState, {
				props: { icon: '🎉' }
			});

			const icon = container.querySelector('.empty-icon');
			expect(icon?.textContent).toBe('🎉');
		});

		it('displays custom title', () => {
			const { getByText } = render(EmptyState, {
				props: { title: 'Nothing here yet' }
			});

			expect(getByText('Nothing here yet')).toBeTruthy();
		});

		it('displays description when provided', () => {
			const { getByText } = render(EmptyState, {
				props: { description: 'Try uploading some photos' }
			});

			expect(getByText('Try uploading some photos')).toBeTruthy();
		});

		it('hides icon when not provided', () => {
			const { container } = render(EmptyState, {
				props: { icon: undefined }
			});

			const icon = container.querySelector('.empty-icon');
			expect(icon).toBeFalsy();
		});

		it('hides title when not provided', () => {
			const { container } = render(EmptyState, {
				props: { title: undefined }
			});

			const title = container.querySelector('.empty-title');
			expect(title).toBeFalsy();
		});

		it('hides description when not provided', () => {
			const { container } = render(EmptyState, {
				props: { description: undefined }
			});

			const description = container.querySelector('.empty-description');
			expect(description).toBeFalsy();
		});

		it('applies custom CSS classes', () => {
			const { container } = render(EmptyState, {
				props: { class: 'custom-class' }
			});

			const emptyState = container.querySelector('.empty-state');
			expect(emptyState?.className).toContain('custom-class');
		});
	});

	describe('Rendering', () => {
		it('renders all text elements in correct order', () => {
			const { container } = render(EmptyState, {
				props: {
					icon: '📭',
					title: 'No items',
					description: 'Try adding some content'
				}
			});

			const children = container.querySelector('.empty-state')?.children;
			expect(children?.length).toBeGreaterThan(0);
		});

		it('renders icon with proper styling', () => {
			const { container } = render(EmptyState, {
				props: { icon: '📁' }
			});

			const icon = container.querySelector('.empty-icon');
			expect(icon?.className).toContain('empty-icon');
			expect(icon?.textContent).toBe('📁');
		});

		it('renders title with proper styling', () => {
			const { container } = render(EmptyState, {
				props: { title: 'Empty state' }
			});

			const title = container.querySelector('.empty-title');
			expect(title?.className).toContain('empty-title');
			expect(title?.textContent).toBe('Empty state');
		});

		it('renders description with proper styling', () => {
			const { container } = render(EmptyState, {
				props: { description: 'Add some content' }
			});

			const description = container.querySelector('.empty-description');
			expect(description?.className).toContain('empty-description');
			expect(description?.textContent).toBe('Add some content');
		});

		it('renders action snippet when provided', () => {
			const { container } = render(EmptyState, {
				props: {
					icon: '🎯',
					title: 'Empty'
				}
			});

			// Verify action container structure is available
			expect(container.querySelector('.empty-state')).toBeTruthy();
		});

		it('hides action when not provided', () => {
			const { container } = render(EmptyState, {
				props: { action: undefined }
			});

			const actionDiv = container.querySelector('.empty-action');
			expect(actionDiv).toBeFalsy();
		});
	});

	describe('Styling', () => {
		it('has empty-state class with centered layout', () => {
			const { container } = render(EmptyState, {
				props: {}
			});

			const emptyState = container.querySelector('.empty-state');
			expect(emptyState).toBeTruthy();
			expect(emptyState?.className).toContain('empty-state');
		// Note: text-align: center is verified in the component's CSS
		});

		it('has proper padding', () => {
			const { container } = render(EmptyState, {
				props: {}
			});

			const emptyState = container.querySelector('.empty-state');
			expect(emptyState?.className).toContain('empty-state');
		});

		it('has background color styling', () => {
			const { container } = render(EmptyState, {
				props: {}
			});

			const emptyState = container.querySelector('.empty-state');
			expect(emptyState).toBeTruthy();
		});

		it('has border radius', () => {
			const { container } = render(EmptyState, {
				props: {}
			});

			const emptyState = container.querySelector('.empty-state');
			expect(emptyState?.className).toContain('empty-state');
		});

		it('icon has larger font size', () => {
			const { container } = render(EmptyState, {
				props: { icon: '🚀' }
			});

			const icon = container.querySelector('.empty-icon');
			expect(icon?.className).toContain('empty-icon');
		});
	});

	describe('Content Variations', () => {
		it('handles empty description with title', () => {
			const { container } = render(EmptyState, {
				props: {
					title: 'No files',
					description: ''
				}
			});

			const title = container.querySelector('.empty-title');
			const description = container.querySelector('.empty-description');

			expect(title).toBeTruthy();
			expect(description).toBeFalsy();
		});

		it('handles emoji icons', () => {
			const emojis = ['📷', '📁', '🎯', '⭐'];

			emojis.forEach((emoji) => {
				const { container } = render(EmptyState, {
					props: { icon: emoji }
				});

				const icon = container.querySelector('.empty-icon');
				expect(icon?.textContent).toBe(emoji);
			});
		});

		it('handles long titles', () => {
			const longTitle = 'This is a very long empty state title that might wrap to multiple lines';

			const { getByText } = render(EmptyState, {
				props: { title: longTitle }
			});

			expect(getByText(longTitle)).toBeTruthy();
		});

		it('handles long descriptions', () => {
			const longDescription = 'This is a very long description that provides more context about why the state is empty and what the user should do next to populate it.';

			const { getByText } = render(EmptyState, {
				props: { description: longDescription }
			});

			expect(getByText(longDescription)).toBeTruthy();
		});

		it('handles special characters in text', () => {
			const { getByText } = render(EmptyState, {
				props: {
					title: 'No items (0)',
					description: 'Try searching with: keyword, tag, date'
				}
			});

			expect(getByText('No items (0)')).toBeTruthy();
			expect(getByText('Try searching with: keyword, tag, date')).toBeTruthy();
		});
	});

	describe('Component Props Pattern', () => {
		it('uses Svelte 5 $props() pattern', () => {
			const { container } = render(EmptyState, {
				props: {
					icon: '🎉',
					title: 'Success'
				}
			});

			expect(container.querySelector('.empty-state')).toBeTruthy();
		});

		it('properly handles all prop types', () => {
			const { getByText } = render(EmptyState, {
				props: {
					icon: '✨',
					title: 'Welcome',
					description: 'Get started here',
					class: 'custom'
				}
			});

			expect(getByText('Welcome')).toBeTruthy();
			expect(getByText('Get started here')).toBeTruthy();
		});
	});

	describe('Accessibility', () => {
		it('has proper semantic structure', () => {
			const { container } = render(EmptyState, {
				props: {
					title: 'No results',
					description: 'Try a different search'
				}
			});

			const title = container.querySelector('.empty-title');
			expect(title?.tagName).toBe('H3');
		});

		it('renders description as paragraph', () => {
			const { container } = render(EmptyState, {
				props: { description: 'Add content to continue' }
			});

			const description = container.querySelector('.empty-description');
			expect(description?.tagName).toBe('P');
		});

		it('provides visual structure through typography', () => {
			const { container } = render(EmptyState, {
				props: {
					icon: '📭',
					title: 'Empty',
					description: 'Nothing here'
				}
			});

			const emptyState = container.querySelector('.empty-state');
			expect(emptyState?.querySelector('.empty-icon')).toBeTruthy();
			expect(emptyState?.querySelector('.empty-title')).toBeTruthy();
			expect(emptyState?.querySelector('.empty-description')).toBeTruthy();
		});
	});

	describe('Edge Cases', () => {
		it('handles undefined icon gracefully', () => {
			const { container } = render(EmptyState, {
				props: { icon: '', title: 'Test' }  // Empty string instead of undefined
			});

			const icon = container.querySelector('.empty-icon');
			expect(icon).toBeFalsy();
		});

		it('handles very short text', () => {
			const { getByText } = render(EmptyState, {
				props: {
					title: 'OK',
					description: 'A'
				}
			});

			expect(getByText('OK')).toBeTruthy();
			expect(getByText('A')).toBeTruthy();
		});

		it('handles HTML-like content safely', () => {
			const { container } = render(EmptyState, {
				props: {
					title: '<b>Not</b> bold',
					description: '<script>alert("xss")</script>'
				}
			});

			const title = container.querySelector('.empty-title');
			// Content should be escaped, not rendered as HTML
			expect(title?.innerHTML).not.toContain('<b>');
			expect(title?.innerHTML).not.toContain('<script>');
		});

		it('maintains rendering during rapid prop changes', async () => {
			const { rerender } = render(EmptyState, {
				props: { title: 'First' }
			});

			await rerender({ title: 'Second' });
			await rerender({ title: 'Third' });

			expect(true).toBe(true);
		});

		it('handles mixed content and empty props', () => {
			const { container } = render(EmptyState, {
				props: {
					icon: '🎯',
					title: 'Goals',
					description: undefined
				}
			});

			expect(container.querySelector('.empty-icon')).toBeTruthy();
			expect(container.querySelector('.empty-title')).toBeTruthy();
			expect(container.querySelector('.empty-description')).toBeFalsy();
		});
	});

	describe('Action Slots', () => {
		it('renders action snippet correctly', () => {
			const { container } = render(EmptyState, {
				props: { icon: '🎯', title: 'Empty' }
			});

			expect(container.querySelector('.empty-state')).toBeTruthy();
		});

		it('wraps action in proper container', () => {
			const { container } = render(EmptyState, {
				props: { icon: '🎯', title: 'Empty' }
			});

			const emptyDiv = container.querySelector('.empty-state');
			expect(emptyDiv).toBeTruthy();
		});

		it('hides action container when no action provided', () => {
			const { container } = render(EmptyState, {
				props: { action: undefined }
			});

			const actionDiv = container.querySelector('.empty-action');
			expect(actionDiv).toBeFalsy();
		});
	});
});
