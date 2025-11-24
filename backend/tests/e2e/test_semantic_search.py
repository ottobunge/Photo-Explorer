"""End-to-end tests for semantic search with real images."""

import pytest
import pytest_asyncio
from pathlib import Path

from app.adapters.outbound.ml import MLServicesAdapter, get_ml_services
from app.adapters.outbound.persistence.qdrant import QdrantVectorStore
from app.adapters.outbound.persistence.postgres import PhotoRepositoryPostgres
from app.domain.entities import Photo, PhotoID, ConnectorType
from tests.fixtures.conftest import (
    test_images_dir,
    cat_images,
    dog_images,
    raccoon_images,
    ferret_images,
    all_test_images,
)


@pytest.mark.asyncio
class TestSemanticSearchE2E:
    """End-to-end tests for semantic search functionality with real animal photos."""

    async def test_search_for_cats_finds_cat_images(
        self, test_session, test_vector_store, test_images_dir, cat_images
    ):
        """
        E2E: Searching for 'cat' should find cat images with high relevance.

        Steps:
        1. Load cat images and generate embeddings
        2. Index them in Qdrant
        3. Search for 'cat' using text query
        4. Verify cat images rank highest
        """
        ml_services = get_ml_services()
        photo_repo = PhotoRepositoryPostgres(test_session)
        vector_store = test_vector_store

        # Step 1 & 2: Index cat images
        indexed_photos = []
        for img_path in cat_images[:3]:  # Use 3 cat images
            # Generate image embedding
            with open(img_path, "rb") as f:
                image_data = f.read()

            embedding = await ml_services.encode_image(image_data)

            # Create photo entity
            photo = Photo.create(
                filename=img_path.name,
                source_path=str(img_path),
                mime_type="image/jpeg",
                connector_type=ConnectorType.LOCAL,
            )

            # Save to database
            saved_photo = await photo_repo.save(photo)

            # Index in vector store
            await vector_store.index_photo(
                photo_id=str(saved_photo.id.value),
                embedding=embedding,
            )

            indexed_photos.append(saved_photo)

        # Step 3: Search for 'cat'
        query_embedding = await ml_services.encode_text("a photo of a cat")
        search_results = await vector_store.search_photos(
            query_embedding=query_embedding,
            limit=10,
        )

        # Step 4: Verify results
        assert len(search_results) > 0, "Should find at least one result"

        # All results should be our indexed cat photos
        result_ids = {result.id for result in search_results}
        indexed_ids = {str(photo.id.value) for photo in indexed_photos}

        assert result_ids.issubset(indexed_ids), "Results should only be our cat photos"

        # Top result should have high confidence (>0.5 similarity)
        top_result = search_results[0]
        assert top_result.score > 0.5, f"Top result should have >0.5 similarity, got {top_result.score}"

    async def test_semantic_search_distinguishes_animals(
        self, test_session, test_vector_store, all_test_images
    ):
        """
        E2E: Semantic search should distinguish between different animals.

        Steps:
        1. Index 1 image each of: cat, dog, raccoon, ferret
        2. Search for each animal by name
        3. Verify correct animal image ranks highest for each query
        """
        ml_services = get_ml_services()
        photo_repo = PhotoRepositoryPostgres(test_session)
        vector_store = test_vector_store

        # Step 1: Index one image of each animal
        indexed_by_category = {}

        for category, images in all_test_images.items():
            if not images:
                continue

            img_path = images[0]  # Use first image from each category

            # Generate embedding
            with open(img_path, "rb") as f:
                image_data = f.read()

            embedding = await ml_services.encode_image(image_data)

            # Create and save photo
            photo = Photo.create(
                filename=f"{category}_{img_path.name}",
                source_path=str(img_path),
                mime_type="image/jpeg",
                connector_type=ConnectorType.LOCAL,
            )

            saved_photo = await photo_repo.save(photo)

            # Index
            await vector_store.index_photo(
                photo_id=str(saved_photo.id.value),
                embedding=embedding,
            )

            indexed_by_category[category] = saved_photo

        # Step 2 & 3: Search for each animal and verify correct one ranks highest
        search_queries = {
            "cats": "a photo of a cat",
            "dogs": "a photo of a dog",
            "raccoons": "a photo of a raccoon",
            "ferrets": "a photo of a ferret",
        }

        for expected_category, query_text in search_queries.items():
            if expected_category not in indexed_by_category:
                continue

            # Perform search
            query_embedding = await ml_services.encode_text(query_text)
            results = await vector_store.search_photos(
                query_embedding=query_embedding,
                limit=10,
            )

            assert len(results) > 0, f"Should find results for '{query_text}'"

            # Get top result
            top_result = results[0]
            expected_photo_id = str(indexed_by_category[expected_category].id.value)

            # Verify top result is the expected animal
            assert top_result.id == expected_photo_id, (
                f"For query '{query_text}', expected {expected_category} photo "
                f"(ID: {expected_photo_id}) to rank highest, "
                f"but got ID: {top_result.id} with score {top_result.score}"
            )

    async def test_similar_image_search(
        self, test_session, test_vector_store, cat_images, dog_images
    ):
        """
        E2E: Searching with an image should find similar images.

        Steps:
        1. Index 3 cat images and 2 dog images
        2. Search using first cat image as query
        3. Verify other cat images rank higher than dog images
        """
        ml_services = get_ml_services()
        photo_repo = PhotoRepositoryPostgres(test_session)
        vector_store = test_vector_store

        # Step 1: Index images
        cat_photos = []
        dog_photos = []

        # Index 3 cats
        for img_path in cat_images[:3]:
            with open(img_path, "rb") as f:
                image_data = f.read()

            embedding = await ml_services.encode_image(image_data)

            photo = Photo.create(
                filename=f"cat_{img_path.name}",
                source_path=str(img_path),
                mime_type="image/jpeg",
                connector_type=ConnectorType.LOCAL,
            )

            saved_photo = await photo_repo.save(photo)
            await vector_store.index_photo(
                photo_id=str(saved_photo.id.value),
                embedding=embedding,
            )
            cat_photos.append(saved_photo)

        # Index 2 dogs
        for img_path in dog_images[:2]:
            with open(img_path, "rb") as f:
                image_data = f.read()

            embedding = await ml_services.encode_image(image_data)

            photo = Photo.create(
                filename=f"dog_{img_path.name}",
                source_path=str(img_path),
                mime_type="image/jpeg",
                connector_type=ConnectorType.LOCAL,
            )

            saved_photo = await photo_repo.save(photo)
            await vector_store.index_photo(
                photo_id=str(saved_photo.id.value),
                embedding=embedding,
            )
            dog_photos.append(saved_photo)

        # Step 2: Search using first cat image
        query_image_path = cat_images[0]
        with open(query_image_path, "rb") as f:
            query_image_data = f.read()

        query_embedding = await ml_services.encode_image(query_image_data)
        results = await vector_store.search_photos(
            query_embedding=query_embedding,
            limit=10,
        )

        # Step 3: Verify ranking
        assert len(results) >= 4, "Should find at least 4 results"

        # Get result IDs
        result_ids = [result.id for result in results]
        cat_ids = [str(photo.id.value) for photo in cat_photos]
        dog_ids = [str(photo.id.value) for photo in dog_photos]

        # Find positions of cats and dogs in results
        cat_positions = [i for i, rid in enumerate(result_ids) if rid in cat_ids]
        dog_positions = [i for i, rid in enumerate(result_ids) if rid in dog_ids]

        # All cat positions should come before dog positions
        if cat_positions and dog_positions:
            max_cat_position = max(cat_positions)
            min_dog_position = min(dog_positions)

            assert max_cat_position < min_dog_position, (
                f"Cat images should rank higher than dog images. "
                f"Cat positions: {cat_positions}, Dog positions: {dog_positions}"
            )

    @pytest.mark.parametrize("animal,query", [
        ("cat", "feline"),
        ("dog", "puppy"),
        ("dog", "canine"),
        ("raccoon", "masked animal"),
    ])
    async def test_semantic_understanding(
        self, test_session, test_vector_store, all_test_images, animal, query
    ):
        """
        E2E: Semantic search should understand related terms (feline = cat, puppy = dog).

        Tests that CLIP embeddings capture semantic meaning, not just exact word matching.
        """
        if animal not in all_test_images or not all_test_images[animal]:
            pytest.skip(f"No {animal} images available")

        ml_services = get_ml_services()
        photo_repo = PhotoRepositoryPostgres(test_session)
        vector_store = test_vector_store

        # Index the target animal image
        img_path = all_test_images[animal][0]

        with open(img_path, "rb") as f:
            image_data = f.read()

        embedding = await ml_services.encode_image(image_data)

        photo = Photo.create(
            filename=img_path.name,
            source_path=str(img_path),
            mime_type="image/jpeg",
            connector_type=ConnectorType.LOCAL,
        )

        saved_photo = await photo_repo.save(photo)
        await vector_store.index_photo(
            photo_id=str(saved_photo.id.value),
            embedding=embedding,
        )

        # Search using semantic query
        query_embedding = await ml_services.encode_text(query)
        results = await vector_store.search_photos(
            query_embedding=query_embedding,
            limit=5,
        )

        # Should find the target image
        assert len(results) > 0, f"Should find results for '{query}'"

        result_ids = [result.id for result in results]
        expected_id = str(saved_photo.id.value)

        assert expected_id in result_ids, (
            f"Semantic search for '{query}' should find {animal} image "
            f"(ID: {expected_id}), but got: {result_ids}"
        )
