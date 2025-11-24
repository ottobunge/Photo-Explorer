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
from app.domain.entities import Face, FaceCluster
from app.domain.exceptions import EntityNotFoundException, InvalidOperationException

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
        limit: int = 50,
        offset: int = 0,
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
            raise EntityNotFoundException(f"Cluster {cluster_id} not found")

        cluster.set_name(name)
        cluster = await self._face_repo.save_cluster(cluster)

        logger.info(f"Named cluster {cluster_id} as '{name}'")
        return cluster

    async def merge_clusters(
        self,
        source_cluster_ids: list[UUID],
        target_cluster_id: UUID,
    ) -> FaceCluster:
        """Merge multiple clusters into one."""
        # Get target cluster
        target = await self._face_repo.find_cluster_by_id(target_cluster_id)
        if not target:
            raise EntityNotFoundException(f"Target cluster {target_cluster_id} not found")

        total_moved = 0

        for source_id in source_cluster_ids:
            if source_id == target_cluster_id:
                continue

            source = await self._face_repo.find_cluster_by_id(source_id)
            if not source:
                continue

            # Merge faces from source to target
            moved_faces = target.merge_from(source)
            total_moved += len(moved_faces)

            # Update face assignments in database
            for face_id in source.face_ids:
                face = await self._face_repo.find_face_by_id(face_id)
                if face:
                    face.assign_to_cluster(target_cluster_id)
                    await self._face_repo.save_face(face)

                    # Update vector store
                    await self._vector_store.update_face_payload(
                        face_id,
                        {"cluster_id": str(target_cluster_id)},
                    )

            # Delete source cluster
            await self._face_repo.delete_cluster(source_id)

        # Save target cluster
        target = await self._face_repo.save_cluster(target)

        logger.info(f"Merged {len(source_cluster_ids)} clusters into {target_cluster_id}, moved {total_moved} faces")
        return target

    async def split_face(self, face_id: UUID) -> FaceCluster:
        """Split a face from its cluster into a new cluster."""
        face = await self._face_repo.find_face_by_id(face_id)
        if not face:
            raise EntityNotFoundException(f"Face {face_id} not found")

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
            raise EntityNotFoundException(f"Face {face_id} not found")

        target_cluster = await self._face_repo.find_cluster_by_id(target_cluster_id)
        if not target_cluster:
            raise EntityNotFoundException(f"Target cluster {target_cluster_id} not found")

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
        limit: int = 50,
        offset: int = 0,
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

    async def get_representative_face_crop(
        self, cluster_id: UUID
    ) -> Optional[tuple[bytes, str]]:
        """Get the crop image for the cluster's representative face."""
        cluster = await self._face_repo.find_cluster_by_id(cluster_id)
        if not cluster or not cluster.representative_face_id:
            return None

        return await self.get_face_crop(cluster.representative_face_id)
