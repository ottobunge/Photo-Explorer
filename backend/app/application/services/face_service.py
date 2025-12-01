"""Face service implementing FaceUseCases."""

import logging
from typing import Optional
from uuid import UUID

from app.application.ports.inbound import FaceUseCases
from app.application.ports.outbound import (
    FaceRepository,
    FileStorage,
    VectorStore,
)
from app.application.services.constants import (
    DEFAULT_CLUSTER_LIMIT,
    DEFAULT_CLUSTER_OFFSET,
    RELATIONSHIP_SAMPLE_PHOTO_LIMIT,
)
from app.domain.entities import Face, FaceCluster
from app.domain.exceptions import EntityNotFoundException
from app.domain.value_objects.face_relationship import FaceRelationship
from app.domain.value_objects.social_graph import ClusterNode, SocialGraph

logger = logging.getLogger(__name__)


class FaceService(FaceUseCases):
    """
    Implementation of face use cases.

    Handles face cluster management operations.
    """

    def __init__(
        self,
        face_repo: FaceRepository,
        file_storage: FileStorage,
        vector_store: VectorStore,
    ) -> None:
        self._face_repo = face_repo
        self._file_storage = file_storage
        self._vector_store = vector_store

    async def list_clusters(
        self,
        named_only: bool = False,
        unnamed_only: bool = False,
        limit: int = DEFAULT_CLUSTER_LIMIT,
        offset: int = DEFAULT_CLUSTER_OFFSET,
    ) -> list[FaceCluster]:
        """List face clusters."""
        return await self._face_repo.find_all_clusters(
            named_only=named_only,
            unnamed_only=unnamed_only,
            limit=limit,
            offset=offset,
        )

    async def get_cluster(self, cluster_id: UUID) -> Optional[FaceCluster]:
        """Get a face cluster by ID."""
        return await self._face_repo.find_cluster_by_id(cluster_id)

    async def name_cluster(self, cluster_id: UUID, name: str) -> FaceCluster:
        """Assign a name to a face cluster."""
        cluster = await self._face_repo.find_cluster_by_id(cluster_id)
        if not cluster:
            raise EntityNotFoundException("Cluster", str(cluster_id))

        cluster.set_name(name)
        cluster = await self._face_repo.save_cluster(cluster)

        logger.info(f"Named cluster {cluster_id} as '{name}'")
        return cluster

    async def merge_clusters(
        self,
        source_cluster_ids: list[UUID],
        target_cluster_id: UUID,
    ) -> FaceCluster:
        """
        Merge multiple clusters into one with atomic state updates.

        This operation is designed to be resilient to failures:
        1. Phase 1: Collect all updates without applying them
        2. Phase 2: Update database (transactional)
        3. Phase 3: Update vector store (batch operation)
        4. Phase 4: Delete source clusters
        If Phase 3 fails, compensates by reverting database updates.
        """
        # Get target cluster
        target = await self._face_repo.find_cluster_by_id(target_cluster_id)
        if not target:
            raise EntityNotFoundException("Cluster", str(target_cluster_id))

        total_moved = 0
        # Track all face updates and their original state for potential rollback
        all_face_updates: list[tuple[Face, UUID | None]] = []  # (face, original_cluster_id)

        try:
            # PHASE 1: Collect all updates without applying them
            for source_id in source_cluster_ids:
                if source_id == target_cluster_id:
                    continue

                source = await self._face_repo.find_cluster_by_id(source_id)
                if not source:
                    continue

                # Merge faces from source to target (updates cluster internally)
                moved_faces = target.merge_from(source)
                total_moved += len(moved_faces)

                # Fetch faces and track them with original cluster ID
                faces = await self._face_repo.find_faces_by_ids(source.face_ids)
                for face in faces:
                    # Store original cluster ID before modifying
                    original_cluster_id = face.cluster_id
                    all_face_updates.append((face, original_cluster_id))

            # Only proceed if there are faces to update
            if all_face_updates:
                # PHASE 2: Update database in transaction
                # Update all faces with new cluster assignment
                for face, _ in all_face_updates:
                    face.assign_to_cluster(target_cluster_id)

                await self._face_repo.save_faces_batch([face for face, _ in all_face_updates])

                # PHASE 3: Batch update vector store
                # Prepare batch updates for all faces
                vector_updates = [
                    (face.id.value, {"cluster_id": str(target_cluster_id)})
                    for face, _ in all_face_updates
                ]

                try:
                    await self._vector_store.update_face_payloads_batch(vector_updates)
                except Exception as vector_error:
                    # If vector store fails, compensate by reverting database changes
                    logger.error(
                        f"Vector store batch update failed during merge: {vector_error}. "
                        f"Compensating by reverting database changes."
                    )
                    await self._compensate_merge_failure(all_face_updates)
                    raise

            # PHASE 4: Delete source clusters
            for source_id in source_cluster_ids:
                if source_id != target_cluster_id:
                    await self._face_repo.delete_cluster(source_id)

            # Save target cluster
            target = await self._face_repo.save_cluster(target)

            logger.info(
                f"Merged {len(source_cluster_ids)} clusters into {target_cluster_id}, "
                f"moved {total_moved} faces"
            )
            return target

        except Exception as e:
            logger.error(f"Merge operation failed: {e}")
            raise

    async def _compensate_merge_failure(
        self,
        face_updates: list[tuple[Face, UUID | None]],
    ) -> None:
        """
        Compensating transaction to rollback failed merge.

        Reverts faces back to their original clusters in both database and vector store.

        Args:
            face_updates: List of (face, original_cluster_id) tuples to revert
        """
        logger.info(f"Compensating merge failure by reverting {len(face_updates)} faces")

        try:
            # Revert database changes
            for face, original_cluster_id in face_updates:
                if original_cluster_id is not None:
                    face.assign_to_cluster(original_cluster_id)
                else:
                    face.remove_from_cluster()

            await self._face_repo.save_faces_batch([face for face, _ in face_updates])

            # Revert vector store changes
            vector_reversion = [
                (face.id.value, {"cluster_id": str(original_cluster_id)})
                for face, original_cluster_id in face_updates
                if original_cluster_id is not None
            ]

            if vector_reversion:
                await self._vector_store.update_face_payloads_batch(vector_reversion)

            logger.info(f"Successfully compensated merge failure for {len(face_updates)} faces")

        except Exception as compensation_error:
            # If compensation fails, log critically but don't raise
            # Database and vector store are now in inconsistent state
            logger.critical(
                f"CRITICAL: Failed to compensate merge failure: {compensation_error}. "
                f"Database and vector store may be in inconsistent state. "
                f"Manual intervention may be required."
            )

    async def split_face(self, face_id: UUID) -> FaceCluster:
        """Split a face from its cluster into a new cluster."""
        face = await self._face_repo.find_face_by_id(face_id)
        if not face:
            raise EntityNotFoundException("Face", str(face_id))

        old_cluster_id = face.cluster_id

        # Create new cluster with just this face
        new_cluster = FaceCluster.create(initial_face_id=face_id)
        new_cluster = await self._face_repo.save_cluster(new_cluster)

        # Update face assignment
        face.assign_to_cluster(new_cluster.id.value)
        await self._face_repo.save_face(face)

        # Update vector store
        await self._vector_store.update_face_payload(
            face_id,
            {"cluster_id": str(new_cluster.id.value)},
        )

        # Remove from old cluster if it exists
        if old_cluster_id:
            old_cluster = await self._face_repo.find_cluster_by_id(old_cluster_id)
            if old_cluster:
                old_cluster.remove_face(face_id)
                await self._face_repo.save_cluster(old_cluster)

                # Delete old cluster if empty
                if old_cluster.is_empty:
                    await self._face_repo.delete_cluster(old_cluster_id)

        logger.info(f"Split face {face_id} into new cluster {new_cluster.id.value}")
        return new_cluster

    async def move_face(self, face_id: UUID, target_cluster_id: UUID) -> Face:
        """Move a face to a different cluster."""
        face = await self._face_repo.find_face_by_id(face_id)
        if not face:
            raise EntityNotFoundException("Face", str(face_id))

        target_cluster = await self._face_repo.find_cluster_by_id(target_cluster_id)
        if not target_cluster:
            raise EntityNotFoundException("Cluster", str(target_cluster_id))

        old_cluster_id = face.cluster_id

        # Add to target cluster
        target_cluster.add_face(face_id)
        await self._face_repo.save_cluster(target_cluster)

        # Update face assignment
        face.assign_to_cluster(target_cluster_id)
        face = await self._face_repo.save_face(face)

        # Update vector store
        await self._vector_store.update_face_payload(
            face_id,
            {"cluster_id": str(target_cluster_id)},
        )

        # Remove from old cluster if it exists
        if old_cluster_id and old_cluster_id != target_cluster_id:
            old_cluster = await self._face_repo.find_cluster_by_id(old_cluster_id)
            if old_cluster:
                old_cluster.remove_face(face_id)
                await self._face_repo.save_cluster(old_cluster)

                # Delete old cluster if empty
                if old_cluster.is_empty:
                    await self._face_repo.delete_cluster(old_cluster_id)

        logger.info(f"Moved face {face_id} to cluster {target_cluster_id}")
        return face

    async def get_face_crop(self, face_id: UUID) -> Optional[tuple[bytes, str]]:
        """Get the cropped face image."""
        face = await self._face_repo.find_face_by_id(face_id)
        if not face or not face.crop_path:
            return None

        file_bytes = await self._file_storage.get_file(face.crop_path)
        if file_bytes:
            return (file_bytes, "image/jpeg")

        return None

    async def get_faces_for_photo(self, photo_id: UUID) -> list[Face]:
        """Get all faces detected in a photo."""
        return await self._face_repo.find_faces_by_photo(photo_id)

    async def get_photos_for_cluster(
        self,
        cluster_id: UUID,
        limit: int = DEFAULT_CLUSTER_LIMIT,
        offset: int = DEFAULT_CLUSTER_OFFSET,
    ) -> list[UUID]:
        """Get photo IDs containing faces from a cluster."""
        return await self._face_repo.find_photo_ids_by_cluster(
            cluster_id=cluster_id,
            limit=limit,
            offset=offset,
        )

    async def count_clusters(self, named_only: bool = False) -> int:
        """Count clusters."""
        return await self._face_repo.count_clusters(named_only=named_only)

    async def get_representative_face_crop(self, cluster_id: UUID) -> Optional[tuple[bytes, str]]:
        """Get the crop image for the cluster's representative face."""
        cluster = await self._face_repo.find_cluster_by_id(cluster_id)
        if not cluster or not cluster.representative_face_id:
            return None

        return await self.get_face_crop(cluster.representative_face_id)

    # Social graph operations

    async def get_social_graph(
        self,
        filtered_by_person_id: UUID | None = None,
    ) -> SocialGraph:
        """
        Get the social graph of face relationships.

        Builds a graph showing relationships between people based on
        photo co-appearances.

        Args:
            filtered_by_person_id: Optional UUID to filter graph to show only
                                   that person's direct connections.

        Returns:
            SocialGraph containing nodes (people) and edges (relationships)
        """
        logger.info(
            f"Building social graph"
            + (f" filtered by person {filtered_by_person_id}" if filtered_by_person_id else "")
        )

        # Get co-appearances from repository
        co_appearances = await self._face_repo.get_co_appearances(cluster_id=filtered_by_person_id)

        # Get all unique cluster IDs involved
        cluster_ids: set[UUID] = set()
        for person_a_id, person_b_id, _ in co_appearances:
            cluster_ids.add(person_a_id)
            cluster_ids.add(person_b_id)

        # Fetch all clusters
        clusters = []
        for cluster_id in cluster_ids:
            cluster = await self._face_repo.find_cluster_by_id(cluster_id)
            if cluster:
                clusters.append(cluster)

        # Build relationships
        relationships = []
        for person_a_id, person_b_id, photo_count in co_appearances:
            # Get sample photo IDs (first few photos they appear together in)
            sample_photos = await self._face_repo.get_shared_photos(person_a_id, person_b_id)
            sample_photo_ids = sample_photos[:RELATIONSHIP_SAMPLE_PHOTO_LIMIT]

            relationship = FaceRelationship(
                person_a_id=person_a_id,
                person_b_id=person_b_id,
                shared_photo_count=photo_count,
                sample_photo_ids=sample_photo_ids,
            )
            relationships.append(relationship)

        # Convert clusters to immutable ClusterNode value objects
        nodes = [
            ClusterNode(
                id=cluster.id.value,
                name=cluster.name,
                face_count=cluster.face_count,
                representative_face_id=cluster.representative_face_id,
            )
            for cluster in clusters
        ]

        # Build graph
        graph = SocialGraph(nodes=nodes, edges=relationships)

        logger.info(
            f"Built social graph with {graph.node_count} nodes and {graph.edge_count} edges"
        )

        return graph

    async def get_relationship_photos(
        self,
        person_a_id: UUID,
        person_b_id: UUID,
    ) -> list[UUID]:
        """
        Get photo IDs where two people appear together.

        Args:
            person_a_id: ID of first person's cluster
            person_b_id: ID of second person's cluster

        Returns:
            List of photo IDs containing both people
        """
        logger.info(f"Getting shared photos for persons {person_a_id} and {person_b_id}")

        photo_ids = await self._face_repo.get_shared_photos(person_a_id, person_b_id)

        logger.info(f"Found {len(photo_ids)} shared photos")

        return photo_ids
