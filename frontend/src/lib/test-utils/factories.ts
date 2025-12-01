/**
 * Factory functions for creating type-safe test data.
 * These factories ensure all required properties are present,
 * eliminating TypeScript errors in tests.
 */

import type {
	Photo,
	Album,
	SearchResult,
	Connector,
	UploadItem
} from '$lib/types';
import type {
	FaceClusterType,
	Face,
	FaceGraphData
} from '$lib/features/faces/types';
import type { WatchedFolder } from '$lib/features/folders/types';

// Counter for unique IDs
let idCounter = 0;
const nextId = (): string => `test-id-${++idCounter}`;

// Reset counter between tests
export function resetIdCounter(): void {
	idCounter = 0;
}

/**
 * Create a complete Photo object with all required properties
 */
export function createPhoto(overrides: Partial<Photo> = {}): Photo {
	const id = overrides.id ?? nextId();
	return {
		id,
		filename: `photo-${id}.jpg`,
		thumbnail_url: `/api/thumbnails/${id}`,
		connector_type: 'local',
		width: 1920,
		height: 1080,
		taken_at: '2024-01-15T10:30:00Z',
		created_at: '2024-01-20T14:00:00Z',
		updated_at: '2024-01-20T14:00:00Z',
		file_path: `/photos/${id}.jpg`,
		file_size: 2048000,
		mime_type: 'image/jpeg',
		...overrides
	};
}

/**
 * Create multiple photos
 */
export function createPhotos(count: number, overrides: Partial<Photo> = {}): Photo[] {
	return Array.from({ length: count }, (_, i) =>
		createPhoto({
			...overrides,
			filename: `photo-${i + 1}.jpg`
		})
	);
}

/**
 * Create an Album with all required properties
 */
export function createAlbum(overrides: Partial<Album> = {}): Album {
	const id = overrides.id ?? nextId();
	return {
		id,
		name: `Album ${id}`,
		description: `Description for album ${id}`,
		photoCount: 10,
		createdAt: '2024-01-01T00:00:00Z',
		updatedAt: '2024-01-20T00:00:00Z',
		coverPhotoUrl: `/api/albums/${id}/cover`,
		...overrides
	};
}

/**
 * Create a SearchResult
 */
export function createSearchResult(overrides: Partial<SearchResult> = {}): SearchResult {
	return {
		photo: createPhoto(overrides.photo),
		score: 0.85,
		...overrides
	};
}

/**
 * Create a Connector
 */
export function createConnector(overrides: Partial<Connector> = {}): Connector {
	const id = overrides.id ?? nextId();
	return {
		id,
		type: 'local',
		name: `Local Folder ${id}`,
		status: 'active',
		created_at: '2024-01-01T00:00:00Z',
		config: {},
		...overrides
	};
}

/**
 * Create a WatchedFolder
 */
export function createWatchedFolder(overrides: Partial<WatchedFolder> = {}): WatchedFolder {
	const id = overrides.id ?? nextId();
	return {
		id,
		path: `/home/user/photos/${id}`,
		name: `Folder ${id}`,
		recursive: true,
		autoAlbum: false,
		connectorId: 'local-connector',
		createdAt: '2024-01-01T00:00:00Z',
		stats: {
			totalFiles: 100,
			processed: 95,
			failed: 2,
			pending: 3
		},
		...overrides
	};
}

/**
 * Create a Face
 */
export function createFace(overrides: Partial<Face> = {}): Face {
	const id = overrides.id ?? nextId();
	return {
		id,
		photo_id: `photo-${id}`,
		cluster_id: `cluster-${id}`,
		crop_url: `/api/faces/${id}/crop`,
		confidence: 0.95,
		box: {
			x: 100,
			y: 100,
			width: 200,
			height: 200
		},
		...overrides
	};
}

/**
 * Create a FaceClusterType
 */
export function createFaceCluster(overrides: Partial<FaceClusterType> = {}): FaceClusterType {
	const id = overrides.id ?? nextId();
	return {
		id,
		name: `Person ${id}`,
		faceCount: 25,
		photoCount: 20,
		representativeFace: {
			id: `face-${id}`,
			cropUrl: `/api/faces/${id}/crop`
		},
		...overrides
	};
}

/**
 * Create FaceGraphData
 */
export function createFaceGraphData(
	nodeCount = 5,
	edgeCount = 4
): FaceGraphData {
	const nodes = Array.from({ length: nodeCount }, (_, i) => ({
		id: `person-${i + 1}`,
		label: `Person ${i + 1}`,
		photoUrl: `/api/faces/person-${i + 1}/photo`,
		faceCount: Math.floor(Math.random() * 50) + 10,
		photoCount: Math.floor(Math.random() * 30) + 5
	}));

	const edges = Array.from({ length: edgeCount }, (_, i) => ({
		id: `edge-${i + 1}`,
		source: nodes[i % nodeCount].id,
		target: nodes[(i + 1) % nodeCount].id,
		strength: Math.random() * 0.5 + 0.5
	}));

	return { nodes, edges };
}

/**
 * Create an UploadItem
 */
export function createUploadItem(overrides: Partial<UploadItem> = {}): UploadItem {
	const id = overrides.id ?? nextId();
	return {
		id,
		file: new File(['test'], `upload-${id}.jpg`, { type: 'image/jpeg' }),
		progress: 0,
		status: 'pending',
		error: undefined,
		...overrides
	};
}

/**
 * Builder pattern for complex object creation
 */
export class PhotoBuilder {
	private photo: Photo;

	constructor() {
		this.photo = createPhoto();
	}

	withDimensions(width: number, height: number): this {
		this.photo.width = width;
		this.photo.height = height;
		return this;
	}

	withConnector(type: string): this {
		this.photo.connector_type = type;
		return this;
	}

	withDates(taken: string, created: string): this {
		this.photo.taken_at = taken;
		this.photo.created_at = created;
		return this;
	}

	withScore(score: number): this {
		this.photo.score = score;
		return this;
	}

	build(): Photo {
		return { ...this.photo };
	}
}

export class AlbumBuilder {
	private album: Album;

	constructor() {
		this.album = createAlbum();
	}

	withName(name: string): this {
		this.album.name = name;
		return this;
	}

	withPhotoCount(count: number): this {
		this.album.photoCount = count;
		return this;
	}

	withDescription(description: string): this {
		this.album.description = description;
		return this;
	}

	empty(): this {
		this.album.photoCount = 0;
		this.album.coverPhotoUrl = undefined;
		return this;
	}

	build(): Album {
		return { ...this.album };
	}
}

export class FaceClusterBuilder {
	private cluster: FaceClusterType;

	constructor() {
		this.cluster = createFaceCluster();
	}

	withName(name: string | undefined): this {
		this.cluster.name = name;
		return this;
	}

	unnamed(): this {
		this.cluster.name = undefined;
		return this;
	}

	withCounts(faces: number, photos: number): this {
		this.cluster.faceCount = faces;
		this.cluster.photoCount = photos;
		return this;
	}

	withoutRepresentative(): this {
		this.cluster.representativeFace = undefined;
		return this;
	}

	build(): FaceClusterType {
		return { ...this.cluster };
	}
}

/**
 * Batch creation utilities
 */
export function createPhotoGrid(rows: number, cols: number): Photo[] {
	const photos: Photo[] = [];
	for (let r = 0; r < rows; r++) {
		for (let c = 0; c < cols; c++) {
			photos.push(createPhoto({
				filename: `photo-${r}-${c}.jpg`,
				width: 1920,
				height: 1080
			}));
		}
	}
	return photos;
}

export function createSearchResults(count: number, baseScore = 0.9): SearchResult[] {
	return Array.from({ length: count }, (_, i) =>
		createSearchResult({
			score: baseScore - (i * 0.05)
		})
	);
}

/**
 * Common test scenarios
 */
export const TestScenarios = {
	emptyGallery: (): Photo[] => [],

	singlePhoto: (): Photo[] => [createPhoto()],

	photoGallery: (): Photo[] => createPhotos(12),

	mixedConnectorPhotos: (): Photo[] => [
		createPhoto({ connector_type: 'local' }),
		createPhoto({ connector_type: 'google_photos' }),
		createPhoto({ connector_type: 'dropbox' })
	],

	searchResultsWithScores: (): SearchResult[] => [
		createSearchResult({ score: 0.95 }),
		createSearchResult({ score: 0.85 }),
		createSearchResult({ score: 0.75 }),
		createSearchResult({ score: 0.65 })
	],

	namedAndUnnamedClusters: (): FaceClusterType[] => [
		createFaceCluster({ name: 'Alice' }),
		createFaceCluster({ name: 'Bob' }),
		createFaceCluster({ name: undefined }),
		createFaceCluster({ name: undefined })
	],

	uploadQueue: (): UploadItem[] => [
		createUploadItem({ status: 'completed', progress: 100 }),
		createUploadItem({ status: 'uploading', progress: 45 }),
		createUploadItem({ status: 'pending', progress: 0 }),
		createUploadItem({ status: 'failed', progress: 30, error: 'Network error' })
	]
};

/**
 * Type guards for test assertions
 */
export function isPhoto(obj: unknown): obj is Photo {
	return obj !== null &&
		typeof obj === 'object' &&
		'id' in obj &&
		'filename' in obj;
}

export function isFaceCluster(obj: unknown): obj is FaceClusterType {
	return obj !== null &&
		typeof obj === 'object' &&
		'id' in obj &&
		'faceCount' in obj;
}