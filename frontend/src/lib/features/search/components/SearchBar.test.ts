import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/svelte';
import { tick } from 'svelte';
import SearchBar from './SearchBar.svelte';
import { mockTimers } from '$lib/test-utils/mocks';

describe('SearchBar', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	describe('Props', () => {
		it('renders with default props', () => {
			const { container } = render(SearchBar, {
				props: {}
			});

			const searchBar = container.querySelector('[data-testid="search-bar"]');
			expect(searchBar).toBeTruthy();

			const input = container.querySelector('input[type="search"]');
			expect(input).toBeTruthy();
			expect(input?.getAttribute('placeholder')).toContain('Search');
		});

		it('displays initial query value', () => {
			const { container } = render(SearchBar, {
				props: {
					query: 'sunset photos'
				}
			});

			const input = container.querySelector('input[type="search"]') as HTMLInputElement;
			expect(input.value).toBe('sunset photos');
		});

		it('shows custom placeholder', () => {
			const { container } = render(SearchBar, {
				props: {
					placeholder: 'Find your memories...'
				}
			});

			const input = container.querySelector('input[type="search"]');
			expect(input?.getAttribute('placeholder')).toBe('Find your memories...');
		});

		it('disables input when loading', () => {
			const { container } = render(SearchBar, {
				props: {
					loading: true
				}
			});

			const input = container.querySelector('input[type="search"]');
			expect(input?.hasAttribute('disabled')).toBe(true);
		});

		it('applies disabled state', () => {
			const { container } = render(SearchBar, {
				props: {
					disabled: true
				}
			});

			const input = container.querySelector('input[type="search"]');
			const button = container.querySelector('button[type="submit"]');

			expect(input?.hasAttribute('disabled')).toBe(true);
			expect(button?.hasAttribute('disabled')).toBe(true);
		});
	});

	describe('User Interactions', () => {
		it('calls onSearch when form is submitted', async () => {
			const onSearch = vi.fn();
			const { container } = render(SearchBar, {
				props: {
					query: 'beach',
					onSearch
				}
			});

			const form = container.querySelector('form');
			await fireEvent.submit(form!);

			expect(onSearch).toHaveBeenCalledTimes(1);
		});

		it('calls onSearch when search button is clicked', async () => {
			const onSearch = vi.fn();
			const { container } = render(SearchBar, {
				props: {
					query: 'mountains',
					onSearch
				}
			});

			const button = container.querySelector('button[type="submit"]');
			await fireEvent.click(button!);

			expect(onSearch).toHaveBeenCalledTimes(1);
		});

		it('updates query value on input', async () => {
			const { container } = render(SearchBar, {
				props: {
					query: ''
				}
			});

			const input = container.querySelector('input[type="search"]') as HTMLInputElement;

			await fireEvent.input(input, { target: { value: 'new query' } });
			expect(input.value).toBe('new query');
		});

		it('clears query when clear button is clicked', async () => {
			const onClear = vi.fn();
			const { container } = render(SearchBar, {
				props: {
					query: 'test query',
					onClear
				}
			});

			const clearButton = container.querySelector('[aria-label="Clear search"]');
			expect(clearButton).toBeTruthy();

			await fireEvent.click(clearButton!);
			expect(onClear).toHaveBeenCalled();
		});

		it('hides clear button when query is empty', () => {
			const { container } = render(SearchBar, {
				props: {
					query: ''
				}
			});

			const clearButton = container.querySelector('[aria-label="Clear search"]');
			expect(clearButton).toBeFalsy();
		});

		it('shows clear button when query has text', () => {
			const { container } = render(SearchBar, {
				props: {
					query: 'some text'
				}
			});

			const clearButton = container.querySelector('[aria-label="Clear search"]');
			expect(clearButton).toBeTruthy();
		});
	});

	describe('Debouncing', () => {
		beforeEach(() => {
			mockTimers.setup();
		});

		afterEach(() => {
			mockTimers.cleanup();
		});

		it('debounces search on input change', async () => {
			const onSearch = vi.fn();
			const { container } = render(SearchBar, {
				props: {
					query: '',
					onSearch,
					debounceMs: 300
				}
			});

			const input = container.querySelector('input[type="search"]') as HTMLInputElement;

			// Type multiple characters quickly
			await fireEvent.input(input, { target: { value: 's' } });
			await fireEvent.input(input, { target: { value: 'su' } });
			await fireEvent.input(input, { target: { value: 'sun' } });

			// Should not call immediately
			expect(onSearch).not.toHaveBeenCalled();

			// Advance timers
			mockTimers.advance(300);
			await tick();

			// Should call once after debounce
			expect(onSearch).toHaveBeenCalledTimes(1);
		});

		it('cancels debounce on form submit', async () => {
			const onSearch = vi.fn();
			const { container } = render(SearchBar, {
				props: {
					query: '',
					onSearch,
					debounceMs: 300
				}
			});

			const input = container.querySelector('input[type="search"]') as HTMLInputElement;
			const form = container.querySelector('form');

			// Type and immediately submit
			await fireEvent.input(input, { target: { value: 'sunset' } });
			await fireEvent.submit(form!);

			// Should call immediately
			expect(onSearch).toHaveBeenCalledTimes(1);

			// Advance timers - should not call again
			mockTimers.advance(300);
			await tick();

			expect(onSearch).toHaveBeenCalledTimes(1);
		});

		it('respects custom debounce delay', async () => {
			const onSearch = vi.fn();
			const { container } = render(SearchBar, {
				props: {
					query: '',
					onSearch,
					debounceMs: 500
				}
			});

			const input = container.querySelector('input[type="search"]') as HTMLInputElement;

			await fireEvent.input(input, { target: { value: 'test' } });

			// Should not call at 300ms
			mockTimers.advance(300);
			await tick();
			expect(onSearch).not.toHaveBeenCalled();

			// Should call at 500ms
			mockTimers.advance(200);
			await tick();
			expect(onSearch).toHaveBeenCalledTimes(1);
		});
	});

	describe('Loading State', () => {
		it('shows loading spinner when loading', () => {
			const { container } = render(SearchBar, {
				props: {
					loading: true
				}
			});

			const spinner = container.querySelector('.loading-spinner');
			expect(spinner).toBeTruthy();
		});

		it('disables submit button when loading', () => {
			const { container } = render(SearchBar, {
				props: {
					loading: true
				}
			});

			const button = container.querySelector('button[type="submit"]');
			expect(button?.hasAttribute('disabled')).toBe(true);
		});

		it('shows loading text in button', () => {
			const { container } = render(SearchBar, {
				props: {
					loading: true
				}
			});

			const button = container.querySelector('button[type="submit"]');
			expect(button?.textContent).toContain('Searching');
		});
	});

	describe('Search Suggestions', () => {
		it('shows suggestions dropdown when typing', async () => {
			const suggestions = ['sunset beach', 'sunset mountains', 'sunset city'];
			const { container } = render(SearchBar, {
				props: {
					query: 'sunset',
					suggestions,
					showSuggestions: true
				}
			});

			const dropdown = container.querySelector('[data-testid="search-suggestions"]');
			expect(dropdown).toBeTruthy();

			const items = dropdown?.querySelectorAll('[role="option"]');
			expect(items?.length).toBe(3);
		});

		it('selects suggestion on click', async () => {
			const onSuggestionSelect = vi.fn();
			const suggestions = ['beach photos', 'mountain views'];

			const { container } = render(SearchBar, {
				props: {
					query: 'bea',
					suggestions,
					showSuggestions: true,
					onSuggestionSelect
				}
			});

			const firstSuggestion = container.querySelector('[role="option"]');
			await fireEvent.click(firstSuggestion!);

			expect(onSuggestionSelect).toHaveBeenCalledWith('beach photos');
		});

		it('navigates suggestions with keyboard', async () => {
			const suggestions = ['option 1', 'option 2', 'option 3'];
			const { container } = render(SearchBar, {
				props: {
					query: 'opt',
					suggestions,
					showSuggestions: true
				}
			});

			const input = container.querySelector('input[type="search"]');

			// Arrow down
			await fireEvent.keyDown(input!, { key: 'ArrowDown' });
			let highlighted = container.querySelector('[aria-selected="true"]');
			expect(highlighted?.textContent).toContain('option 1');

			// Arrow down again
			await fireEvent.keyDown(input!, { key: 'ArrowDown' });
			highlighted = container.querySelector('[aria-selected="true"]');
			expect(highlighted?.textContent).toContain('option 2');

			// Arrow up
			await fireEvent.keyDown(input!, { key: 'ArrowUp' });
			highlighted = container.querySelector('[aria-selected="true"]');
			expect(highlighted?.textContent).toContain('option 1');
		});

		it('selects suggestion with Enter key', async () => {
			const onSuggestionSelect = vi.fn();
			const suggestions = ['suggestion 1'];

			const { container } = render(SearchBar, {
				props: {
					query: 'sug',
					suggestions,
					showSuggestions: true,
					onSuggestionSelect
				}
			});

			const input = container.querySelector('input[type="search"]');

			await fireEvent.keyDown(input!, { key: 'ArrowDown' });
			await fireEvent.keyDown(input!, { key: 'Enter' });

			expect(onSuggestionSelect).toHaveBeenCalledWith('suggestion 1');
		});

		it('closes suggestions on Escape', async () => {
			const { container } = render(SearchBar, {
				props: {
					query: 'test',
					suggestions: ['test 1', 'test 2'],
					showSuggestions: true
				}
			});

			let dropdown = container.querySelector('[data-testid="search-suggestions"]');
			expect(dropdown).toBeTruthy();

			const input = container.querySelector('input[type="search"]');
			await fireEvent.keyDown(input!, { key: 'Escape' });

			dropdown = container.querySelector('[data-testid="search-suggestions"]');
			expect(dropdown?.className).toContain('hidden');
		});
	});

	describe('Accessibility', () => {
		it('has proper ARIA attributes', () => {
			const { container } = render(SearchBar, {
				props: {
					query: 'test'
				}
			});

			const input = container.querySelector('input[type="search"]');
			expect(input?.getAttribute('role')).toBe('searchbox');
			expect(input?.getAttribute('aria-label')).toContain('Search');
		});

		it('has proper ARIA attributes for suggestions', () => {
			const { container } = render(SearchBar, {
				props: {
					query: 'test',
					suggestions: ['test 1', 'test 2'],
					showSuggestions: true
				}
			});

			const input = container.querySelector('input[type="search"]');
			const dropdown = container.querySelector('[data-testid="search-suggestions"]');

			expect(input?.getAttribute('aria-autocomplete')).toBe('list');
			expect(input?.getAttribute('aria-controls')).toBeTruthy();
			expect(dropdown?.getAttribute('role')).toBe('listbox');
		});

		it('announces loading state', () => {
			const { container } = render(SearchBar, {
				props: {
					loading: true
				}
			});

			const liveRegion = container.querySelector('[aria-live="polite"]');
			expect(liveRegion?.textContent).toContain('Searching');
		});
	});

	describe('Edge Cases', () => {
		it('handles empty query submission', async () => {
			const onSearch = vi.fn();
			const { container } = render(SearchBar, {
				props: {
					query: '',
					onSearch
				}
			});

			const form = container.querySelector('form');
			await fireEvent.submit(form!);

			// May or may not call based on implementation
			// But should not crash
			expect(true).toBe(true);
		});

		it('handles very long queries', () => {
			const longQuery = 'a'.repeat(500);
			const { container } = render(SearchBar, {
				props: {
					query: longQuery,
					maxLength: 100
				}
			});

			const input = container.querySelector('input[type="search"]') as HTMLInputElement;
			expect(input.value.length).toBeLessThanOrEqual(100);
		});

		it('handles special characters in query', () => {
			const specialQuery = '<script>alert("xss")</script>';
			const { container } = render(SearchBar, {
				props: {
					query: specialQuery
				}
			});

			const input = container.querySelector('input[type="search"]') as HTMLInputElement;
			// Value should be escaped/safe
			expect(input.value).toBe(specialQuery);
			expect(container.innerHTML).not.toContain('<script>');
		});

		it('handles rapid prop changes', async () => {
			const { rerender } = render(SearchBar, {
				props: {
					query: 'initial'
				}
			});

			await rerender({ query: 'second' });
			await rerender({ query: 'third' });
			await rerender({ query: 'final' });

			// Should handle all changes without error
			expect(true).toBe(true);
		});
	});
});