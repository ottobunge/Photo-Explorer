// Photos feature types

export interface Photo {
	id: string;
	filename: string;
	thumbnail_url: string | null;
	connector_type: string;
	width: number | null;
	height: number | null;
	taken_at: string | null;
	created_at: string;
	score?: number;
}

export interface PhotosState {
	photos: Photo[];
	loading: boolean;
	error: string | null;
	total: number;
	currentPage: number;
	perPage: number;
}
