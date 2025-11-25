"""Integration tests for semantic search flow.

Tests:
1. Index photos with embeddings
2. Semantic search by text query
3. Visual similarity search
4. Filtering by connector/album
5. Ranking by similarity score
"""


import pytest

from app.adapters.outbound.persistence.postgres.repositories import (
    ConnectorRepositoryPostgres,
    PhotoRepositoryPostgres,
)
from tests.integration.factories import (
    ConnectorFactory,
    EmbeddingFactory,
    PhotoFactory,
)


class TestSemanticSearchFlow:
    """Test semantic search functionality."""

    @pytest.mark.asyncio
    async def test_index_and_search_photos(
        self,
        test_session,
        test_vector_store,
    ):
        """Test indexing photos and searching by embedding."""
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create and index multiple photos
        photos = []
        embeddings = []
        for i in range(10):
            photo = PhotoFactory.create(
                filename=f"photo_{i}.jpg",
                description=f"Photo description {i}",
            )
            saved = await photo_repo.save(photo)
            photos.append(saved)

            # Create unique embedding for each photo
            embedding = EmbeddingFactory.create_clip_embedding()
            embeddings.append(embedding)

            await test_vector_store.store_photo_embedding(
                saved.id.value,
                embedding,
                payload={"filename": saved.filename},
            )

        # 2. Search using first photo's embedding
        query_embedding = embeddings[0]
        results = await test_vector_store.search_photos(
            query_embedding,
            limit=5,
        )

        # 3. Verify results
        assert len(results) >= 1
        assert len(results) <= 5

        # First result should be the query photo itself (highest similarity)
        assert str(results[0].id) == str(photos[0].id.value)
        assert results[0].score >= 0.99  # Very high similarity to itself

        # Results should be ordered by score (descending)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_search_with_similar_embeddings(
        self,
        test_session,
        test_vector_store,
    ):
        """Test that similar photos rank higher in search results."""
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create base photo and embedding
        base_photo = PhotoFactory.create(filename="base_photo.jpg")
        base_photo = await photo_repo.save(base_photo)
        base_embedding = EmbeddingFactory.create_clip_embedding()

        await test_vector_store.store_photo_embedding(
            base_photo.id.value,
            base_embedding,
        )

        # 2. Create similar photos with similar embeddings
        similar_photos = []
        for i in range(3):
            photo = PhotoFactory.create(filename=f"similar_{i}.jpg")
            photo = await photo_repo.save(photo)
            similar_photos.append(photo)

            # Create embedding similar to base
            similar_embedding = EmbeddingFactory.create_similar_embedding(
                base_embedding,
                noise=0.05,  # Small noise = high similarity
            )
            await test_vector_store.store_photo_embedding(
                photo.id.value,
                similar_embedding,
            )

        # 3. Create dissimilar photos
        dissimilar_photos = []
        for i in range(3):
            photo = PhotoFactory.create(filename=f"dissimilar_{i}.jpg")
            photo = await photo_repo.save(photo)
            dissimilar_photos.append(photo)

            # Create completely different embedding
            different_embedding = EmbeddingFactory.create_clip_embedding()
            await test_vector_store.store_photo_embedding(
                photo.id.value,
                different_embedding,
            )

        # 4. Search using base embedding
        results = await test_vector_store.search_photos(
            base_embedding,
            limit=10,
        )

        # 5. Verify similar photos rank higher
        result_ids = [str(r.id) for r in results[:4]]  # Top 4 results
        similar_ids = [str(p.id.value) for p in [base_photo] + similar_photos]

        # Base photo and similar photos should be in top results
        matches = sum(1 for sid in similar_ids if sid in result_ids)
        assert matches >= 3  # At least 3 of 4 similar photos in top 4

    @pytest.mark.asyncio
    async def test_search_with_filtering_by_connector(
        self,
        test_session,
        test_vector_store,
    ):
        """Test search with connector filtering."""
        photo_repo = PhotoRepositoryPostgres(test_session)
        connector_repo = ConnectorRepositoryPostgres(test_session)

        # 1. Create two connectors
        connector1 = ConnectorFactory.create_local_folder(name="Connector 1")
        connector2 = ConnectorFactory.create_local_folder(name="Connector 2")
        connector1 = await connector_repo.save(connector1)
        connector2 = await connector_repo.save(connector2)

        # 2. Create photos for each connector
        base_embedding = EmbeddingFactory.create_clip_embedding()

        photos_c1 = []
        for i in range(3):
            photo = PhotoFactory.create(
                filename=f"c1_photo_{i}.jpg",
                connector_id=connector1.id.value,
            )
            photo = await photo_repo.save(photo)
            photos_c1.append(photo)

            embedding = EmbeddingFactory.create_similar_embedding(base_embedding)
            await test_vector_store.store_photo_embedding(
                photo.id.value,
                embedding,
                payload={"connector_id": str(connector1.id.value)},
            )

        photos_c2 = []
        for i in range(3):
            photo = PhotoFactory.create(
                filename=f"c2_photo_{i}.jpg",
                connector_id=connector2.id.value,
            )
            photo = await photo_repo.save(photo)
            photos_c2.append(photo)

            embedding = EmbeddingFactory.create_similar_embedding(base_embedding)
            await test_vector_store.store_photo_embedding(
                photo.id.value,
                embedding,
                payload={"connector_id": str(connector2.id.value)},
            )

        # 3. Search with connector filter (using payload filter)
        from qdrant_client.http import models as qdrant_models

        # Search for connector 1 photos only
        results_c1 = await test_vector_store.search_photos(
            base_embedding,
            limit=10,
            filter=qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="connector_id",
                        match=qdrant_models.MatchValue(value=str(connector1.id.value)),
                    )
                ]
            ),
        )

        # 4. Verify only connector 1 photos are returned
        c1_photo_ids = {str(p.id.value) for p in photos_c1}
        result_ids = {str(r.id) for r in results_c1}

        assert len(result_ids.intersection(c1_photo_ids)) == len(results_c1)

    @pytest.mark.asyncio
    async def test_search_ranking_by_similarity(
        self,
        test_session,
        test_vector_store,
    ):
        """Test that search results are properly ranked by similarity score."""
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create query embedding
        query_embedding = EmbeddingFactory.create_clip_embedding()

        # 2. Create photos with varying similarity
        similarities = [0.99, 0.85, 0.70, 0.55, 0.40]
        photo_ids = []

        for i, target_similarity in enumerate(similarities):
            photo = PhotoFactory.create(filename=f"photo_sim_{i}.jpg")
            photo = await photo_repo.save(photo)
            photo_ids.append(photo.id.value)

            # Create embedding with specific similarity to query
            if i == 0:
                # Use query embedding for highest similarity
                embedding = query_embedding
            else:
                # Create progressively more different embeddings
                embedding = EmbeddingFactory.create_similar_embedding(
                    query_embedding,
                    noise=0.1 * i,
                )

            await test_vector_store.store_photo_embedding(
                photo.id.value,
                embedding,
            )

        # 3. Search
        results = await test_vector_store.search_photos(
            query_embedding,
            limit=5,
        )

        # 4. Verify results are ordered by score
        assert len(results) == 5
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

        # First result should have highest similarity
        assert results[0].score >= 0.99

    @pytest.mark.asyncio
    async def test_search_with_limit(
        self,
        test_session,
        test_vector_store,
    ):
        """Test search respects limit parameter."""
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create many photos
        base_embedding = EmbeddingFactory.create_clip_embedding()
        for i in range(20):
            photo = PhotoFactory.create(filename=f"photo_{i}.jpg")
            photo = await photo_repo.save(photo)

            embedding = EmbeddingFactory.create_similar_embedding(base_embedding)
            await test_vector_store.store_photo_embedding(
                photo.id.value,
                embedding,
            )

        # 2. Search with different limits
        results_5 = await test_vector_store.search_photos(base_embedding, limit=5)
        results_10 = await test_vector_store.search_photos(base_embedding, limit=10)
        results_15 = await test_vector_store.search_photos(base_embedding, limit=15)

        # 3. Verify limits are respected
        assert len(results_5) == 5
        assert len(results_10) == 10
        assert len(results_15) == 15

    @pytest.mark.asyncio
    async def test_face_similarity_search(
        self,
        test_session,
        test_vector_store,
    ):
        """Test face similarity search for face clustering."""
        from app.adapters.outbound.persistence.postgres.repositories import FaceRepositoryPostgres
        from tests.integration.factories import FaceFactory

        face_repo = FaceRepositoryPostgres(test_session)
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create photo
        photo = PhotoFactory.create()
        photo = await photo_repo.save(photo)

        # 2. Create base face
        base_face = FaceFactory.create(photo_id=photo.id.value)
        base_face = await face_repo.save(base_face)

        await test_vector_store.store_face_embedding(
            base_face.id.value,
            base_face.embedding,
        )

        # 3. Create similar faces (same person)
        similar_faces = []
        for i in range(3):
            face = FaceFactory.create(
                photo_id=photo.id.value,
                embedding=EmbeddingFactory.create_similar_embedding(
                    base_face.embedding,
                    noise=0.03,  # Very similar
                ),
            )
            face = await face_repo.save(face)
            similar_faces.append(face)

            await test_vector_store.store_face_embedding(
                face.id.value,
                face.embedding,
            )

        # 4. Create different faces (different people)
        different_faces = []
        for i in range(3):
            face = FaceFactory.create(
                photo_id=photo.id.value,
                embedding=EmbeddingFactory.create_face_embedding(),
            )
            face = await face_repo.save(face)
            different_faces.append(face)

            await test_vector_store.store_face_embedding(
                face.id.value,
                face.embedding,
            )

        # 5. Search for similar faces
        results = await test_vector_store.search_faces(
            base_face.embedding,
            limit=5,
        )

        # 6. Verify similar faces rank higher
        result_ids = [str(r.id) for r in results[:4]]
        similar_ids = [str(f.id.value) for f in [base_face] + similar_faces]

        matches = sum(1 for sid in similar_ids if sid in result_ids)
        assert matches >= 3  # At least 3 of 4 similar faces in top 4

    @pytest.mark.asyncio
    async def test_empty_search_results(
        self,
        test_vector_store,
    ):
        """Test search returns empty list when no photos indexed."""
        # Search in empty collection
        embedding = EmbeddingFactory.create_clip_embedding()
        results = await test_vector_store.search_photos(
            embedding,
            limit=10,
        )

        assert len(results) == 0
