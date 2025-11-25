"""Integration tests for face detection and clustering.

Tests:
1. Detect faces in photos
2. Store face embeddings
3. Cluster similar faces
4. Tag faces with person names
5. Find photos by face
"""

from uuid import uuid4

import pytest

from app.adapters.outbound.persistence.postgres.repositories import (
    FaceRepositoryPostgres,
    PhotoRepositoryPostgres,
)
from tests.integration.factories import (
    EmbeddingFactory,
    FaceFactory,
    PhotoFactory,
)


class TestFaceDetectionAndClustering:
    """Test face detection and clustering workflows."""

    @pytest.mark.asyncio
    async def test_detect_and_store_faces(
        self,
        test_session,
    ):
        """Test detecting faces and storing them in database."""
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        # 1. Create photo
        photo = PhotoFactory.create(filename="photo_with_faces.jpg")
        photo = await photo_repo.save(photo)

        # 2. Simulate face detection - create multiple faces
        faces = FaceFactory.create_batch(3, photo_id=photo.id.value)

        # 3. Save faces
        saved_faces = []
        for face in faces:
            saved = await face_repo.save(face)
            saved_faces.append(saved)

        # 4. Verify faces are saved
        assert len(saved_faces) == 3
        for face in saved_faces:
            assert face.photo_id == photo.id.value
            assert face.confidence > 0.9

        # 5. Retrieve faces by photo
        retrieved_faces = await face_repo.find_by_photo_id(photo.id.value)
        assert len(retrieved_faces) == 3

    @pytest.mark.asyncio
    async def test_store_face_embeddings_in_vector_store(
        self,
        test_session,
        test_vector_store,
    ):
        """Test storing face embeddings in Qdrant."""
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        # 1. Create photo and faces
        photo = PhotoFactory.create()
        photo = await photo_repo.save(photo)

        face = FaceFactory.create(
            photo_id=photo.id.value,
            embedding=EmbeddingFactory.create_face_embedding(),
        )
        face = await face_repo.save(face)

        # 2. Store embedding in vector store
        await test_vector_store.store_face_embedding(
            face.id.value,
            face.embedding,
            payload={
                "photo_id": str(photo.id.value),
                "confidence": face.confidence,
            },
        )

        # 3. Search for the face
        results = await test_vector_store.search_faces(
            face.embedding,
            limit=1,
        )

        # 4. Verify face is found
        assert len(results) == 1
        assert str(results[0].id) == str(face.id.value)

    @pytest.mark.asyncio
    async def test_cluster_similar_faces(
        self,
        test_session,
        test_vector_store,
    ):
        """Test clustering similar faces together."""
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        # 1. Create photos
        photos = PhotoFactory.create_batch(5)
        saved_photos = []
        for photo in photos:
            saved = await photo_repo.save(photo)
            saved_photos.append(saved)

        # 2. Create base embedding for "person 1"
        person1_base_embedding = EmbeddingFactory.create_face_embedding()

        # 3. Create similar faces for person 1 across multiple photos
        person1_faces = []
        for i in range(3):
            # Similar embedding = same person
            embedding = EmbeddingFactory.create_similar_embedding(
                person1_base_embedding,
                noise=0.02,  # Very small variation
            )
            face = FaceFactory.create(
                photo_id=saved_photos[i].id.value,
                embedding=embedding,
            )
            saved_face = await face_repo.save(face)
            person1_faces.append(saved_face)

            await test_vector_store.store_face_embedding(
                saved_face.id.value,
                saved_face.embedding,
            )

        # 4. Create different faces for person 2
        person2_faces = []
        person2_base_embedding = EmbeddingFactory.create_face_embedding()

        for i in range(2):
            embedding = EmbeddingFactory.create_similar_embedding(
                person2_base_embedding,
                noise=0.02,
            )
            face = FaceFactory.create(
                photo_id=saved_photos[i + 3].id.value,
                embedding=embedding,
            )
            saved_face = await face_repo.save(face)
            person2_faces.append(saved_face)

            await test_vector_store.store_face_embedding(
                saved_face.id.value,
                saved_face.embedding,
            )

        # 5. Find similar faces for person 1
        similar_to_person1 = await test_vector_store.search_faces(
            person1_faces[0].embedding,
            limit=5,
        )

        # 6. Verify similar faces are grouped
        person1_ids = {str(f.id.value) for f in person1_faces}
        similar_ids = {str(r.id) for r in similar_to_person1[:3]}

        # At least 2 of person 1's faces should be in top results
        matches = len(person1_ids.intersection(similar_ids))
        assert matches >= 2

    @pytest.mark.asyncio
    async def test_assign_cluster_to_faces(
        self,
        test_session,
    ):
        """Test assigning faces to a cluster."""
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        # 1. Create photos and faces
        photos = PhotoFactory.create_batch(3)
        faces = []
        for photo in photos:
            saved_photo = await photo_repo.save(photo)
            face = FaceFactory.create(photo_id=saved_photo.id.value)
            saved_face = await face_repo.save(face)
            faces.append(saved_face)

        # 2. Create cluster ID
        cluster_id = uuid4()

        # 3. Assign all faces to cluster
        for face in faces:
            face.cluster_id = cluster_id
            await face_repo.save(face)

        # 4. Find faces by cluster
        clustered_faces = await face_repo.find_by_cluster_id(cluster_id)

        # 5. Verify all faces are in cluster
        assert len(clustered_faces) == 3
        assert all(f.cluster_id == cluster_id for f in clustered_faces)

    @pytest.mark.asyncio
    async def test_tag_face_cluster_with_person_name(
        self,
        test_session,
    ):
        """Test tagging a face cluster with a person's name."""
        # Note: This would typically be done through a FaceClusterRepository
        # For now, we'll test the concept using face cluster_id

        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        # 1. Create faces in a cluster
        cluster_id = uuid4()
        person_name = "John Doe"

        photos = PhotoFactory.create_batch(3)
        faces = []
        for photo in photos:
            saved_photo = await photo_repo.save(photo)
            face = FaceFactory.create(
                photo_id=saved_photo.id.value,
                cluster_id=cluster_id,
            )
            saved_face = await face_repo.save(face)
            faces.append(saved_face)

        # 2. Find photos containing this person (by cluster_id)
        photos_with_person = []
        for face in faces:
            photo = await photo_repo.find_by_id(face.photo_id)
            photos_with_person.append(photo)

        # 3. Verify we can find all photos with this person
        assert len(photos_with_person) == 3

    @pytest.mark.asyncio
    async def test_find_photos_by_face_cluster(
        self,
        test_session,
    ):
        """Test finding all photos containing a specific person (cluster)."""
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        # 1. Create cluster for person
        cluster_id = uuid4()

        # 2. Create photos with this person
        photos_with_person = PhotoFactory.create_batch(3)
        for photo in photos_with_person:
            saved_photo = await photo_repo.save(photo)
            face = FaceFactory.create(
                photo_id=saved_photo.id.value,
                cluster_id=cluster_id,
            )
            await face_repo.save(face)

        # 3. Create photos without this person
        photos_without = PhotoFactory.create_batch(2)
        for photo in photos_without:
            await photo_repo.save(photo)

        # 4. Find all faces in cluster
        faces_in_cluster = await face_repo.find_by_cluster_id(cluster_id)

        # 5. Get unique photo IDs
        photo_ids = {f.photo_id for f in faces_in_cluster}

        # 6. Verify correct count
        assert len(photo_ids) == 3

    @pytest.mark.asyncio
    async def test_multiple_faces_per_photo(
        self,
        test_session,
    ):
        """Test handling multiple faces in a single photo."""
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        # 1. Create photo
        photo = PhotoFactory.create(filename="group_photo.jpg")
        photo = await photo_repo.save(photo)

        # 2. Create multiple faces with different positions
        from app.domain.value_objects import BoundingBox

        face1 = FaceFactory.create(
            photo_id=photo.id.value,
            bounding_box=BoundingBox(x=100, y=100, width=150, height=150),
        )
        face2 = FaceFactory.create(
            photo_id=photo.id.value,
            bounding_box=BoundingBox(x=300, y=120, width=140, height=140),
        )
        face3 = FaceFactory.create(
            photo_id=photo.id.value,
            bounding_box=BoundingBox(x=500, y=150, width=160, height=160),
        )

        await face_repo.save(face1)
        await face_repo.save(face2)
        await face_repo.save(face3)

        # 3. Retrieve all faces
        faces = await face_repo.find_by_photo_id(photo.id.value)

        # 4. Verify all faces retrieved
        assert len(faces) == 3

        # 5. Verify bounding boxes are different
        bboxes = [f.bounding_box for f in faces]
        assert len(set((bb.x, bb.y) for bb in bboxes)) == 3

    @pytest.mark.asyncio
    async def test_face_confidence_filtering(
        self,
        test_session,
    ):
        """Test filtering faces by confidence threshold."""
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        # 1. Create photo
        photo = PhotoFactory.create()
        photo = await photo_repo.save(photo)

        # 2. Create faces with different confidence levels
        high_conf = FaceFactory.create(
            photo_id=photo.id.value,
            confidence=0.95,
        )
        medium_conf = FaceFactory.create(
            photo_id=photo.id.value,
            confidence=0.75,
        )
        low_conf = FaceFactory.create(
            photo_id=photo.id.value,
            confidence=0.45,
        )

        await face_repo.save(high_conf)
        await face_repo.save(medium_conf)
        await face_repo.save(low_conf)

        # 3. Retrieve all faces
        all_faces = await face_repo.find_by_photo_id(photo.id.value)
        assert len(all_faces) == 3

        # 4. Filter high confidence faces (>= 0.8)
        high_confidence_faces = [f for f in all_faces if f.confidence >= 0.8]
        assert len(high_confidence_faces) == 1
        assert high_confidence_faces[0].confidence == 0.95

    @pytest.mark.asyncio
    async def test_delete_photo_cascade_to_faces(
        self,
        test_session,
    ):
        """Test that deleting a photo cascades to its faces."""
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        # 1. Create photo with faces
        photo = PhotoFactory.create()
        photo = await photo_repo.save(photo)

        faces = FaceFactory.create_batch(3, photo_id=photo.id.value)
        for face in faces:
            await face_repo.save(face)

        # 2. Verify faces exist
        retrieved_faces = await face_repo.find_by_photo_id(photo.id.value)
        assert len(retrieved_faces) == 3

        # 3. Delete photo
        await photo_repo.delete(photo.id.value)
        await test_session.commit()

        # 4. Verify faces are deleted (cascade)
        faces_after = await face_repo.find_by_photo_id(photo.id.value)
        assert len(faces_after) == 0

    @pytest.mark.asyncio
    async def test_face_embedding_update(
        self,
        test_session,
        test_vector_store,
    ):
        """Test updating face embedding (e.g., after re-processing)."""
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        # 1. Create face with initial embedding
        photo = PhotoFactory.create()
        photo = await photo_repo.save(photo)

        initial_embedding = EmbeddingFactory.create_face_embedding()
        face = FaceFactory.create(
            photo_id=photo.id.value,
            embedding=initial_embedding,
        )
        face = await face_repo.save(face)

        # 2. Store in vector store
        await test_vector_store.store_face_embedding(
            face.id.value,
            initial_embedding,
        )

        # 3. Update embedding
        new_embedding = EmbeddingFactory.create_face_embedding()
        face.embedding = new_embedding
        updated_face = await face_repo.save(face)

        # 4. Update in vector store
        await test_vector_store.store_face_embedding(
            face.id.value,
            new_embedding,
        )

        # 5. Search with new embedding
        results = await test_vector_store.search_faces(
            new_embedding,
            limit=1,
        )

        # 6. Verify updated embedding is used
        assert len(results) == 1
        assert str(results[0].id) == str(face.id.value)

    @pytest.mark.asyncio
    async def test_cluster_statistics(
        self,
        test_session,
    ):
        """Test getting statistics for face clusters."""
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        # 1. Create two clusters
        cluster1_id = uuid4()
        cluster2_id = uuid4()

        # 2. Cluster 1: 5 faces
        photos1 = PhotoFactory.create_batch(5)
        for photo in photos1:
            saved_photo = await photo_repo.save(photo)
            face = FaceFactory.create(
                photo_id=saved_photo.id.value,
                cluster_id=cluster1_id,
            )
            await face_repo.save(face)

        # 3. Cluster 2: 3 faces
        photos2 = PhotoFactory.create_batch(3)
        for photo in photos2:
            saved_photo = await photo_repo.save(photo)
            face = FaceFactory.create(
                photo_id=saved_photo.id.value,
                cluster_id=cluster2_id,
            )
            await face_repo.save(face)

        # 4. Get cluster counts
        cluster1_faces = await face_repo.find_by_cluster_id(cluster1_id)
        cluster2_faces = await face_repo.find_by_cluster_id(cluster2_id)

        # 5. Verify counts
        assert len(cluster1_faces) == 5
        assert len(cluster2_faces) == 3
