"""Face use cases - Inbound port for face operations."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.entities import Face, FaceCluster
from app.domain.value_objects.social_graph import SocialGraph


class FaceUseCases(ABC):
    """Interface defining face-related use cases."""

    @abstractmethod
    async def list_clusters(
        self,
        named_only: bool = False,
        unnamed_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[FaceCluster]:
        """
        List face clusters.

        Args:
            named_only: Only return clusters with names
            unnamed_only: Only return clusters without names
            limit: Maximum number of clusters to return
            offset: Number of clusters to skip

        Returns:
            List of FaceCluster entities
        """

    @abstractmethod
    async def get_cluster(self, cluster_id: UUID) -> Optional[FaceCluster]:
        """
        Get a face cluster by ID.

        Args:
            cluster_id: The cluster's unique identifier

        Returns:
            The FaceCluster entity or None if not found
        """

    @abstractmethod
    async def name_cluster(self, cluster_id: UUID, name: str) -> FaceCluster:
        """
        Assign a name to a face cluster.

        Args:
            cluster_id: The cluster's unique identifier
            name: The name to assign (person's name)

        Returns:
            The updated FaceCluster entity
        """

    @abstractmethod
    async def merge_clusters(
        self,
        source_cluster_ids: list[UUID],
        target_cluster_id: UUID,
    ) -> FaceCluster:
        """
        Merge multiple clusters into one.

        Args:
            source_cluster_ids: Clusters to merge from
            target_cluster_id: Cluster to merge into

        Returns:
            The merged FaceCluster entity
        """

    @abstractmethod
    async def split_face(self, face_id: UUID) -> FaceCluster:
        """
        Split a face from its cluster into a new cluster.

        Args:
            face_id: The face to split out

        Returns:
            The new FaceCluster containing just this face
        """

    @abstractmethod
    async def move_face(self, face_id: UUID, target_cluster_id: UUID) -> Face:
        """
        Move a face to a different cluster.

        Args:
            face_id: The face to move
            target_cluster_id: The destination cluster

        Returns:
            The updated Face entity
        """

    @abstractmethod
    async def get_face_crop(self, face_id: UUID) -> Optional[tuple[bytes, str]]:
        """
        Get the cropped face image.

        Args:
            face_id: The face's unique identifier

        Returns:
            Tuple of (image_bytes, content_type) or None if not found
        """

    @abstractmethod
    async def get_faces_for_photo(self, photo_id: UUID) -> list[Face]:
        """
        Get all faces detected in a photo.

        Args:
            photo_id: The photo's unique identifier

        Returns:
            List of Face entities
        """

    @abstractmethod
    async def get_photos_for_cluster(
        self,
        cluster_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[UUID]:
        """
        Get photo IDs containing faces from a cluster.

        Args:
            cluster_id: The cluster's unique identifier
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of photo IDs
        """

    @abstractmethod
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

    @abstractmethod
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
