// Face clustering API client methods

import { client } from './client';
import type { FaceClusterType } from '$lib/features/faces/types';
import { z } from 'zod';

/**
 * Zod schema for representative face data from backend
 */
const RepresentativeFaceSchema = z.object({
	id: z.string(),
	crop_url: z.string()
});

/**
 * Zod schema for cluster data from backend
 */
const ClusterDataSchema = z.object({
	id: z.string(),
	name: z.string().optional(),
	face_count: z.number(),
	photo_count: z.number(),
	representative_face: RepresentativeFaceSchema.optional()
});

/**
 * TypeScript type inferred from Zod schema
 */
type ClusterData = z.infer<typeof ClusterDataSchema>;

/**
 * Converts backend ClusterData to frontend FaceClusterType
 */
function mapClusterData(data: ClusterData): FaceClusterType {
	const cluster: FaceClusterType = {
		id: data.id,
		faceCount: data.face_count,
		photoCount: data.photo_count
	};

	// Only add optional properties if they have values
	if (data.name !== undefined) {
		cluster.name = data.name;
	}

	if (data.representative_face) {
		cluster.representativeFace = {
			id: data.representative_face.id,
			cropUrl: data.representative_face.crop_url
		};
	}

	return cluster;
}

/**
 * Split a face into a new cluster
 *
 * Removes the face from its current cluster and creates a new cluster with just this face.
 * Useful for separating incorrectly grouped faces.
 *
 * @param faceId - ID of the face to split
 * @returns The newly created cluster containing only this face
 * @throws ApiError if the operation fails
 */
export async function splitFace(faceId: string): Promise<FaceClusterType> {
	const response = await client.post<ClusterData>(`/faces/${faceId}/split`, ClusterDataSchema);
	return mapClusterData(response.data);
}

/**
 * Move a face to an existing cluster
 *
 * Removes the face from its current cluster and adds it to the target cluster.
 * Useful for correcting clustering mistakes or manually grouping faces.
 *
 * @param faceId - ID of the face to move
 * @param targetClusterId - ID of the cluster to move the face to
 * @returns The target cluster with the face added
 * @throws ApiError if the operation fails or target cluster doesn't exist
 */
export async function moveFace(
	faceId: string,
	targetClusterId: string
): Promise<FaceClusterType> {
	const response = await client.post<ClusterData>(
		`/faces/${faceId}/move`,
		ClusterDataSchema,
		{ target_cluster_id: targetClusterId }
	);
	return mapClusterData(response.data);
}

/**
 * Merge multiple clusters into a target cluster
 *
 * Moves all faces from source clusters into the target cluster, then deletes the source clusters.
 * This operation is irreversible.
 *
 * @param sourceClusterIds - IDs of clusters to merge (1-100 clusters)
 * @param targetClusterId - ID of the cluster to merge into (must not be in sourceClusterIds)
 * @returns The target cluster with all faces merged
 * @throws ApiError if the operation fails, target is in sources, or validation fails
 */
export async function mergeClusters(
	sourceClusterIds: string[],
	targetClusterId: string
): Promise<FaceClusterType> {
	const response = await client.post<ClusterData>(
		'/faces/clusters/merge',
		ClusterDataSchema,
		{
			source_cluster_ids: sourceClusterIds,
			target_cluster_id: targetClusterId
		}
	);
	return mapClusterData(response.data);
}
