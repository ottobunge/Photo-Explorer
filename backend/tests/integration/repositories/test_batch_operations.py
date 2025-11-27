"""Integration tests for batch repository operations.

Tests performance and correctness of bulk operations.
"""

import time
from uuid import uuid4

import pytest

from app.adapters.outbound.persistence.postgres.repositories import (
    FaceRepositoryPostgres,
    PhotoRepositoryPostgres,
)
from tests.integration.factories import (
    EmbeddingFactory,
    FaceClusterFactory,
    FaceFactory,
    PhotoFactory,
)


@pytest.mark.integration
class TestBatchOperationsIntegration:
    """Integration tests for batch repository operations."""

    @pytest.mark.asyncio
    async def test_batch_face_save_performance(
        self,
        test_session,
        test_vector_store,
    ):
        """Test batch save is significantly faster than individual saves.

        Performance requirement: Batch save 100 faces should take <1 second.
        """
        face_repo = FaceRepositoryPostgres(test_session)
        photo_repo = PhotoRepositoryPostgres(test_session)

        # Create a photo
        photo = PhotoFactory.create(filename="batch_test.jpg")
        await photo_repo.save(photo)

        # Create 100 faces
        faces = []
        for i in range(100):
            face = FaceFactory.create(
                photo_id=photo.id.value,
                embedding=EmbeddingFactory.create_face_embedding(),
                confidence=0.90 + (i % 10) * 0.01,
            )
            faces.append(face)

        # Batch save
        start = time.time()

        for face in faces:
            await face_repo.save(face)

        await test_session.commit()

        batch_time = time.time() - start

        # Verify all saved
        saved_faces = await face_repo.find_by_photo_id(photo.id.value)
        assert len(saved_faces) == 100

        # Performance expectation: <1 second for 100 faces
        assert batch_time < 1.0, f"Batch save too slow: {batch_time}s"

        print(f"✓ Batch saved 100 faces in {batch_time:.3f}s")

    @pytest.mark.asyncio
    async def test_count_photos_by_cluster_performance(
        self,
        test_session,
        test_vector_store,
    ):
        """Test count is fast even for large clusters.

        Performance requirement: Count should complete in <100ms.
        """
        face_repo = FaceRepositoryPostgres(test_session)
        photo_repo = PhotoRepositoryPostgres(test_session)

        # Create a large cluster with 50 photos
        cluster_id = uuid4()

        photo_ids = []
        for i in range(50):
            photo = PhotoFactory.create(filename=f"cluster_photo_{i}.jpg")
            saved_photo = await photo_repo.save(photo)
            photo_ids.append(saved_photo.id.value)

            # Create 2 faces per photo in the same cluster
            for j in range(2):
                face = FaceFactory.create(
                    photo_id=saved_photo.id.value,
                    cluster_id=cluster_id,
                )
                await face_repo.save(face)

        await test_session.commit()

        # Count photos in cluster
        start = time.time()

        # Get all faces in cluster
        cluster_faces = await face_repo.find_by_cluster_id(cluster_id)

        # Count unique photos
        unique_photos = set(face.photo_id for face in cluster_faces)
        count = len(unique_photos)

        count_time = time.time() - start

        # Verify count
        assert count == 50

        # Performance expectation: <100ms
        assert count_time < 0.1, f"Count too slow: {count_time}s"

        print(f"✓ Counted {count} photos in cluster in {count_time*1000:.1f}ms")

    @pytest.mark.asyncio
    async def test_batch_photo_update(
        self,
        test_session,
    ):
        """Test batch updating multiple photos is performant."""
        photo_repo = PhotoRepositoryPostgres(test_session)

        # Create 50 photos
        photos = []
        for i in range(50):
            photo = PhotoFactory.create(
                filename=f"batch_update_{i}.jpg",
                processing_status="pending",
            )
            saved = await photo_repo.save(photo)
            photos.append(saved)

        await test_session.commit()

        # Batch update all to completed
        start = time.time()

        for photo in photos:
            photo.processing_status = "completed"
            await photo_repo.save(photo)

        await test_session.commit()

        update_time = time.time() - start

        # Verify all updated
        for photo in photos:
            retrieved = await photo_repo.find_by_id(photo.id.value)
            assert retrieved.processing_status == "completed"

        # Performance expectation: <500ms for 50 updates
        assert update_time < 0.5, f"Batch update too slow: {update_time}s"

        print(f"✓ Batch updated 50 photos in {update_time:.3f}s")

    @pytest.mark.asyncio
    async def test_bulk_face_clustering_assignment(
        self,
        test_session,
    ):
        """Test assigning many faces to clusters is performant."""
        face_repo = FaceRepositoryPostgres(test_session)
        photo_repo = PhotoRepositoryPostgres(test_session)

        # Create faces for clustering
        num_faces = 100
        num_clusters = 10

        cluster_ids = [uuid4() for _ in range(num_clusters)]

        # Create photos and faces
        for i in range(num_faces):
            photo = PhotoFactory.create(filename=f"cluster_assign_{i}.jpg")
            await photo_repo.save(photo)

            face = FaceFactory.create(
                photo_id=photo.id.value,
                cluster_id=None,  # Initially unclustered
            )
            await face_repo.save(face)

        await test_session.commit()

        # Get all unclustered faces
        unclustered = await face_repo.find_unclustered_faces(limit=num_faces)
        assert len(unclustered) >= num_faces

        # Assign faces to clusters (round-robin)
        start = time.time()

        for i, face in enumerate(unclustered[:num_faces]):
            cluster_id = cluster_ids[i % num_clusters]
            face.cluster_id = cluster_id
            await face_repo.save(face)

        await test_session.commit()

        assignment_time = time.time() - start

        # Verify all assigned
        for cluster_id in cluster_ids:
            cluster_faces = await face_repo.find_by_cluster_id(cluster_id)
            assert len(cluster_faces) > 0

        # Performance expectation: <2 seconds for 100 assignments
        assert assignment_time < 2.0, f"Assignment too slow: {assignment_time}s"

        print(f"✓ Assigned {num_faces} faces to clusters in {assignment_time:.3f}s")

    @pytest.mark.asyncio
    async def test_find_photos_by_ids_batch(
        self,
        test_session,
    ):
        """Test finding multiple photos by IDs is efficient."""
        photo_repo = PhotoRepositoryPostgres(test_session)

        # Create 30 photos
        photo_ids = []
        for i in range(30):
            photo = PhotoFactory.create(filename=f"batch_find_{i}.jpg")
            saved = await photo_repo.save(photo)
            photo_ids.append(saved.id.value)

        await test_session.commit()

        # Find all photos by IDs
        start = time.time()

        found_photos = []
        for photo_id in photo_ids:
            photo = await photo_repo.find_by_id(photo_id)
            if photo:
                found_photos.append(photo)

        find_time = time.time() - start

        # Verify all found
        assert len(found_photos) == 30

        # Performance expectation: <200ms for 30 lookups
        assert find_time < 0.2, f"Batch find too slow: {find_time}s"

        print(f"✓ Found 30 photos by ID in {find_time*1000:.1f}ms")

    @pytest.mark.asyncio
    async def test_delete_cascade_performance(
        self,
        test_session,
        test_vector_store,
    ):
        """Test deleting photos with faces cascades efficiently."""
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        # Create 10 photos with 5 faces each
        photo_ids = []

        for i in range(10):
            photo = PhotoFactory.create(filename=f"delete_cascade_{i}.jpg")
            saved_photo = await photo_repo.save(photo)
            photo_ids.append(saved_photo.id.value)

            # Add 5 faces per photo
            for j in range(5):
                face = FaceFactory.create(photo_id=saved_photo.id.value)
                await face_repo.save(face)

        await test_session.commit()

        # Verify setup
        for photo_id in photo_ids:
            faces = await face_repo.find_by_photo_id(photo_id)
            assert len(faces) == 5

        # Delete all photos
        start = time.time()

        for photo_id in photo_ids:
            await photo_repo.delete(photo_id)

        await test_session.commit()

        delete_time = time.time() - start

        # Verify all photos deleted
        for photo_id in photo_ids:
            photo = await photo_repo.find_by_id(photo_id)
            assert photo is None

            # Faces should also be deleted (cascade)
            faces = await face_repo.find_by_photo_id(photo_id)
            assert len(faces) == 0

        # Performance expectation: <500ms for deleting 10 photos with 50 faces
        assert delete_time < 0.5, f"Cascade delete too slow: {delete_time}s"

        print(
            f"✓ Deleted 10 photos with 50 faces in {delete_time:.3f}s (cascade)"
        )

    @pytest.mark.asyncio
    async def test_vector_store_batch_operations(
        self,
        test_vector_store,
    ):
        """Test vector store handles batch embeddings efficiently."""
        # Create 50 photo embeddings
        photo_embeddings = []
        for i in range(50):
            photo_id = uuid4()
            embedding = EmbeddingFactory.create_clip_embedding()
            photo_embeddings.append((photo_id, embedding))

        # Batch store embeddings
        start = time.time()

        for photo_id, embedding in photo_embeddings:
            await test_vector_store.store_photo_embedding(
                photo_id,
                embedding,
                payload={"index": str(photo_id)},
            )

        store_time = time.time() - start

        # Verify all stored by searching
        search_results = await test_vector_store.search_photos(
            photo_embeddings[0][1],
            limit=50,
        )

        assert len(search_results) >= 1

        # Performance expectation: <2 seconds for 50 embeddings
        assert store_time < 2.0, f"Vector store batch too slow: {store_time}s"

        print(f"✓ Stored 50 embeddings in vector store in {store_time:.3f}s")

    @pytest.mark.asyncio
    async def test_repository_transaction_rollback(
        self,
        test_session,
    ):
        """Test transaction rollback works correctly for batch operations."""
        photo_repo = PhotoRepositoryPostgres(test_session)

        # Create initial photo
        photo1 = PhotoFactory.create(filename="commit_test.jpg")
        await photo_repo.save(photo1)
        await test_session.commit()

        # Start transaction
        try:
            # Create more photos
            photo2 = PhotoFactory.create(filename="rollback_test_1.jpg")
            await photo_repo.save(photo2)

            photo3 = PhotoFactory.create(filename="rollback_test_2.jpg")
            await photo_repo.save(photo3)

            # Simulate error before commit
            raise ValueError("Simulated error")

        except ValueError:
            # Rollback transaction
            await test_session.rollback()

        # Verify only first photo exists
        all_photos = await photo_repo.find_all(limit=100)
        assert len(all_photos) == 1
        assert all_photos[0].filename == "commit_test.jpg"

    @pytest.mark.asyncio
    async def test_concurrent_batch_operations(
        self,
        test_session,
    ):
        """Test concurrent batch operations maintain data integrity."""
        import asyncio

        photo_repo = PhotoRepositoryPostgres(test_session)

        async def create_batch(start_idx: int, count: int) -> list:
            """Create a batch of photos."""
            photos = []
            for i in range(start_idx, start_idx + count):
                photo = PhotoFactory.create(filename=f"concurrent_{i}.jpg")
                saved = await photo_repo.save(photo)
                photos.append(saved)
            return photos

        # Create 3 batches concurrently
        batch1_task = create_batch(0, 10)
        batch2_task = create_batch(10, 10)
        batch3_task = create_batch(20, 10)

        results = await asyncio.gather(batch1_task, batch2_task, batch3_task)

        await test_session.commit()

        # Verify all photos created
        total_photos = sum(len(batch) for batch in results)
        assert total_photos == 30

        # Verify unique IDs
        all_ids = set()
        for batch in results:
            for photo in batch:
                all_ids.add(photo.id.value)

        assert len(all_ids) == 30, "All photo IDs should be unique"
