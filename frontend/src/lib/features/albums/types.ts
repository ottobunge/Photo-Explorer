// Albums feature types

export interface Album {
	id: string;
	name: string;
	description?: string;
	coverPhotoUrl?: string;
	photoCount: number;
	createdAt: string;
}

export interface AlbumsState {
	albums: Album[];
	loading: boolean;
	error: string | null;
}
