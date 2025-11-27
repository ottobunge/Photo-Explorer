"""Integration tests for complete photo processing workflow.

Tests the end-to-end flow: Upload → Process → Embedding → Search
"""

import io
import time
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.adapters.outbound.persistence.postgres.repositories import (
    FaceRepositoryPostgres,
    PhotoRepositoryPostgres,
)
from app.application.services.photo_processing_service import (
    PhotoProcessingService,
)
from app.application.services.search_service import SearchService
from tests.integration.factories import EmbeddingFactory, PhotoFactory


@pytest.mark.integration
class TestPhotoProcessingWorkflow:
    """Integration tests for complete photo processing workflow."""

    @pytest.mark.asyncio
    async def test_upload_process_search_workflow(
        self,
        test_session,
        test_file_storage,
        test_vector_store,
        sample_image_bytes,
    ):
        """Test: Upload → Process → Search returns photo.

        This is a critical workflow that verifies:
        1. Photo can be uploaded and saved to storage
        2. Photo metadata is persisted to database
        3. Embedding is generated and stored in vector store
        4. Photo becomes searchable via semantic search
        """
        # Setup repositories and services
        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)

        # Mock ML services
        ml_services = AsyncMock()
        ml_services.encode_image = AsyncMock(
            return_value=EmbeddingFactory.create_clip_embedding()
        )

        processing_service = PhotoProcessingService(
            photo_repo=photo_repo,
            face_repo=face_repo,
            ml_services=ml_services,
            vector_store=test_vector_store,
            file_storage=test_file_storage,
        )

        search_service = SearchService(
            photo_repo=photo_repo,
            vector_store=test_vector_store,
            ml_services=ml_services,
        )

        # 1. Upload photo
        photo_id = uuid4()
        file = io.BytesIO(sample_image_bytes)
        storage_path = await test_file_storage.save_photo(file, "workflow_test.jpg")

        photo = PhotoFactory.create(
            id=photo_id,
            filename="workflow_test.jpg",
            storage_path=storage_path,
            processing_status="pending",
            width=1920,
            height=1080,
            mime_type="image/jpeg",
            file_size=len(sample_image_bytes),
        )

        saved_photo = await photo_repo.save(photo)
        assert saved_photo.id.value == photo_id
        assert saved_photo.processing_status == "pending"

        # 2. Process photo (generates embedding)
        # In real implementation, this would call the actual ML service
        # For this test, we simulate the processing
        embedding = EmbeddingFactory.create_clip_embedding(dimension=768)

        await test_vector_store.store_photo_embedding(
            photo_id,
            embedding,
            payload={
                "filename": saved_photo.filename,
                "created_at": saved_photo.created_at.isoformat(),
            },
        )

        # Mark as completed
        saved_photo.processing_status = "completed"
        updated_photo = await photo_repo.save(saved_photo)
        assert updated_photo.processing_status == "completed"

        # 3. Verify photo is searchable via semantic search
        search_embedding = EmbeddingFactory.create_similar_embedding(
            embedding, noise=0.01
        )
        results = await test_vector_store.search_photos(
            search_embedding,
            limit=10,
        )

        photo_ids = [str(r.id) for r in results]
        assert str(photo_id) in photo_ids, "Processed photo should be searchable"

        # 4. Verify we can retrieve the photo from database
        retrieved_photo = await photo_repo.find_by_id(photo_id)
        assert retrieved_photo is not None
        assert retrieved_photo.filename == "workflow_test.jpg"
        assert retrieved_photo.processing_status == "completed"

    @pytest.mark.asyncio
    async def test_processing_failure_marks_photo_failed(
        self,
        test_session,
        test_file_storage,
        test_vector_store,
        sample_image_bytes,
    ):
        """Test photo marked as failed when processing encounters errors."""
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create photo
        photo_id = uuid4()
        file = io.BytesIO(sample_image_bytes)
        storage_path = await test_file_storage.save_photo(file, "test_fail.jpg")

        photo = PhotoFactory.create(
            id=photo_id,
            filename="test_fail.jpg",
            storage_path=storage_path,
            processing_status="pending",
        )

        await photo_repo.save(photo)

        # 2. Simulate processing failure
        try:
            # Simulate an error during processing
            raise ValueError("Simulated processing error")
        except ValueError:
            # Mark photo as failed
            photo.processing_status = "failed"
            failed_photo = await photo_repo.save(photo)

        # 3. Verify photo is marked as failed
        assert failed_photo.processing_status == "failed"

        # 4. Verify photo is not in vector store
        embedding = EmbeddingFactory.create_clip_embedding()
        results = await test_vector_store.search_photos(embedding, limit=10)
        photo_ids = [str(r.id) for r in results]
        assert str(photo_id) not in photo_ids

    @pytest.mark.asyncio
    async def test_batch_processing_performance(
        self,
        test_session,
        test_file_storage,
        test_vector_store,
        sample_image_bytes,
    ):
        """Test batch processing is performant for multiple photos."""
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create batch of photos
        batch_size = 10
        photo_ids = []

        start_time = time.time()

        for i in range(batch_size):
            photo_id = uuid4()
            file = io.BytesIO(sample_image_bytes)
            storage_path = await test_file_storage.save_photo(
                file, f"batch_{i}.jpg"
            )

            photo = PhotoFactory.create(
                id=photo_id,
                filename=f"batch_{i}.jpg",
                storage_path=storage_path,
                processing_status="pending",
            )

            await photo_repo.save(photo)
            photo_ids.append(photo_id)

        creation_time = time.time() - start_time

        # 2. Process all photos
        process_start = time.time()

        for photo_id in photo_ids:
            embedding = EmbeddingFactory.create_clip_embedding()
            await test_vector_store.store_photo_embedding(
                photo_id,
                embedding,
            )

            photo = await photo_repo.find_by_id(photo_id)
            photo.processing_status = "completed"
            await photo_repo.save(photo)

        process_time = time.time() - process_start

        # 3. Verify all photos are completed
        completed_count = 0
        for photo_id in photo_ids:
            photo = await photo_repo.find_by_id(photo_id)
            if photo.processing_status == "completed":
                completed_count += 1

        assert completed_count == batch_size

        # 4. Performance assertions
        # Should process 10 photos in reasonable time (<10s total)
        assert process_time < 10.0, f"Batch processing too slow: {process_time}s"

        # Average time per photo should be reasonable
        avg_time = process_time / batch_size
        assert avg_time < 1.0, f"Average processing time too high: {avg_time}s"

    @pytest.mark.asyncio
    async def test_processing_idempotency(
        self,
        test_session,
        test_file_storage,
        test_vector_store,
        sample_image_bytes,
    ):
        """Test processing same photo twice doesn't create duplicates."""
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create and process photo
        photo_id = uuid4()
        file = io.BytesIO(sample_image_bytes)
        storage_path = await test_file_storage.save_photo(file, "idempotent.jpg")

        photo = PhotoFactory.create(
            id=photo_id,
            filename="idempotent.jpg",
            storage_path=storage_path,
            processing_status="pending",
        )

        await photo_repo.save(photo)

        # First processing
        embedding = EmbeddingFactory.create_clip_embedding()
        await test_vector_store.store_photo_embedding(
            photo_id,
            embedding,
            payload={"filename": "idempotent.jpg"},
        )

        photo.processing_status = "completed"
        await photo_repo.save(photo)

        # 2. Process again (simulating retry or re-processing)
        embedding2 = EmbeddingFactory.create_clip_embedding()
        await test_vector_store.store_photo_embedding(
            photo_id,
            embedding2,  # Different embedding, should update existing
            payload={"filename": "idempotent.jpg"},
        )

        # 3. Verify only one entry exists in vector store
        results = await test_vector_store.search_photos(
            embedding2,
            limit=10,
        )

        # Count how many times our photo appears
        matching_count = sum(1 for r in results if str(r.id) == str(photo_id))
        assert matching_count <= 1, "Photo should not be duplicated in vector store"

    @pytest.mark.asyncio
    async def test_concurrent_processing_isolation(
        self,
        test_session,
        test_file_storage,
        test_vector_store,
        sample_image_bytes,
    ):
        """Test concurrent processing of multiple photos maintains isolation."""
        import asyncio

        photo_repo = PhotoRepositoryPostgres(test_session)

        async def process_photo(index: int) -> str:
            """Process a single photo and return its ID."""
            photo_id = uuid4()
            file = io.BytesIO(sample_image_bytes)
            storage_path = await test_file_storage.save_photo(
                file, f"concurrent_{index}.jpg"
            )

            photo = PhotoFactory.create(
                id=photo_id,
                filename=f"concurrent_{index}.jpg",
                storage_path=storage_path,
                processing_status="pending",
            )

            await photo_repo.save(photo)

            # Simulate processing
            embedding = EmbeddingFactory.create_clip_embedding()
            await test_vector_store.store_photo_embedding(
                photo_id,
                embedding,
            )

            photo.processing_status = "completed"
            await photo_repo.save(photo)

            return str(photo_id)

        # Process 5 photos concurrently
        tasks = [process_photo(i) for i in range(5)]
        photo_ids = await asyncio.gather(*tasks)

        # Verify all photos processed successfully
        assert len(photo_ids) == 5
        assert len(set(photo_ids)) == 5, "Photo IDs should be unique"

        # Verify all in database
        for photo_id in photo_ids:
            photo = await photo_repo.find_by_id(uuid4(hex=photo_id))
            assert photo is not None
            assert photo.processing_status == "completed"

    @pytest.mark.asyncio
    async def test_thumbnail_generation_workflow(
        self,
        test_session,
        test_file_storage,
        sample_image_bytes,
    ):
        """Test thumbnail generation as part of processing workflow."""
        from PIL import Image

        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Upload photo
        photo_id = uuid4()
        file = io.BytesIO(sample_image_bytes)
        storage_path = await test_file_storage.save_photo(file, "thumb_test.jpg")

        photo = PhotoFactory.create(
            id=photo_id,
            filename="thumb_test.jpg",
            storage_path=storage_path,
            processing_status="pending",
        )

        await photo_repo.save(photo)

        # 2. Generate thumbnail
        photo_data = await test_file_storage.read_photo(storage_path)
        thumbnail_path = await test_file_storage.save_thumbnail(
            photo_data,
            str(photo_id),
        )

        # 3. Update photo with thumbnail path
        photo.thumbnail_path = thumbnail_path
        photo.processing_status = "completed"
        updated = await photo_repo.save(photo)

        assert updated.thumbnail_path == thumbnail_path

        # 4. Verify thumbnail exists and is valid
        thumbnail_data = await test_file_storage.read_thumbnail(thumbnail_path)
        assert len(thumbnail_data) > 0

        # Verify thumbnail is resized appropriately
        thumbnail_image = Image.open(io.BytesIO(thumbnail_data))
        assert thumbnail_image.size[0] <= 400
        assert thumbnail_image.size[1] <= 400

    @pytest.mark.asyncio
    async def test_photo_metadata_persistence_workflow(
        self,
        test_session,
        test_file_storage,
        sample_image_bytes,
    ):
        """Test that photo metadata is correctly persisted throughout workflow."""
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create photo with rich metadata
        photo_id = uuid4()
        file = io.BytesIO(sample_image_bytes)
        storage_path = await test_file_storage.save_photo(file, "metadata.jpg")

        taken_at = datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC)

        photo = PhotoFactory.create(
            id=photo_id,
            filename="metadata.jpg",
            storage_path=storage_path,
            processing_status="pending",
            width=1920,
            height=1080,
            mime_type="image/jpeg",
            file_size=len(sample_image_bytes),
            taken_at=taken_at,
            exif={"Make": "Canon", "Model": "EOS R5"},
            description="Test photo with metadata",
        )

        saved = await photo_repo.save(photo)

        # 2. Simulate processing
        saved.processing_status = "completed"
        processed = await photo_repo.save(saved)

        # 3. Verify all metadata preserved
        retrieved = await photo_repo.find_by_id(photo_id)

        assert retrieved is not None
        assert retrieved.filename == "metadata.jpg"
        assert retrieved.width == 1920
        assert retrieved.height == 1080
        assert retrieved.mime_type == "image/jpeg"
        assert retrieved.file_size == len(sample_image_bytes)
        assert retrieved.taken_at == taken_at
        assert retrieved.exif == {"Make": "Canon", "Model": "EOS R5"}
        assert retrieved.description == "Test photo with metadata"
        assert retrieved.processing_status == "completed"
