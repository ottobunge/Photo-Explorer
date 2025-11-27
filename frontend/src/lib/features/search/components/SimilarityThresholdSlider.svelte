<script lang="ts">
	/**
	 * SimilarityThresholdSlider - A toggleable slider component for filtering search results
	 * by minimum similarity score.
	 *
	 * Features:
	 * - Toggle to enable/disable similarity filtering
	 * - Range slider (0-100%)
	 * - Visual percentage display
	 * - Maintains value when toggling on/off
	 * - Accessible with proper ARIA attributes
	 */

	interface Props {
		value: number | null;
		onchange: (value: number | null) => void;
	}

	let { value = null, onchange }: Props = $props();

	// Internal state
	let enabled = $state(value !== null);
	let sliderValue = $state(value ?? 0.5);

	// Sync enabled state when value prop changes
	$effect(() => {
		if (value !== null) {
			enabled = true;
			sliderValue = value;
		}
	});

	function handleToggle(): void {
		enabled = !enabled;
		onchange(enabled ? sliderValue : null);
	}

	function handleSliderChange(e: Event): void {
		const target = e.target as HTMLInputElement;
		sliderValue = parseFloat(target.value);
		if (enabled) {
			onchange(sliderValue);
		}
	}

	// Computed percentage for display
	const percentage = $derived(Math.round(sliderValue * 100));
</script>

<div class="similarity-threshold" data-testid="similarity-threshold">
	<div class="header">
		<label for="similarity-toggle" class="toggle-label">
			<input
				type="checkbox"
				id="similarity-toggle"
				data-testid="similarity-toggle"
				bind:checked={enabled}
				onchange={handleToggle}
				class="toggle-checkbox"
			/>
			<span class="label-text">Similarity Threshold</span>
		</label>
		{#if enabled}
			<span class="value" data-testid="similarity-value">{percentage}%</span>
		{/if}
	</div>

	{#if enabled}
		<div class="slider-container" data-testid="similarity-slider-container">
			<input
				type="range"
				min="0"
				max="1"
				step="0.01"
				value={sliderValue}
				oninput={handleSliderChange}
				data-testid="similarity-slider"
				class="slider"
				aria-label="Similarity threshold percentage"
				aria-valuemin="0"
				aria-valuemax="100"
				aria-valuenow={percentage}
				aria-valuetext="{percentage}%"
			/>
			<div class="labels">
				<span class="label-min">0%</span>
				<span class="label-mid">50%</span>
				<span class="label-max">100%</span>
			</div>
		</div>
		<p class="description">
			Only show results with similarity ≥ {percentage}%
		</p>
	{/if}
</div>

<style>
	.similarity-threshold {
		margin: 1rem 0;
		padding: 1rem;
		border-radius: 0.5rem;
		background-color: #f9fafb;
		border: 1px solid #e5e7eb;
	}

	.header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.toggle-label {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		cursor: pointer;
		font-size: 0.875rem;
		font-weight: 500;
		color: #374151;
		user-select: none;
	}

	.toggle-checkbox {
		width: 1rem;
		height: 1rem;
		cursor: pointer;
		accent-color: #3b82f6;
	}

	.label-text {
		font-size: 0.875rem;
		font-weight: 500;
		color: #374151;
	}

	.value {
		font-size: 0.875rem;
		font-weight: 600;
		color: #3b82f6;
		background-color: #dbeafe;
		padding: 0.25rem 0.75rem;
		border-radius: 0.375rem;
	}

	.slider-container {
		margin-top: 0.75rem;
		padding: 0 0.25rem;
	}

	.slider {
		width: 100%;
		height: 0.5rem;
		border-radius: 0.25rem;
		background: linear-gradient(to right, #e5e7eb 0%, #3b82f6 100%);
		outline: none;
		appearance: none;
		-webkit-appearance: none;
		cursor: pointer;
	}

	.slider::-webkit-slider-thumb {
		appearance: none;
		-webkit-appearance: none;
		width: 1.25rem;
		height: 1.25rem;
		border-radius: 50%;
		background: #3b82f6;
		border: 2px solid white;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
		cursor: pointer;
		transition: transform 0.2s;
	}

	.slider::-webkit-slider-thumb:hover {
		transform: scale(1.1);
	}

	.slider::-moz-range-thumb {
		width: 1.25rem;
		height: 1.25rem;
		border-radius: 50%;
		background: #3b82f6;
		border: 2px solid white;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
		cursor: pointer;
		transition: transform 0.2s;
	}

	.slider::-moz-range-thumb:hover {
		transform: scale(1.1);
	}

	.labels {
		display: flex;
		justify-content: space-between;
		margin-top: 0.5rem;
		font-size: 0.75rem;
		color: #6b7280;
	}

	.label-min,
	.label-mid,
	.label-max {
		flex: 1;
	}

	.label-min {
		text-align: left;
	}

	.label-mid {
		text-align: center;
	}

	.label-max {
		text-align: right;
	}

	.description {
		margin-top: 0.75rem;
		font-size: 0.75rem;
		color: #6b7280;
		font-style: italic;
	}

	/* Responsive adjustments */
	@media (max-width: 640px) {
		.similarity-threshold {
			padding: 0.75rem;
		}

		.header {
			flex-direction: column;
			align-items: flex-start;
			gap: 0.5rem;
		}

		.value {
			align-self: flex-start;
		}
	}
</style>
