// Search feature types

export interface SearchResult {
	photo: {
		id: string;
		filename: string;
		thumbnailUrl: string;
		description?: string;
	};
	score: number;
	highlights: string[];
}

export interface SearchFilters {
	albumIds?: string[];
	startDate?: string;
	endDate?: string;
	hasFaces?: boolean;
	faceClusterIds?: string[];
	isIndoor?: boolean;
}

export interface SearchState {
	query: string;
	results: SearchResult[];
	filters: SearchFilters;
	loading: boolean;
	error: string | null;
}
