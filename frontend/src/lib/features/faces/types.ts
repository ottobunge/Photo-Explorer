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

// Social Graph types

export interface GraphNode {
	id: string;
	name: string | null;
	face_count: number;
	representative_face_id: string | null;
}

export interface GraphEdge {
	person_a_id: string;
	person_b_id: string;
	shared_photo_count: number;
	sample_photo_ids: string[];
}

export interface SocialGraph {
	nodes: GraphNode[];
	edges: GraphEdge[];
	node_count: number;
	edge_count: number;
	is_empty: boolean;
	has_connections: boolean;
}

export interface SocialGraphState {
	graph: SocialGraph | null;
	filteredPersonId: string | null;
	loading: boolean;
	error: string | null;
}
