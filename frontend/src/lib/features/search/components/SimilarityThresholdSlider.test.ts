import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, fireEvent, screen, waitFor } from '@testing-library/svelte';
import SimilarityThresholdSlider from './SimilarityThresholdSlider.svelte';

describe('SimilarityThresholdSlider', () => {
	// Mock timers for debounce testing
	beforeEach(() => {
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.restoreAllMocks();
		vi.useRealTimers();
	});

	describe('Rendering', () => {
		it('should render with default value (18%)', () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			// Check that the component is rendered
			const container = screen.getByTestId('similarity-threshold');
			expect(container).toBeTruthy();

			// Check that the default value is displayed
			const valueDisplay = screen.getByTestId('similarity-value');
			expect(valueDisplay.textContent).toBe('18%');
		});

		it('should render slider with correct attributes', () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			const slider = screen.getByTestId('similarity-slider') as HTMLInputElement;

			// Check slider attributes
			expect(slider.type).toBe('range');
			expect(slider.min).toBe('0');
			expect(slider.max).toBe('1');
			expect(slider.step).toBe('0.01');
			expect(slider.value).toBe('0.18');
		});

		it('should have proper accessibility attributes', () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.25, onchange } });

			const slider = screen.getByTestId('similarity-slider');

			// Check ARIA attributes
			expect(slider.getAttribute('aria-label')).toBe('Similarity threshold percentage');
			expect(slider.getAttribute('aria-describedby')).toContain('similarity-description');
			expect(slider.getAttribute('aria-describedby')).toContain('similarity-explanation');
			expect(slider.getAttribute('aria-valuemin')).toBe('0');
			expect(slider.getAttribute('aria-valuemax')).toBe('100');
			expect(slider.getAttribute('aria-valuenow')).toBe('25');
			expect(slider.getAttribute('aria-valuetext')).toBe('25%');
		});

		it('should display min/max labels', () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			// Check that labels are present
			const labels = screen.getByTestId('similarity-slider-container');
			expect(labels.textContent).toContain('0%');
			expect(labels.textContent).toContain('50%');
			expect(labels.textContent).toContain('100%');
		});
	});

	describe('Value Display', () => {
		it('should display correct percentage for default value (18%)', () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			const valueDisplay = screen.getByTestId('similarity-value');
			expect(valueDisplay.textContent).toBe('18%');
		});

		it('should display 0% when value is 0', () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0, onchange } });

			const valueDisplay = screen.getByTestId('similarity-value');
			expect(valueDisplay.textContent).toBe('0%');
		});

		it('should display 100% when value is 1', () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 1, onchange } });

			const valueDisplay = screen.getByTestId('similarity-value');
			expect(valueDisplay.textContent).toBe('100%');
		});

		it('should display 50% when value is 0.5', () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.5, onchange } });

			const valueDisplay = screen.getByTestId('similarity-value');
			expect(valueDisplay.textContent).toBe('50%');
		});

		it('should round percentage to nearest integer', () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.456, onchange } });

			const valueDisplay = screen.getByTestId('similarity-value');
			expect(valueDisplay.textContent).toBe('46%'); // 45.6 rounds to 46
		});
	});

	describe('Description Text', () => {
		it('should show "Showing all results" when value is 0', () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0, onchange } });

			const description = screen.getByText(/showing all results/i);
			expect(description).toBeTruthy();
			expect(description.textContent).toContain('no filtering');
		});

		it('should show "Only show results with similarity ≥ X%" when value > 0', () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			const description = screen.getByText(/only show results with similarity ≥ 18%/i);
			expect(description).toBeTruthy();
		});

		it('should update description text when value changes', async () => {
			const onchange = vi.fn();
			const { rerender } = render(SimilarityThresholdSlider, {
				props: { value: 0.18, onchange }
			});

			// Verify initial description
			expect(screen.getByText(/only show results with similarity ≥ 18%/i)).toBeTruthy();

			// Update value to 0
			rerender({ value: 0, onchange });

			// Wait for update
			await waitFor(() => {
				expect(screen.getByText(/showing all results/i)).toBeTruthy();
			});
		});
	});

	describe('Slider Interaction', () => {
		it('should trigger onChange callback when slider value changes', async () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			const slider = screen.getByTestId('similarity-slider');

			// Simulate input event
			await fireEvent.input(slider, { target: { value: '0.5' } });

			// Fast-forward debounce timer
			vi.advanceTimersByTime(300);

			// Check that onChange was called with new value
			expect(onchange).toHaveBeenCalledTimes(1);
			expect(onchange).toHaveBeenCalledWith(0.5);
		});

		it('should update local value immediately on slider input', async () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			const slider = screen.getByTestId('similarity-slider');
			const valueDisplay = screen.getByTestId('similarity-value');

			// Simulate input event
			await fireEvent.input(slider, { target: { value: '0.75' } });

			// Value display should update immediately (before debounce)
			expect(valueDisplay.textContent).toBe('75%');

			// But onChange should not be called yet
			expect(onchange).not.toHaveBeenCalled();
		});

		it('should update slider value when prop changes', async () => {
			const onchange = vi.fn();
			const { rerender } = render(SimilarityThresholdSlider, {
				props: { value: 0.18, onchange }
			});

			const slider = screen.getByTestId('similarity-slider') as HTMLInputElement;
			expect(slider.value).toBe('0.18');

			// Update prop
			rerender({ value: 0.5, onchange });

			// Wait for update
			await waitFor(() => {
				expect(slider.value).toBe('0.5');
			});
		});
	});

	describe('User Interaction Workflow', () => {
		it('should notify parent component only after user stops adjusting slider', async () => {
			// BEHAVIOR: When user rapidly adjusts slider, parent should only get final value
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			const slider = screen.getByTestId('similarity-slider');

			// User rapidly adjusts the slider (drags it quickly)
			await fireEvent.input(slider, { target: { value: '0.6' } });
			await fireEvent.input(slider, { target: { value: '0.7' } });
			await fireEvent.input(slider, { target: { value: '0.8' } });

			// Parent should not be notified while user is still adjusting
			expect(onchange).not.toHaveBeenCalled();

			// User stops adjusting (waits for debounce to complete)
			vi.advanceTimersByTime(300);

			// Now parent gets the final value
			expect(onchange).toHaveBeenCalledTimes(1);
			expect(onchange).toHaveBeenCalledWith(0.8);
		});

		it('should provide immediate visual feedback while delaying parent notification', async () => {
			// BEHAVIOR: UI updates instantly, but parent notification is delayed
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			const slider = screen.getByTestId('similarity-slider');
			const valueDisplay = screen.getByTestId('similarity-value');

			// User drags slider
			await fireEvent.input(slider, { target: { value: '0.75' } });

			// Visual feedback is immediate
			expect(valueDisplay.textContent).toBe('75%');

			// But parent is not notified yet
			expect(onchange).not.toHaveBeenCalled();

			// After user stops
			vi.advanceTimersByTime(300);

			// Parent is notified
			expect(onchange).toHaveBeenCalledWith(0.75);
		});
	});

	describe('Info Icon and Explanation', () => {
		it('should render info icon button', () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			const infoIcon = screen.getByTestId('info-icon');
			expect(infoIcon).toBeTruthy();
			expect(infoIcon.getAttribute('aria-label')).toBe(
				'Toggle similarity threshold explanation'
			);
		});

		it('should toggle explanation visibility on info icon click', async () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			const infoIcon = screen.getByTestId('info-icon');

			// Initially, explanation should not be visible
			let explanationText = screen.queryByTestId('explanation-text');
			expect(explanationText).toBeFalsy();

			// Click info icon to show explanation
			await fireEvent.click(infoIcon);

			// Explanation should now be visible
			explanationText = screen.getByTestId('explanation-text');
			expect(explanationText).toBeTruthy();
			expect(explanationText.textContent).toContain('How it works:');

			// Click again to hide explanation
			await fireEvent.click(infoIcon);

			// Explanation should be hidden again
			explanationText = screen.queryByTestId('explanation-text');
			expect(explanationText).toBeFalsy();
		});

		it('should always have explanation text in DOM for screen readers', () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			// Check that explanation text is in DOM with id="similarity-explanation"
			const explanation = document.getElementById('similarity-explanation');
			expect(explanation).toBeTruthy();

			// The text should contain the explanation content
			const explanationText =
				'Similarity threshold filters search results based on how closely they match your query';
			expect(explanation?.textContent).toContain(explanationText);
		});

		it('should display detailed explanation when visible', async () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			const infoIcon = screen.getByTestId('info-icon');
			await fireEvent.click(infoIcon);

			const explanation = screen.getByTestId('explanation-text');

			// Check that explanation contains key information
			expect(explanation.textContent).toContain('How it works:');
			expect(explanation.textContent).toContain('Similarity threshold filters search results');
			expect(explanation.textContent).toContain('Higher values');
			expect(explanation.textContent).toContain('Lower values');
			expect(explanation.textContent).toContain('default (18%)');
		});

		it('should use sr-only class when explanation is hidden', () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			const explanation = document.getElementById('similarity-explanation');
			expect(explanation?.className).toContain('sr-only');
		});

		it('should not use sr-only class when explanation is visible', async () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			const infoIcon = screen.getByTestId('info-icon');
			await fireEvent.click(infoIcon);

			const explanation = document.getElementById('similarity-explanation');
			expect(explanation?.className).not.toContain('sr-only');
		});
	});

	describe('Edge Cases', () => {
		it('should handle minimum value (0)', async () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0, onchange } });

			const slider = screen.getByTestId('similarity-slider') as HTMLInputElement;
			const valueDisplay = screen.getByTestId('similarity-value');

			expect(slider.value).toBe('0');
			expect(valueDisplay.textContent).toBe('0%');
		});

		it('should handle maximum value (1)', async () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 1, onchange } });

			const slider = screen.getByTestId('similarity-slider') as HTMLInputElement;
			const valueDisplay = screen.getByTestId('similarity-value');

			expect(slider.value).toBe('1');
			expect(valueDisplay.textContent).toBe('100%');
		});

		it('should handle fractional values correctly', async () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.333, onchange } });

			const valueDisplay = screen.getByTestId('similarity-value');
			expect(valueDisplay.textContent).toBe('33%'); // 33.3 rounds to 33
		});

		it('should handle onChange callback being called with exact slider value', async () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			const slider = screen.getByTestId('similarity-slider');

			// Set a precise fractional value
			await fireEvent.input(slider, { target: { value: '0.456' } });
			vi.advanceTimersByTime(300);

			expect(onchange).toHaveBeenCalledWith(0.456);
		});
	});

	describe('Parent-Driven Updates', () => {
		it('should reflect value changes from parent component', async () => {
			const onchange = vi.fn();
			const { rerender } = render(SimilarityThresholdSlider, {
				props: { value: 0.18, onchange }
			});

			const valueDisplay = screen.getByTestId('similarity-value');
			expect(valueDisplay.textContent).toBe('18%');

			// Update prop from parent
			rerender({ value: 0.75, onchange });

			await waitFor(() => {
				expect(valueDisplay.textContent).toBe('75%');
			});
		});
	});

	describe('Accessibility', () => {
		it('should have label for slider', () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			const label = screen.getByText('Similarity Threshold');
			expect(label.tagName).toBe('LABEL');

			const slider = screen.getByTestId('similarity-slider');
			expect(label.getAttribute('for')).toBe(slider.id);
		});

		it('should update aria-valuenow when value changes', async () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			const slider = screen.getByTestId('similarity-slider');

			expect(slider.getAttribute('aria-valuenow')).toBe('18');

			await fireEvent.input(slider, { target: { value: '0.6' } });

			await waitFor(() => {
				expect(slider.getAttribute('aria-valuenow')).toBe('60');
			});
		});

		it('should update aria-valuetext when value changes', async () => {
			const onchange = vi.fn();
			render(SimilarityThresholdSlider, { props: { value: 0.18, onchange } });

			const slider = screen.getByTestId('similarity-slider');

			expect(slider.getAttribute('aria-valuetext')).toBe('18%');

			await fireEvent.input(slider, { target: { value: '0.6' } });

			await waitFor(() => {
				expect(slider.getAttribute('aria-valuetext')).toBe('60%');
			});
		});
	});
});
