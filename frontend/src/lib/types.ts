/**
 * Shared type definitions used across the frontend application.
 * These types define the core domain models.
 */

export interface Photo {
	id: string;
	filename: string;
	thumbnail_url: string | null;
	connector_type: string;
	width: number | null;
	height: number | null;
	taken_at: string | null;
	created_at: string;
	updated_at?: string;
	file_path?: string;
	file_size?: number;
	mime_type?: string;
	score?: number; // Used in search results
}

export interface Album {
	id: string;
	name: string;
	description: string | null;
	photoCount: number;
	createdAt: string;
	updatedAt: string;
	coverPhotoUrl?: string;
}

export interface SearchResult {
	photo: Photo;
	score: number;
}

export interface Connector {
	id: string;
	type: string;
	name: string;
	status: 'active' | 'inactive' | 'error';
	created_at: string;
	config: Record<string, unknown>;
}

export interface UploadItem {
	id: string;
	file: File;
	progress: number;
	status: 'pending' | 'uploading' | 'completed' | 'failed';
	error?: string;
}

export interface ApiResponse<T> {
	success: boolean;
	data: T;
	meta?: {
		total?: number;
		page?: number;
		per_page?: number;
	};
}

export interface ApiError {
	code: string;
	message: string;
	details?: Record<string, unknown>;
}