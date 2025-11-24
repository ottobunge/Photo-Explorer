"""Face repository port - Interface for face and cluster persistence."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.entities import Face, FaceCluster


class FaceRepository(ABC):
    """Interface for face and cluster persistence operations."""

    # Face operations

    @abstractmethod
    async def save_face(self, face: Face) -> Face:
        """
        Persist a face entity.

        Args:
            face: The face to save

        Returns:
            The saved face
        """
        pass

    @abstractmethod
    async def find_face_by_id(self, face_id: UUID) -> Optional[Face]:
        """
        Find a face by its ID.

        Args:
            face_id: The face's unique identifier

        Returns:
            The Face entity or None if not found
        """
        pass

    @abstractmethod
    async def find_faces_by_photo(self, photo_id: UUID) -> list[Face]:
        """
        Find all faces in a photo.

        Args:
            photo_id: The photo's unique identifier

        Returns:
            List of Face entities
        """
        pass

    @abstractmethod
    async def find_faces_by_cluster(self, cluster_id: UUID) -> list[Face]:
        """
        Find all faces in a cluster.

        Args:
            cluster_id: The cluster's unique identifier

        Returns:
            List of Face entities
        """
        pass

    @abstractmethod
    async def delete_face(self, face_id: UUID) -> bool:
        """
        Delete a face.

        Args:
            face_id: The face's unique identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    # Cluster operations

    @abstractmethod
    async def save_cluster(self, cluster: FaceCluster) -> FaceCluster:
        """
        Persist a face cluster.

        Args:
            cluster: The cluster to save

        Returns:
            The saved cluster
        """
        pass

    @abstractmethod
    async def find_cluster_by_id(self, cluster_id: UUID) -> Optional[FaceCluster]:
        """
        Find a cluster by its ID.

        Args:
            cluster_id: The cluster's unique identifier

        Returns:
            The FaceCluster entity or None if not found
        """
        pass

    @abstractmethod
    async def find_all_clusters(
        self,
        named_only: bool = False,
        unnamed_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[FaceCluster]:
        """
        Find clusters with optional filtering.

        Args:
            named_only: Only return named clusters
            unnamed_only: Only return unnamed clusters
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of FaceCluster entities
        """
        pass

    @abstractmethod
    async def delete_cluster(self, cluster_id: UUID) -> bool:
        """
        Delete a cluster.

        Args:
            cluster_id: The cluster's unique identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def count_clusters(self, named_only: bool = False) -> int:
        """
        Count clusters.

        Args:
            named_only: Only count named clusters

        Returns:
            Total count of clusters
        """
        pass

    @abstractmethod
    async def find_photo_ids_by_cluster(
        self,
        cluster_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[UUID]:
        """
        Find photo IDs containing faces from a cluster.

        Args:
            cluster_id: The cluster's unique identifier
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of photo IDs
        """
        pass
