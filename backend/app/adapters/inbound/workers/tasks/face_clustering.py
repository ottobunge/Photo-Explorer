"""Face clustering tasks for background execution."""

import asyncio
import logging
from contextlib import contextmanager
from typing import Generator
from uuid import UUID

import redis
from sqlalchemy.exc import OperationalError

from app.adapters.inbound.workers.celery_app import celery_app
from app.adapters.inbound.workers.exceptions import TransientError
from app.adapters.outbound.persistence.postgres import (
    FaceRepositoryPostgres,
)
from app.adapters.outbound.persistence.postgres.database import get_worker_session_context
from app.adapters.outbound.persistence.qdrant import QdrantVectorStore
from app.config import get_settings
from app.domain.entities import FaceCluster

logger = logging.getLogger(__name__)

# Lock timeout in seconds - prevents deadlocks if worker crashes
CLUSTERING_LOCK_TIMEOUT = 300  # 5 minutes
CLUSTERING_LOCK_KEY = "face_clustering:global_lock"


@contextmanager
def acquire_clustering_lock(timeout: int = CLUSTERING_LOCK_TIMEOUT) -> Generator[bool, None, None]:
    """
    Acquire a distributed lock for face clustering operations.

    This prevents concurrent clustering tasks from running simultaneously,
    which could lead to duplicate clusters or race conditions.

    Args:
        timeout: Lock timeout in seconds. Lock auto-expires after this time.

    Yields:
        True if lock was acquired successfully

    Raises:
        TransientError: If lock cannot be acquired (another task is running)
    """
    settings = get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)

    try:
        # Try to acquire the lock with a timeout
        # nx=True means "set if not exists" (atomic operation)
        # ex=timeout sets expiration time
        acquired = client.set(CLUSTERING_LOCK_KEY, "locked", nx=True, ex=timeout)

        if not acquired:
            logger.warning("Face clustering lock already held by another task")
            raise TransientError(
                "Face clustering is already in progress. Please try again later."
            )

        logger.info("Acquired face clustering lock")
        yield True

    finally:
        # Always release the lock when done
        try:
            client.delete(CLUSTERING_LOCK_KEY)
            logger.info("Released face clustering lock")
        except Exception as e:
            logger.error(f"Error releasing clustering lock: {e}")
        finally:
            client.close()


def run_async(coro):
    """Helper to run async code in sync context.

    Creates a new event loop for each call without setting it as the global
    event loop to avoid race conditions in multi-threaded Celery workers.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    name="face_clustering.cluster_faces",
    autoretry_for=(TransientError, OperationalError, ConnectionError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    time_limit=7200,  # 2 hours hard limit
    soft_time_limit=6600,  # 110 minutes soft limit
)
def cluster_faces_task(self, similarity_threshold: float = 0.6) -> dict:
    """
    Cluster all unclustered faces based on similarity.

    Timeouts: 110 min soft, 2 hours hard.

    Uses a simple greedy algorithm:
    1. For each unclustered face, find similar faces
    2. Group similar faces into clusters
    3. Assign representative face to each cluster

    Args:
        similarity_threshold: Minimum similarity score to consider faces same person

    Returns:
        Dictionary with clustering results
    """
    return run_async(_cluster_faces_async(similarity_threshold))


async def _cluster_faces_async(similarity_threshold: float) -> dict:
    """Async implementation of face clustering."""
    # Acquire distributed lock to prevent concurrent clustering
    with acquire_clustering_lock():
        # Initialize vector store (singleton, no cleanup needed)
        vector_store = QdrantVectorStore()

        try:
            async with get_worker_session_context() as session:
                face_repo = FaceRepositoryPostgres(session)

                # Get all unclustered faces
                try:
                    unclustered_faces = await face_repo.find_unclustered_faces(limit=1000)
                except Exception as e:
                    logger.error(f"Database error fetching unclustered faces: {e}", exc_info=True)
                    raise

                if not unclustered_faces:
                    logger.info("No unclustered faces found")
                    return {"status": "completed", "clusters_created": 0, "faces_clustered": 0}

                logger.info(f"Found {len(unclustered_faces)} unclustered faces")

                # Track which faces have been assigned
                assigned_face_ids: set[UUID] = set()
                clusters_created = 0
                faces_clustered = 0

                for face in unclustered_faces:
                    if face.id.value in assigned_face_ids:
                        continue

                    # Find similar faces
                    similar_results = await vector_store.find_similar_faces(
                        face.id.value,
                        threshold=similarity_threshold,
                        limit=100,
                    )

                    # Filter to only unclustered faces not yet assigned
                    similar_face_ids = [
                        result.id for result in similar_results if result.id not in assigned_face_ids
                    ]

                    # Create a new cluster with this face and similar faces
                    cluster = FaceCluster.create(initial_face_id=face.id.value)

                    # Add similar faces to cluster
                    for similar_id in similar_face_ids:
                        if similar_id != face.id.value:
                            cluster.add_face(similar_id)

                    # Save cluster
                    cluster = await face_repo.save_cluster(cluster)

                    # Update faces with cluster assignment
                    all_cluster_face_ids = [face.id.value] + similar_face_ids
                    for face_id in all_cluster_face_ids:
                        face_entity = await face_repo.find_face_by_id(face_id)
                        if face_entity:
                            face_entity.assign_to_cluster(cluster.id.value)
                            await face_repo.save_face(face_entity)

                            # Update vector store payload
                            await vector_store.update_face_payload(
                                face_id,
                                {"cluster_id": str(cluster.id.value)},
                            )

                        assigned_face_ids.add(face_id)

                    clusters_created += 1
                    faces_clustered += len(all_cluster_face_ids)

                    logger.debug(
                        f"Created cluster {cluster.id.value} with {len(all_cluster_face_ids)} faces"
                    )

                logger.info(
                    f"Clustering complete: {clusters_created} clusters, " f"{faces_clustered} faces"
                )

                return {
                    "status": "completed",
                    "clusters_created": clusters_created,
                    "faces_clustered": faces_clustered,
                }
        except Exception as e:
            logger.exception(f"Error during face clustering: {e}")
            return {"status": "error", "message": str(e)}


@celery_app.task(
    bind=True,
    name="face_clustering.update_clusters",
    autoretry_for=(TransientError, OperationalError, ConnectionError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    time_limit=7200,  # 2 hours hard limit
    soft_time_limit=6600,  # 110 minutes soft limit
)
def update_clusters_task(
    self,
    face_ids: list[str],
    similarity_threshold: float = 0.6,
) -> dict:
    """
    Update cluster assignments for specific faces.

    Timeouts: 110 min soft, 2 hours hard.

    This is used when new faces are detected to incrementally add them
    to existing clusters or create new ones.

    Args:
        face_ids: List of face UUIDs to cluster
        similarity_threshold: Minimum similarity score

    Returns:
        Dictionary with update results
    """
    return run_async(_update_clusters_async(face_ids, similarity_threshold))


async def _update_clusters_async(
    face_ids: list[str],
    similarity_threshold: float,
) -> dict:
    """Async implementation of incremental cluster update."""
    # Initialize vector store (singleton, no cleanup needed)
    vector_store = QdrantVectorStore()

    try:
        async with get_worker_session_context() as session:
            face_repo = FaceRepositoryPostgres(session)

            faces_assigned = 0
            new_clusters = 0

            for face_id_str in face_ids:
                face_id = UUID(face_id_str)

                # Get the face
                face = await face_repo.find_face_by_id(face_id)
                if not face or face.is_clustered:
                    continue

                # Find similar faces (including clustered ones)
                similar_results = await vector_store.find_similar_faces(
                    face_id,
                    threshold=similarity_threshold,
                    limit=10,
                )

                if not similar_results:
                    # No similar faces - create new cluster
                    cluster = FaceCluster.create(initial_face_id=face_id)
                    cluster = await face_repo.save_cluster(cluster)

                    face.assign_to_cluster(cluster.id.value)
                    await face_repo.save_face(face)

                    await vector_store.update_face_payload(
                        face_id,
                        {"cluster_id": str(cluster.id.value)},
                    )

                    new_clusters += 1
                    faces_assigned += 1
                    continue

                # Check if any similar faces are already clustered
                clustered_results = []
                for result in similar_results:
                    similar_face = await face_repo.find_face_by_id(result.id)
                    if similar_face and similar_face.is_clustered:
                        clustered_results.append((similar_face, result.score))

                if clustered_results:
                    # Assign to the cluster of the most similar face
                    best_match = max(clustered_results, key=lambda x: x[1])
                    cluster_id = best_match[0].cluster_id

                    # Get and update cluster
                    cluster = await face_repo.find_cluster_by_id(cluster_id)
                    if cluster:
                        cluster.add_face(face_id)
                        await face_repo.save_cluster(cluster)

                        face.assign_to_cluster(cluster_id)
                        await face_repo.save_face(face)

                        await vector_store.update_face_payload(
                            face_id,
                            {"cluster_id": str(cluster_id)},
                        )

                        faces_assigned += 1
                else:
                    # All similar faces are also unclustered - create new cluster
                    cluster = FaceCluster.create(initial_face_id=face_id)

                    # Add similar unclustered faces
                    for result in similar_results[:5]:  # Limit to top 5
                        similar_face = await face_repo.find_face_by_id(result.id)
                        if similar_face and not similar_face.is_clustered:
                            cluster.add_face(result.id)

                    cluster = await face_repo.save_cluster(cluster)

                    # Update all faces in new cluster
                    for cluster_face_id in cluster.face_ids:
                        cluster_face = await face_repo.find_face_by_id(cluster_face_id)
                        if cluster_face:
                            cluster_face.assign_to_cluster(cluster.id.value)
                            await face_repo.save_face(cluster_face)

                            await vector_store.update_face_payload(
                                cluster_face_id,
                                {"cluster_id": str(cluster.id.value)},
                            )

                    new_clusters += 1
                    faces_assigned += len(cluster.face_ids)

            return {
                "status": "completed",
                "faces_assigned": faces_assigned,
                "new_clusters": new_clusters,
            }
    except Exception as e:
        logger.exception(f"Error updating clusters: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(
    bind=True,
    name="face_clustering.merge_clusters",
    autoretry_for=(TransientError, OperationalError, ConnectionError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    time_limit=7200,  # 2 hours hard limit
    soft_time_limit=6600,  # 110 minutes soft limit
)
def merge_clusters_task(
    self,
    source_cluster_id: str,
    target_cluster_id: str,
) -> dict:
    """
    Merge two face clusters together.

    Args:
        source_cluster_id: Cluster to merge from (will be deleted)
        target_cluster_id: Cluster to merge into

    Returns:
        Dictionary with merge results
    """
    return run_async(_merge_clusters_async(source_cluster_id, target_cluster_id))


async def _merge_clusters_async(
    source_cluster_id: str,
    target_cluster_id: str,
) -> dict:
    """Async implementation of cluster merge."""
    # Initialize vector store (singleton, no cleanup needed)
    vector_store = QdrantVectorStore()

    try:
        async with get_worker_session_context() as session:
            face_repo = FaceRepositoryPostgres(session)

            source_id = UUID(source_cluster_id)
            target_id = UUID(target_cluster_id)

            # Get both clusters
            source = await face_repo.find_cluster_by_id(source_id)
            target = await face_repo.find_cluster_by_id(target_id)

            if not source or not target:
                return {"status": "error", "message": "Cluster not found"}

            # Merge source into target
            moved_faces = target.merge_from(source)
            await face_repo.save_cluster(target)

            # Update face assignments
            for face_id in source.face_ids:
                face = await face_repo.find_face_by_id(face_id)
                if face:
                    face.assign_to_cluster(target_id)
                    await face_repo.save_face(face)

                    await vector_store.update_face_payload(
                        face_id,
                        {"cluster_id": str(target_id)},
                    )

            # Delete source cluster
            await face_repo.delete_cluster(source_id)

            return {
                "status": "completed",
                "faces_moved": len(moved_faces),
                "target_cluster_id": target_cluster_id,
            }
    except Exception as e:
        logger.exception(f"Error merging clusters: {e}")
        return {"status": "error", "message": str(e)}
