"""Integration tests for photo upload and processing flow.

Tests the complete flow:
1. Upload photo via file storage
2. Create photo in database
3. Generate thumbnail
4. Create embedding in Qdrant
5. Detect faces (mocked)
"""

import io
from datetime import UTC
from uuid import uuid4

import pytest
from PIL import Image

from app.adapters.outbound.persistence.postgres.repositories import (
    FaceRepositoryPostgres,
    PhotoRepositoryPostgres,
)
from app.domain.value_objects import BoundingBox
from tests.integration.factories import EmbeddingFactory, FaceFactory, PhotoFactory


class TestPhotoUploadAndProcessingFlow:
    """Test complete photo upload and processing workflow."""

    @pytest.mark.asyncio
    async def test_upload_photo_end_to_end(
        self,
        test_session,
        test_file_storage,
        test_vector_store,
        sample_image_bytes,
    ):
        """Test complete photo upload flow: storage -> database -> thumbnail -> embedding."""
        # 1. Upload photo to file storage
        photo_id = uuid4()
        file = io.BytesIO(sample_image_bytes)
        storage_path = await test_file_storage.save_photo(file, "test_photo.jpg")

        assert storage_path is not None
        assert len(storage_path) > 0

        # 2. Create photo in database
        photo_repo = PhotoRepositoryPostgres(test_session)
        photo = PhotoFactory.create(
            id=photo_id,
            filename="test_photo.jpg",
            storage_path=storage_path,
            processing_status="pending",
        )
        saved_photo = await photo_repo.save(photo)

        assert saved_photo.id.value == photo_id
        assert saved_photo.storage_path == storage_path

        # 3. Verify photo exists in database
        retrieved_photo = await photo_repo.find_by_id(photo_id)
        assert retrieved_photo is not None
        assert retrieved_photo.filename == "test_photo.jpg"
        assert retrieved_photo.processing_status == "pending"

        # 4. Generate thumbnail
        thumbnail_data = await test_file_storage.read_photo(storage_path)
        thumbnail_path = await test_file_storage.save_thumbnail(
            thumbnail_data,
            str(photo_id),
        )

        # Update photo with thumbnail path
        retrieved_photo.thumbnail_path = thumbnail_path
        updated_photo = await photo_repo.save(retrieved_photo)
        assert updated_photo.thumbnail_path == thumbnail_path

        # 5. Generate and store embedding
        embedding = EmbeddingFactory.create_clip_embedding(dimension=768)
        await test_vector_store.store_photo_embedding(
            photo_id,
            embedding,
            payload={"filename": "test_photo.jpg"},
        )

        # 6. Verify embedding exists in vector store
        results = await test_vector_store.search_photos(
            embedding,
            limit=1,
        )
        assert len(results) == 1
        assert str(results[0].id) == str(photo_id)

        # 7. Update processing status
        retrieved_photo.processing_status = "completed"
        final_photo = await photo_repo.save(retrieved_photo)
        assert final_photo.processing_status == "completed"

    @pytest.mark.asyncio
    async def test_photo_with_face_detection(
        self,
        test_session,
        test_file_storage,
        test_vector_store,
        sample_image_bytes,
    ):
        """Test photo processing with face detection."""
        # 1. Create photo
        photo_id = uuid4()
        photo_repo = PhotoRepositoryPostgres(test_session)
        photo = PhotoFactory.create(
            id=photo_id,
            filename="photo_with_faces.jpg",
        )
        await photo_repo.save(photo)

        # 2. Simulate face detection (in real flow, this would be done by ML service)
        face_repo = FaceRepositoryPostgres(test_session)

        # Create multiple faces
        face1 = FaceFactory.create(
            photo_id=photo_id,
            bounding_box=BoundingBox(x=100, y=100, width=150, height=150),
            confidence=0.95,
            embedding=EmbeddingFactory.create_face_embedding(),
        )
        face2 = FaceFactory.create(
            photo_id=photo_id,
            bounding_box=BoundingBox(x=300, y=120, width=140, height=140),
            confidence=0.92,
            embedding=EmbeddingFactory.create_face_embedding(),
        )

        saved_face1 = await face_repo.save(face1)
        saved_face2 = await face_repo.save(face2)

        # 3. Store face embeddings in vector store
        await test_vector_store.store_face_embedding(
            saved_face1.id.value,
            saved_face1.embedding,
            payload={"photo_id": str(photo_id)},
        )
        await test_vector_store.store_face_embedding(
            saved_face2.id.value,
            saved_face2.embedding,
            payload={"photo_id": str(photo_id)},
        )

        # 4. Verify faces are stored
        faces = await face_repo.find_by_photo_id(photo_id)
        assert len(faces) == 2
        assert all(f.photo_id == photo_id for f in faces)

        # 5. Search for similar faces in vector store
        results = await test_vector_store.search_faces(
            saved_face1.embedding,
            limit=2,
        )
        assert len(results) >= 1
        assert str(results[0].id) == str(saved_face1.id.value)

    @pytest.mark.asyncio
    async def test_photo_processing_failure_recovery(
        self,
        test_session,
        test_file_storage,
    ):
        """Test that photo status is updated correctly on processing failures."""
        # 1. Create photo with pending status
        photo_id = uuid4()
        photo_repo = PhotoRepositoryPostgres(test_session)
        photo = PhotoFactory.create(
            id=photo_id,
            processing_status="pending",
        )
        await photo_repo.save(photo)

        # 2. Simulate processing failure
        photo.processing_status = "failed"
        updated = await photo_repo.save(photo)
        assert updated.processing_status == "failed"

        # 3. Retry processing
        photo.processing_status = "processing"
        retrying = await photo_repo.save(photo)
        assert retrying.processing_status == "processing"

        # 4. Mark as completed
        photo.processing_status = "completed"
        completed = await photo_repo.save(photo)
        assert completed.processing_status == "completed"

    @pytest.mark.asyncio
    async def test_multiple_photos_batch_processing(
        self,
        test_session,
        test_file_storage,
        test_vector_store,
    ):
        """Test processing multiple photos in a batch."""
        photo_repo = PhotoRepositoryPostgres(test_session)
        photo_ids = []

        # 1. Create multiple photos
        for i in range(5):
            photo = PhotoFactory.create(
                filename=f"batch_photo_{i}.jpg",
                processing_status="pending",
            )
            saved = await photo_repo.save(photo)
            photo_ids.append(saved.id.value)

        # 2. Verify all photos are pending
        pending = await photo_repo.find_pending_processing(limit=10)
        assert len(pending) >= 5

        # 3. Process each photo
        for photo_id in photo_ids:
            photo = await photo_repo.find_by_id(photo_id)
            assert photo is not None

            # Generate embedding
            embedding = EmbeddingFactory.create_clip_embedding()
            await test_vector_store.store_photo_embedding(
                photo_id,
                embedding,
            )

            # Update status
            photo.processing_status = "completed"
            await photo_repo.save(photo)

        # 4. Verify all photos are completed
        for photo_id in photo_ids:
            photo = await photo_repo.find_by_id(photo_id)
            assert photo.processing_status == "completed"

        # 5. No more pending photos
        pending_after = await photo_repo.find_pending_processing(limit=10)
        pending_count = len([p for p in pending_after if p.id.value in photo_ids])
        assert pending_count == 0

    @pytest.mark.asyncio
    async def test_thumbnail_generation(
        self,
        test_file_storage,
        sample_image_bytes,
    ):
        """Test thumbnail generation from original photo."""
        # 1. Save original photo
        file = io.BytesIO(sample_image_bytes)
        storage_path = await test_file_storage.save_photo(file, "original.jpg")

        # 2. Read back the photo
        photo_data = await test_file_storage.read_photo(storage_path)
        assert len(photo_data) > 0

        # 3. Generate thumbnail
        photo_id = uuid4()
        thumbnail_path = await test_file_storage.save_thumbnail(
            photo_data,
            str(photo_id),
        )
        assert thumbnail_path is not None

        # 4. Verify thumbnail exists and is readable
        thumbnail_data = await test_file_storage.read_thumbnail(thumbnail_path)
        assert len(thumbnail_data) > 0

        # 5. Verify thumbnail is valid image
        thumbnail_image = Image.open(io.BytesIO(thumbnail_data))
        assert thumbnail_image.size[0] <= 400  # Max thumbnail width
        assert thumbnail_image.size[1] <= 400  # Max thumbnail height

    @pytest.mark.asyncio
    async def test_photo_deletion_cascade(
        self,
        test_session,
        test_file_storage,
        test_vector_store,
    ):
        """Test that deleting a photo cascades to faces and embeddings."""
        # 1. Create photo with faces
        photo_id = uuid4()
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        photo = PhotoFactory.create(id=photo_id)
        await photo_repo.save(photo)

        face = FaceFactory.create(photo_id=photo_id)
        await face_repo.save(face)

        # 2. Store embeddings
        photo_embedding = EmbeddingFactory.create_clip_embedding()
        await test_vector_store.store_photo_embedding(photo_id, photo_embedding)

        face_embedding = EmbeddingFactory.create_face_embedding()
        await test_vector_store.store_face_embedding(face.id.value, face_embedding)

        # 3. Verify everything exists
        assert await photo_repo.find_by_id(photo_id) is not None
        faces = await face_repo.find_by_photo_id(photo_id)
        assert len(faces) == 1

        # 4. Delete photo
        await photo_repo.delete(photo_id)
        await test_session.commit()

        # 5. Verify photo is deleted
        assert await photo_repo.find_by_id(photo_id) is None

        # 6. Verify faces are deleted (cascade)
        faces_after = await face_repo.find_by_photo_id(photo_id)
        assert len(faces_after) == 0

        # Note: Vector store cleanup would be handled by separate cleanup process

    @pytest.mark.asyncio
    async def test_photo_metadata_extraction(
        self,
        test_session,
        sample_image_bytes,
    ):
        """Test photo metadata extraction and storage."""
        from datetime import datetime

        # 1. Create photo with metadata
        photo_repo = PhotoRepositoryPostgres(test_session)
        photo = PhotoFactory.create(
            filename="photo_with_metadata.jpg",
            width=1920,
            height=1080,
            mime_type="image/jpeg",
            file_size=len(sample_image_bytes),
            taken_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        )

        saved = await photo_repo.save(photo)

        # 2. Verify metadata is stored
        assert saved.width == 1920
        assert saved.height == 1080
        assert saved.mime_type == "image/jpeg"
        assert saved.file_size == len(sample_image_bytes)
        assert saved.taken_at is not None

        # 3. Retrieve and verify
        retrieved = await photo_repo.find_by_id(saved.id.value)
        assert retrieved.width == 1920
        assert retrieved.height == 1080
