// Search feature - Public exports

export { default as SearchBar } from './components/SearchBar.svelte';
export { default as SearchResults } from './components/SearchResults.svelte';
export { default as SearchFilters } from './components/SearchFilters.svelte';
export { default as SimilarityThresholdSlider } from './components/SimilarityThresholdSlider.svelte';
export { searchStore } from './stores/search.svelte';
export type { SearchResult, SearchFilters as SearchFiltersType } from './types';
