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

    @abstractmethod
    async def find_face_by_id(self, face_id: UUID) -> Optional[Face]:
        """
        Find a face by its ID.

        Args:
            face_id: The face's unique identifier

        Returns:
            The Face entity or None if not found
        """

    @abstractmethod
    async def find_faces_by_photo(self, photo_id: UUID) -> list[Face]:
        """
        Find all faces in a photo.

        Args:
            photo_id: The photo's unique identifier

        Returns:
            List of Face entities
        """

    @abstractmethod
    async def find_faces_by_cluster(self, cluster_id: UUID) -> list[Face]:
        """
        Find all faces in a cluster.

        Args:
            cluster_id: The cluster's unique identifier

        Returns:
            List of Face entities
        """

    @abstractmethod
    async def delete_face(self, face_id: UUID) -> bool:
        """
        Delete a face.

        Args:
            face_id: The face's unique identifier

        Returns:
            True if deleted, False if not found
        """

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

    @abstractmethod
    async def find_cluster_by_id(self, cluster_id: UUID) -> Optional[FaceCluster]:
        """
        Find a cluster by its ID.

        Args:
            cluster_id: The cluster's unique identifier

        Returns:
            The FaceCluster entity or None if not found
        """

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

    @abstractmethod
    async def delete_cluster(self, cluster_id: UUID) -> bool:
        """
        Delete a cluster.

        Args:
            cluster_id: The cluster's unique identifier

        Returns:
            True if deleted, False if not found
        """

    @abstractmethod
    async def count_clusters(self, named_only: bool = False) -> int:
        """
        Count clusters.

        Args:
            named_only: Only count named clusters

        Returns:
            Total count of clusters
        """

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

    @abstractmethod
    async def save_faces_batch(self, faces: list[Face]) -> list[Face]:
        """
        Persist multiple face entities in a single batch operation.

        This reduces database round-trips from N to 1 for bulk face saves.

        Args:
            faces: List of faces to save

        Returns:
            List of saved faces
        """

    @abstractmethod
    async def find_faces_by_ids(self, face_ids: list[UUID]) -> list[Face]:
        """
        Find multiple faces by IDs in a single query.

        This reduces database round-trips from N to 1 for bulk face lookups.

        Args:
            face_ids: List of face IDs to find

        Returns:
            List of Face entities (may be fewer than requested if some not found)
        """

    @abstractmethod
    async def count_photos_by_cluster(self, cluster_id: UUID) -> int:
        """
        Count unique photos in a cluster without loading all photo IDs.

        This is much more efficient than fetching 10,000 IDs just to count them.

        Args:
            cluster_id: The cluster's unique identifier

        Returns:
            Count of unique photos containing faces from this cluster
        """

    @abstractmethod
    async def count_photos_by_clusters_batch(
        self, cluster_ids: list[UUID]
    ) -> dict[UUID, int]:
        """
        Count unique photos for multiple clusters in a single batch query.

        This eliminates N+1 queries by fetching all photo counts in one query
        with a GROUP BY clause, instead of querying each cluster individually.

        Args:
            cluster_ids: List of cluster IDs to count photos for

        Returns:
            Dictionary mapping cluster_id to photo_count
        """

    # Social graph operations

    @abstractmethod
    async def get_co_appearances(
        self,
        cluster_id: Optional[UUID] = None,
    ) -> list[tuple[UUID, UUID, int]]:
        """
        Get all face co-appearances (people appearing together in photos).

        Returns pairs of cluster IDs that appear together in photos,
        along with the count of shared photos.

        Args:
            cluster_id: Optional filter to only get co-appearances for a specific person.
                       If None, returns all co-appearances.

        Returns:
            List of tuples (person_a_id, person_b_id, shared_photo_count).
            Each pair appears only once (a < b to avoid duplicates).
        """

    @abstractmethod
    async def get_shared_photos(
        self,
        person_a_id: UUID,
        person_b_id: UUID,
    ) -> list[UUID]:
        """
        Get IDs of all photos where two people appear together.

        Args:
            person_a_id: ID of first person's cluster
            person_b_id: ID of second person's cluster

        Returns:
            List of photo IDs containing both people
        """
