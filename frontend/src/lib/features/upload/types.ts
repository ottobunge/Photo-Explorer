// Upload feature types

export interface UploadItem {
	id: string;
	file: File;
	progress: number;
	status: 'pending' | 'uploading' | 'completed' | 'failed';
	error?: string;
}

export interface UploadState {
	items: UploadItem[];
	uploading: boolean;
}
