"""End-to-end tests for local file upload and processing."""

import pytest
import pytest_asyncio
from pathlib import Path

from app.adapters.outbound.ml import get_ml_services
from app.adapters.outbound.persistence.qdrant import QdrantVectorStore
from app.adapters.outbound.persistence.postgres import PhotoRepositoryPostgres
from app.adapters.outbound.storage import LocalFileStorage
from app.domain.entities import Photo, ConnectorType


@pytest.mark.asyncio
class TestLocalFileUploadE2E:
    """End-to-end tests for uploading local files and full processing pipeline."""

    async def test_upload_photo_generates_thumbnail(
        self, test_session, test_file_storage, cat_images
    ):
        """
        E2E: Uploading a photo should generate a thumbnail.

        Steps:
        1. Upload a cat image
        2. Save to storage
        3. Generate thumbnail
        4. Verify thumbnail exists and is smaller than original
        """
        if not cat_images:
            pytest.skip("No cat images available")

        photo_repo = PhotoRepositoryPostgres(test_session)
        file_storage = test_file_storage

        # Step 1: Load cat image
        source_path = cat_images[0]
        with open(source_path, "rb") as f:
            image_data = f.read()

        # Step 2: Create photo entity and save
        photo = Photo.create(
            filename=source_path.name,
            source_path=str(source_path),
            mime_type="image/jpeg",
            connector_type=ConnectorType.LOCAL,
        )

        # Save image data to storage
        storage_path = await file_storage.save_photo(
            photo_id=str(photo.id.value),
            file_data=image_data,
            filename=source_path.name,
        )
        photo.storage_path = storage_path

        # Step 3: Generate thumbnail
        thumbnail_data = await file_storage.generate_thumbnail(
            image_data=image_data,
            max_size=(300, 300),
        )

        thumbnail_path = await file_storage.save_thumbnail(
            photo_id=str(photo.id.value),
            thumbnail_data=thumbnail_data,
        )
        photo.thumbnail_path = thumbnail_path

        # Save to database
        saved_photo = await photo_repo.save(photo)

        # Step 4: Verify thumbnail exists and is valid
        assert saved_photo.thumbnail_path is not None
        assert Path(saved_photo.thumbnail_path).exists()

        # Verify thumbnail is smaller than original
        thumbnail_size = Path(saved_photo.thumbnail_path).stat().st_size
        original_size = len(image_data)

        assert thumbnail_size < original_size, (
            f"Thumbnail ({thumbnail_size} bytes) should be smaller than "
            f"original ({original_size} bytes)"
        )

    async def test_upload_photo_generates_embedding(
        self, test_session, test_vector_store, test_file_storage, dog_images
    ):
        """
        E2E: Uploading a photo should generate CLIP embedding and index in Qdrant.

        Steps:
        1. Upload a dog image
        2. Generate CLIP embedding
        3. Index in Qdrant
        4. Verify can retrieve and search
        """
        if not dog_images:
            pytest.skip("No dog images available")

        ml_services = get_ml_services()
        photo_repo = PhotoRepositoryPostgres(test_session)
        vector_store = test_vector_store
        file_storage = test_file_storage

        # Step 1: Upload dog image
        source_path = dog_images[0]
        with open(source_path, "rb") as f:
            image_data = f.read()

        photo = Photo.create(
            filename=source_path.name,
            source_path=str(source_path),
            mime_type="image/jpeg",
            connector_type=ConnectorType.LOCAL,
        )

        storage_path = await file_storage.save_photo(
            photo_id=str(photo.id.value),
            file_data=image_data,
            filename=source_path.name,
        )
        photo.storage_path = storage_path

        saved_photo = await photo_repo.save(photo)

        # Step 2: Generate embedding
        embedding = await ml_services.encode_image(image_data)

        assert embedding is not None
        assert len(embedding) > 0, "Embedding should not be empty"

        # Step 3: Index in Qdrant
        await vector_store.index_photo(
            photo_id=str(saved_photo.id.value),
            embedding=embedding,
        )

        # Step 4: Verify can search and find it
        query_embedding = await ml_services.encode_text("a dog")
        results = await vector_store.search_photos(
            query_embedding=query_embedding,
            limit=10,
        )

        result_ids = [result.id for result in results]
        expected_id = str(saved_photo.id.value)

        assert expected_id in result_ids, (
            f"Should be able to find uploaded photo (ID: {expected_id}) "
            f"in search results: {result_ids}"
        )

    async def test_batch_upload_and_search(
        self, test_session, test_vector_store, test_file_storage, all_test_images
    ):
        """
        E2E: Upload multiple photos and verify they can all be searched.

        Steps:
        1. Upload 2 cats, 2 dogs, 1 raccoon
        2. Generate embeddings and index all
        3. Search for each animal type
        4. Verify correct photos found
        """
        ml_services = get_ml_services()
        photo_repo = PhotoRepositoryPostgres(test_session)
        vector_store = test_vector_store
        file_storage = test_file_storage

        # Step 1: Upload multiple photos
        uploaded_photos = {}

        for category in ["cats", "dogs", "raccoons"]:
            if category not in all_test_images or not all_test_images[category]:
                continue

            num_to_upload = 2 if category in ["cats", "dogs"] else 1
            uploaded_photos[category] = []

            for img_path in all_test_images[category][:num_to_upload]:
                with open(img_path, "rb") as f:
                    image_data = f.read()

                # Create photo
                photo = Photo.create(
                    filename=f"{category}_{img_path.name}",
                    source_path=str(img_path),
                    mime_type="image/jpeg",
                    connector_type=ConnectorType.LOCAL,
                )

                # Save to storage
                storage_path = await file_storage.save_photo(
                    photo_id=str(photo.id.value),
                    file_data=image_data,
                    filename=photo.filename,
                )
                photo.storage_path = storage_path

                # Generate thumbnail
                thumbnail_data = await file_storage.generate_thumbnail(
                    image_data=image_data,
                    max_size=(300, 300),
                )
                thumbnail_path = await file_storage.save_thumbnail(
                    photo_id=str(photo.id.value),
                    thumbnail_data=thumbnail_data,
                )
                photo.thumbnail_path = thumbnail_path

                # Save to database
                saved_photo = await photo_repo.save(photo)

                # Step 2: Generate embedding and index
                embedding = await ml_services.encode_image(image_data)
                await vector_store.index_photo(
                    photo_id=str(saved_photo.id.value),
                    embedding=embedding,
                )

                uploaded_photos[category].append(saved_photo)

        # Step 3 & 4: Search for each category and verify
        search_queries = {
            "cats": "a cat",
            "dogs": "a dog",
            "raccoons": "a raccoon",
        }

        for category, query_text in search_queries.items():
            if category not in uploaded_photos:
                continue

            # Search
            query_embedding = await ml_services.encode_text(query_text)
            results = await vector_store.search_photos(
                query_embedding=query_embedding,
                limit=10,
            )

            # Verify uploaded photos of this category are in results
            result_ids = {result.id for result in results}
            expected_ids = {
                str(photo.id.value) for photo in uploaded_photos[category]
            }

            found_ids = expected_ids.intersection(result_ids)

            assert len(found_ids) > 0, (
                f"Should find at least one {category} photo when searching for '{query_text}'. "
                f"Expected IDs: {expected_ids}, Results: {result_ids}"
            )

    async def test_full_pipeline_with_real_file(
        self, test_session, test_vector_store, test_file_storage, ferret_images
    ):
        """
        E2E: Complete upload-to-search pipeline with a real file.

        Simulates the full user journey:
        1. User uploads a photo (ferret)
        2. System saves file to storage
        3. System generates thumbnail
        4. System extracts any EXIF data (skip for now)
        5. System generates CLIP embedding
        6. System indexes in vector database
        7. User searches for 'ferret'
        8. System returns the uploaded photo
        """
        if not ferret_images:
            pytest.skip("No ferret images available")

        ml_services = get_ml_services()
        photo_repo = PhotoRepositoryPostgres(test_session)
        vector_store = test_vector_store
        file_storage = test_file_storage

        # Step 1: User uploads a photo
        upload_path = ferret_images[0]
        with open(upload_path, "rb") as f:
            uploaded_data = f.read()

        # Step 2: System saves file to storage
        photo = Photo.create(
            filename=upload_path.name,
            source_path=str(upload_path),
            mime_type="image/jpeg",
            file_size=len(uploaded_data),
            connector_type=ConnectorType.LOCAL,
        )

        storage_path = await file_storage.save_photo(
            photo_id=str(photo.id.value),
            file_data=uploaded_data,
            filename=photo.filename,
        )
        photo.storage_path = storage_path

        # Step 3: System generates thumbnail
        thumbnail_data = await file_storage.generate_thumbnail(
            image_data=uploaded_data,
            max_size=(300, 300),
        )
        thumbnail_path = await file_storage.save_thumbnail(
            photo_id=str(photo.id.value),
            thumbnail_data=thumbnail_data,
        )
        photo.thumbnail_path = thumbnail_path

        # Step 5: System generates CLIP embedding
        embedding = await ml_services.encode_image(uploaded_data)

        # Save photo to database
        photo.processing_status = "completed"
        saved_photo = await photo_repo.save(photo)

        # Step 6: System indexes in vector database
        await vector_store.index_photo(
            photo_id=str(saved_photo.id.value),
            embedding=embedding,
        )

        # Step 7: User searches for 'ferret'
        query_embedding = await ml_services.encode_text("a photo of a ferret")
        search_results = await vector_store.search_photos(
            query_embedding=query_embedding,
            limit=10,
        )

        # Step 8: System returns the uploaded photo
        assert len(search_results) > 0, "Search should return results"

        result_ids = [result.id for result in search_results]
        expected_id = str(saved_photo.id.value)

        assert expected_id in result_ids, (
            f"Uploaded ferret photo (ID: {expected_id}) should be found "
            f"when searching for 'ferret'. Results: {result_ids}"
        )

        # Verify photo details are preserved
        top_result_id = search_results[0].id
        found_photo = await photo_repo.find_by_id(top_result_id)

        assert found_photo is not None
        assert found_photo.filename == upload_path.name
        assert found_photo.storage_path is not None
        assert found_photo.thumbnail_path is not None
        assert found_photo.processing_status == "completed"
