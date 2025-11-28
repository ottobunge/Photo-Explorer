<script lang="ts">
	/**
	 * SimilarityThresholdSlider - A range slider for filtering search results
	 * by minimum similarity score.
	 *
	 * Features:
	 * - Range slider (0-100%)
	 * - Always visible
	 * - Default: 0.18 (18% - filters out very dissimilar results)
	 * - Debounced input to avoid backend spam
	 * - Accessible with proper ARIA attributes
	 */

	interface Props {
		value: number;
		onchange: (value: number) => void;
		debounceMs?: number;
	}

	const { value = 0.18, onchange, debounceMs = 300 }: Props = $props();

	let debounceTimer: number | undefined = $state(undefined);
	let localValue = $state(value);
	let showExplanation = $state(false);

	// Update local value when prop changes
	$effect(() => {
		localValue = value;
	});

	function toggleExplanation(): void {
		showExplanation = !showExplanation;
	}

	// Explanation text for accessibility and info display
	const explanationText =
		'Similarity threshold filters search results based on how closely they match your query. Higher values (closer to 100%) return fewer but more relevant results. Lower values return more results but may include less relevant matches. The default (18%) filters out very dissimilar results while keeping most relevant ones.';

	function handleSliderInput(e: Event): void {
		const target = e.target as HTMLInputElement;
		const newValue = parseFloat(target.value);
		localValue = newValue;

		// Clear existing timer
		if (debounceTimer !== undefined) {
			clearTimeout(debounceTimer);
		}

		// Set new timer
		debounceTimer = setTimeout(() => {
			onchange(newValue);
		}, debounceMs) as unknown as number;
	}

	// Computed percentage for display
	const percentage = $derived(Math.round(localValue * 100));
</script>

<div class="similarity-threshold" data-testid="similarity-threshold">
	<div class="header">
		<div class="label-container">
			<label for="similarity-slider" class="label">
				Similarity Threshold
			</label>
			<button
				type="button"
				class="info-icon"
				onclick={toggleExplanation}
				aria-label="Toggle similarity threshold explanation"
				title="Click for more information"
				data-testid="info-icon"
			>
				ⓘ
			</button>
		</div>
		<span class="value" data-testid="similarity-value">{percentage}%</span>
	</div>

	<div class="slider-container" data-testid="similarity-slider-container">
		<input
			type="range"
			id="similarity-slider"
			min="0"
			max="1"
			step="0.01"
			value={localValue}
			oninput={handleSliderInput}
			data-testid="similarity-slider"
			class="slider"
			aria-label="Similarity threshold percentage"
			aria-describedby="similarity-description similarity-explanation"
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
	<p class="description" id="similarity-description">
		{#if percentage === 0}
			Showing all results (no filtering)
		{:else}
			Only show results with similarity ≥ {percentage}%
		{/if}
	</p>

	{#if showExplanation}
		<div class="explanation" id="similarity-explanation" data-testid="explanation-text">
			<strong>How it works:</strong> {explanationText}
		</div>
	{:else}
		<!-- Hidden element for screen readers -->
		<div id="similarity-explanation" class="sr-only">
			{explanationText}
		</div>
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
		margin-bottom: 0.75rem;
	}

	.label-container {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.label {
		font-size: 0.875rem;
		font-weight: 500;
		color: #374151;
	}

	.info-icon {
		background: none;
		border: none;
		padding: 0;
		margin: 0;
		cursor: pointer;
		font-size: 1rem;
		color: #3b82f6;
		transition: color 0.2s, transform 0.2s;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 1.25rem;
		height: 1.25rem;
	}

	.info-icon:hover {
		color: #2563eb;
		transform: scale(1.1);
	}

	.info-icon:focus {
		outline: 2px solid #3b82f6;
		outline-offset: 2px;
		border-radius: 50%;
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

	.explanation {
		margin-top: 0.5rem;
		font-size: 0.75rem;
		line-height: 1.4;
		color: #4b5563;
		padding: 0.5rem;
		background-color: #f3f4f6;
		border-left: 2px solid #3b82f6;
		border-radius: 0.25rem;
	}

	.explanation strong {
		color: #1f2937;
	}

	/* Screen reader only (for accessibility) */
	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border-width: 0;
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
