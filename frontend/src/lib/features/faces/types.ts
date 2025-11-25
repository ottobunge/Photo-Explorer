// Faces feature types

export interface Face {
	id: string;
	photoId: string;
	cropUrl: string;
	clusterId?: string;
}

export interface FaceClusterType {
	id: string;
	name?: string;
	faceCount: number;
	photoCount: number;
	representativeFace?: {
		id: string;
		cropUrl: string;
	};
}

export interface FacesState {
	clusters: FaceClusterType[];
	loading: boolean;
	error: string | null;
}
