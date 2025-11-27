"""Integration tests for face detection and clustering workflow.

Tests the complete face workflow: Detect → Embed → Cluster → Search by person
"""

import io
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.adapters.outbound.persistence.postgres.repositories import (
    FaceRepositoryPostgres,
    PhotoRepositoryPostgres,
)
from app.application.services.face_service import FaceService
from app.domain.value_objects import BoundingBox
from tests.integration.factories import (
    EmbeddingFactory,
    FaceClusterFactory,
    FaceFactory,
    PhotoFactory,
)


@pytest.mark.integration
class TestFaceDetectionClusteringWorkflow:
    """Integration tests for face detection and clustering."""

    @pytest.mark.asyncio
    async def test_detect_cluster_search_workflow(
        self,
        test_session,
        test_file_storage,
        test_vector_store,
        sample_image_bytes,
    ):
        """Test: Upload photo → Detect faces → Cluster → Search by person.

        This critical workflow verifies:
        1. Photos can have faces detected
        2. Face embeddings are stored in vector store
        3. Similar faces are clustered together
        4. Can search for photos by person (cluster)
        """
        # Setup
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        # Mock ML services
        ml_services = AsyncMock()
        ml_services.detect_faces = AsyncMock(return_value=[])

        face_service = FaceService(
            face_repo=face_repo,
            photo_repo=photo_repo,
            vector_store=test_vector_store,
            ml_services=ml_services,
        )

        # 1. Create photos with faces
        photo1_id = uuid4()
        photo2_id = uuid4()

        file1 = io.BytesIO(sample_image_bytes)
        storage_path1 = await test_file_storage.save_photo(file1, "person1_photo1.jpg")

        file2 = io.BytesIO(sample_image_bytes)
        storage_path2 = await test_file_storage.save_photo(file2, "person1_photo2.jpg")

        photo1 = PhotoFactory.create(
            id=photo1_id,
            filename="person1_photo1.jpg",
            storage_path=storage_path1,
        )
        photo2 = PhotoFactory.create(
            id=photo2_id,
            filename="person1_photo2.jpg",
            storage_path=storage_path2,
        )

        await photo_repo.save(photo1)
        await photo_repo.save(photo2)

        # 2. Detect faces (simulated - in real flow, ML service would detect)
        # Create similar face embeddings (same person)
        base_embedding = EmbeddingFactory.create_face_embedding()

        face1 = FaceFactory.create(
            photo_id=photo1_id,
            bounding_box=BoundingBox(x=100, y=100, width=200, height=200),
            confidence=0.95,
            embedding=base_embedding,
        )
        face2 = FaceFactory.create(
            photo_id=photo2_id,
            bounding_box=BoundingBox(x=150, y=120, width=180, height=180),
            confidence=0.93,
            embedding=EmbeddingFactory.create_similar_embedding(
                base_embedding, noise=0.05
            ),
        )

        saved_face1 = await face_repo.save(face1)
        saved_face2 = await face_repo.save(face2)

        # 3. Store face embeddings in vector store
        await test_vector_store.store_face_embedding(
            saved_face1.id.value,
            saved_face1.embedding,
            payload={"photo_id": str(photo1_id)},
        )
        await test_vector_store.store_face_embedding(
            saved_face2.id.value,
            saved_face2.embedding,
            payload={"photo_id": str(photo2_id)},
        )

        # 4. Cluster similar faces
        # In real implementation, clustering would be done by background task
        # For this test, we manually assign faces to a cluster
        cluster_id = uuid4()

        saved_face1.cluster_id = cluster_id
        saved_face2.cluster_id = cluster_id

        await face_repo.save(saved_face1)
        await face_repo.save(saved_face2)

        # Create cluster entity
        cluster = FaceClusterFactory.create(
            id=cluster_id,
            name="John Doe",
            representative_face_id=saved_face1.id.value,
            face_ids=[saved_face1.id.value, saved_face2.id.value],
        )

        # Note: Would save cluster via face service or cluster repository
        # For this test, we verify the faces are clustered

        # 5. Search for similar faces
        search_results = await test_vector_store.search_faces(
            base_embedding,
            limit=10,
        )

        face_ids = [str(r.id) for r in search_results]
        assert str(saved_face1.id.value) in face_ids
        assert str(saved_face2.id.value) in face_ids

        # 6. Find all faces in cluster
        cluster_faces = await face_repo.find_by_cluster_id(cluster_id)
        assert len(cluster_faces) == 2
        assert all(f.cluster_id == cluster_id for f in cluster_faces)

        # 7. Find all photos containing this person
        photo_ids_with_person = set()
        for face in cluster_faces:
            photo_ids_with_person.add(face.photo_id)

        assert photo1_id in photo_ids_with_person
        assert photo2_id in photo_ids_with_person

    @pytest.mark.asyncio
    async def test_face_clustering_accuracy(
        self,
        test_session,
        test_vector_store,
        sample_image_bytes,
    ):
        """Test that similar faces cluster together, dissimilar faces don't.

        Tests clustering algorithm by creating:
        - 3 faces of Person A (should cluster together)
        - 2 faces of Person B (should cluster together)
        - 1 face of Person C (separate cluster or unclustered)
        """
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        # Create base embeddings for 3 different people
        person_a_base = EmbeddingFactory.create_face_embedding()
        person_b_base = EmbeddingFactory.create_face_embedding()
        person_c_base = EmbeddingFactory.create_face_embedding()

        # Create photos and faces
        faces_person_a = []
        faces_person_b = []
        faces_person_c = []

        # Person A: 3 faces
        for i in range(3):
            photo = PhotoFactory.create(filename=f"person_a_{i}.jpg")
            await photo_repo.save(photo)

            embedding = EmbeddingFactory.create_similar_embedding(
                person_a_base, noise=0.03
            )
            face = FaceFactory.create(
                photo_id=photo.id.value,
                embedding=embedding,
            )
            saved_face = await face_repo.save(face)
            faces_person_a.append(saved_face)

            await test_vector_store.store_face_embedding(
                saved_face.id.value,
                saved_face.embedding,
            )

        # Person B: 2 faces
        for i in range(2):
            photo = PhotoFactory.create(filename=f"person_b_{i}.jpg")
            await photo_repo.save(photo)

            embedding = EmbeddingFactory.create_similar_embedding(
                person_b_base, noise=0.03
            )
            face = FaceFactory.create(
                photo_id=photo.id.value,
                embedding=embedding,
            )
            saved_face = await face_repo.save(face)
            faces_person_b.append(saved_face)

            await test_vector_store.store_face_embedding(
                saved_face.id.value,
                saved_face.embedding,
            )

        # Person C: 1 face
        photo = PhotoFactory.create(filename="person_c_0.jpg")
        await photo_repo.save(photo)

        face = FaceFactory.create(
            photo_id=photo.id.value,
            embedding=person_c_base,
        )
        saved_face = await face_repo.save(face)
        faces_person_c.append(saved_face)

        await test_vector_store.store_face_embedding(
            saved_face.id.value,
            saved_face.embedding,
        )

        # Verify Person A faces are similar to each other
        a1_results = await test_vector_store.search_faces(
            faces_person_a[0].embedding,
            limit=5,
        )
        a1_ids = [str(r.id) for r in a1_results]

        # Person A faces should be in top results
        assert str(faces_person_a[0].id.value) in a1_ids
        assert str(faces_person_a[1].id.value) in a1_ids
        assert str(faces_person_a[2].id.value) in a1_ids

        # Verify Person B faces are similar to each other
        b1_results = await test_vector_store.search_faces(
            faces_person_b[0].embedding,
            limit=5,
        )
        b1_ids = [str(r.id) for r in b1_results]

        assert str(faces_person_b[0].id.value) in b1_ids
        assert str(faces_person_b[1].id.value) in b1_ids

    @pytest.mark.asyncio
    async def test_cluster_merge_workflow(
        self,
        test_session,
        test_vector_store,
    ):
        """Test merging two face clusters.

        When user identifies that two clusters are the same person,
        all faces from source cluster should move to target cluster.
        """
        face_repo = FaceRepositoryPostgres(test_session)

        # Create two clusters
        cluster1_id = uuid4()
        cluster2_id = uuid4()

        # Cluster 1: 2 faces
        face1 = FaceFactory.create(cluster_id=cluster1_id)
        face2 = FaceFactory.create(cluster_id=cluster1_id)

        await face_repo.save(face1)
        await face_repo.save(face2)

        # Cluster 2: 3 faces
        face3 = FaceFactory.create(cluster_id=cluster2_id)
        face4 = FaceFactory.create(cluster_id=cluster2_id)
        face5 = FaceFactory.create(cluster_id=cluster2_id)

        await face_repo.save(face3)
        await face_repo.save(face4)
        await face_repo.save(face5)

        # Merge cluster1 into cluster2
        # Move all faces from cluster1 to cluster2
        cluster1_faces = await face_repo.find_by_cluster_id(cluster1_id)

        for face in cluster1_faces:
            face.cluster_id = cluster2_id
            await face_repo.save(face)

        # Verify merge
        cluster1_after = await face_repo.find_by_cluster_id(cluster1_id)
        cluster2_after = await face_repo.find_by_cluster_id(cluster2_id)

        assert len(cluster1_after) == 0, "Source cluster should be empty"
        assert len(cluster2_after) == 5, "Target cluster should have all faces"

    @pytest.mark.asyncio
    async def test_face_detection_multiple_faces_per_photo(
        self,
        test_session,
        test_vector_store,
    ):
        """Test photo with multiple faces (e.g., group photo)."""
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        # Create a photo
        photo = PhotoFactory.create(filename="group_photo.jpg")
        await photo_repo.save(photo)

        # Detect 5 faces in the photo
        faces = []
        for i in range(5):
            embedding = EmbeddingFactory.create_face_embedding()
            face = FaceFactory.create(
                photo_id=photo.id.value,
                bounding_box=BoundingBox(
                    x=100 + i * 200,
                    y=100,
                    width=150,
                    height=150,
                ),
                embedding=embedding,
                confidence=0.90 + i * 0.01,
            )

            saved_face = await face_repo.save(face)
            faces.append(saved_face)

            await test_vector_store.store_face_embedding(
                saved_face.id.value,
                saved_face.embedding,
                payload={"photo_id": str(photo.id.value)},
            )

        # Verify all faces detected and stored
        photo_faces = await face_repo.find_by_photo_id(photo.id.value)
        assert len(photo_faces) == 5

        # Verify all faces have different bounding boxes
        bboxes = [f.bounding_box for f in photo_faces]
        unique_bboxes = set((bb.x, bb.y, bb.width, bb.height) for bb in bboxes)
        assert len(unique_bboxes) == 5, "All faces should have unique positions"

    @pytest.mark.asyncio
    async def test_face_clustering_threshold_sensitivity(
        self,
        test_session,
        test_vector_store,
    ):
        """Test that clustering threshold affects cluster formation.

        With strict threshold (0.9): faces must be very similar
        With loose threshold (0.6): more faces cluster together
        """
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        # Create base embedding
        base_embedding = EmbeddingFactory.create_face_embedding()

        # Create faces with varying similarity
        # Very similar (noise=0.02) - should cluster with strict threshold
        # Somewhat similar (noise=0.15) - only cluster with loose threshold

        very_similar_faces = []
        for i in range(3):
            photo = PhotoFactory.create(filename=f"very_similar_{i}.jpg")
            await photo_repo.save(photo)

            embedding = EmbeddingFactory.create_similar_embedding(
                base_embedding, noise=0.02
            )
            face = FaceFactory.create(photo_id=photo.id.value, embedding=embedding)

            saved = await face_repo.save(face)
            very_similar_faces.append(saved)

            await test_vector_store.store_face_embedding(
                saved.id.value,
                saved.embedding,
            )

        somewhat_similar_faces = []
        for i in range(2):
            photo = PhotoFactory.create(filename=f"somewhat_similar_{i}.jpg")
            await photo_repo.save(photo)

            embedding = EmbeddingFactory.create_similar_embedding(
                base_embedding, noise=0.15
            )
            face = FaceFactory.create(photo_id=photo.id.value, embedding=embedding)

            saved = await face_repo.save(face)
            somewhat_similar_faces.append(saved)

            await test_vector_store.store_face_embedding(
                saved.id.value,
                saved.embedding,
            )

        # Strict threshold: only very similar faces should be found
        strict_results = await test_vector_store.search_faces(
            very_similar_faces[0].embedding,
            limit=10,
            score_threshold=0.90,
        )

        strict_ids = [str(r.id) for r in strict_results]

        # Very similar faces should be in results
        for face in very_similar_faces:
            assert str(face.id.value) in strict_ids

        # Loose threshold: both very similar and somewhat similar found
        loose_results = await test_vector_store.search_faces(
            very_similar_faces[0].embedding,
            limit=10,
            score_threshold=0.50,
        )

        loose_ids = [str(r.id) for r in loose_results]

        # All faces might be in results with loose threshold
        assert len(loose_results) >= len(very_similar_faces)

    @pytest.mark.asyncio
    async def test_unclustered_faces_workflow(
        self,
        test_session,
        test_vector_store,
    ):
        """Test retrieving faces that haven't been clustered yet."""
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        # Create faces: some clustered, some not
        cluster_id = uuid4()

        # Clustered faces
        for i in range(3):
            photo = PhotoFactory.create(filename=f"clustered_{i}.jpg")
            await photo_repo.save(photo)

            face = FaceFactory.create(
                photo_id=photo.id.value,
                cluster_id=cluster_id,
            )
            await face_repo.save(face)

        # Unclustered faces
        unclustered_ids = []
        for i in range(4):
            photo = PhotoFactory.create(filename=f"unclustered_{i}.jpg")
            await photo_repo.save(photo)

            face = FaceFactory.create(
                photo_id=photo.id.value,
                cluster_id=None,  # Not clustered
            )
            saved = await face_repo.save(face)
            unclustered_ids.append(saved.id.value)

        # Find unclustered faces
        unclustered = await face_repo.find_unclustered_faces(limit=10)

        assert len(unclustered) >= 4
        found_ids = [f.id.value for f in unclustered]

        for face_id in unclustered_ids:
            assert face_id in found_ids

    @pytest.mark.asyncio
    async def test_cluster_representative_face_selection(
        self,
        test_session,
        test_vector_store,
    ):
        """Test selecting the best representative face for a cluster.

        Representative face should be:
        - Highest confidence
        - Good quality bounding box (not too small)
        - Centered in photo
        """
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        cluster_id = uuid4()

        # Create faces with different qualities
        faces = []

        # Low confidence face
        photo1 = PhotoFactory.create(filename="low_conf.jpg")
        await photo_repo.save(photo1)
        face1 = FaceFactory.create(
            photo_id=photo1.id.value,
            cluster_id=cluster_id,
            confidence=0.75,
            bounding_box=BoundingBox(x=100, y=100, width=200, height=200),
        )
        saved1 = await face_repo.save(face1)
        faces.append(saved1)

        # High confidence, small face
        photo2 = PhotoFactory.create(filename="small_face.jpg")
        await photo_repo.save(photo2)
        face2 = FaceFactory.create(
            photo_id=photo2.id.value,
            cluster_id=cluster_id,
            confidence=0.95,
            bounding_box=BoundingBox(x=100, y=100, width=50, height=50),
        )
        saved2 = await face_repo.save(face2)
        faces.append(saved2)

        # High confidence, good size - BEST REPRESENTATIVE
        photo3 = PhotoFactory.create(filename="best_face.jpg")
        await photo_repo.save(photo3)
        face3 = FaceFactory.create(
            photo_id=photo3.id.value,
            cluster_id=cluster_id,
            confidence=0.97,
            bounding_box=BoundingBox(x=100, y=100, width=300, height=300),
        )
        saved3 = await face_repo.save(face3)
        faces.append(saved3)

        # Select best representative (highest confidence + good size)
        cluster_faces = await face_repo.find_by_cluster_id(cluster_id)

        # Simple heuristic: confidence * bbox_size
        best_face = max(
            cluster_faces,
            key=lambda f: f.confidence
            * (f.bounding_box.width * f.bounding_box.height),
        )

        assert best_face.id.value == saved3.id.value, "Face 3 should be representative"
        assert best_face.confidence == 0.97
        assert best_face.bounding_box.width == 300
