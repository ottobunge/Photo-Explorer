<script lang="ts">
	type TabType = 'list' | 'graph';

	interface Props {
		activeTab: TabType;
	}

	const { activeTab }: Props = $props();
</script>

<div class="tabs-container" role="tablist" aria-label="Face Explorer Views">
	<a
		href="/faces"
		role="tab"
		aria-selected={activeTab === 'list'}
		aria-controls="list-panel"
		class="tab"
		class:active={activeTab === 'list'}
		data-testid="list-tab"
	>
		<svg
			class="tab-icon"
			fill="none"
			stroke="currentColor"
			viewBox="0 0 24 24"
			xmlns="http://www.w3.org/2000/svg"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				stroke-width="2"
				d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
			/>
		</svg>
		<span>List</span>
	</a>

	<a
		href="/faces?view=graph"
		role="tab"
		aria-selected={activeTab === 'graph'}
		aria-controls="graph-panel"
		class="tab"
		class:active={activeTab === 'graph'}
		data-testid="graph-tab"
	>
		<svg
			class="tab-icon"
			fill="none"
			stroke="currentColor"
			viewBox="0 0 24 24"
			xmlns="http://www.w3.org/2000/svg"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				stroke-width="2"
				d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
			/>
		</svg>
		<span>Graph</span>
	</a>
</div>

<style>
	.tabs-container {
		display: flex;
		gap: 0.5rem;
		border-bottom: 2px solid #e5e7eb;
		margin-bottom: 2rem;
	}

	.tab {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1.5rem;
		background: none;
		border: none;
		border-bottom: 3px solid transparent;
		color: #6b7280;
		font-weight: 500;
		font-size: 0.875rem;
		cursor: pointer;
		transition: all 0.2s;
		margin-bottom: -2px;
	}

	.tab:hover {
		color: #4f46e5;
		background: #f9fafb;
	}

	.tab.active {
		color: #4f46e5;
		border-bottom-color: #4f46e5;
	}

	.tab-icon {
		width: 1.25rem;
		height: 1.25rem;
	}

	@media (max-width: 640px) {
		.tab span {
			display: none;
		}
	}
</style>
