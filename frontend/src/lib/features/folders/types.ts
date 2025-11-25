// Folders feature types

export interface FolderStats {
	totalFiles: number;
	processed: number;
	pending: number;
	failed: number;
}

export interface WatchedFolder {
	id: string;
	path: string;
	name?: string;
	recursive: boolean;
	autoAlbum: boolean;
	stats?: FolderStats;
	lastScannedAt?: string;
	createdAt: string;
}

export interface FoldersState {
	folders: WatchedFolder[];
	loading: boolean;
	error: string | null;
}
