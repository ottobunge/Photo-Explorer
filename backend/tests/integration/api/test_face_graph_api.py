"""Integration tests for Face Social Graph API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbound.persistence.postgres.repositories.face_repository import (
    FaceRepositoryPostgres,
)
from app.adapters.outbound.persistence.postgres.repositories.photo_repository import (
    PhotoRepositoryPostgres,
)
from tests.integration.factories import FaceClusterFactory, FaceFactory, PhotoFactory


@pytest.fixture
async def face_repo(test_session: AsyncSession):
    """Provide FaceRepository instance with test database session."""
    return FaceRepositoryPostgres(test_session)


@pytest.fixture
async def photo_repo(test_session: AsyncSession):
    """Provide PhotoRepository instance with test database session."""
    return PhotoRepositoryPostgres(test_session)


class TestSocialGraphAPI:
    """Tests for GET /api/v1/faces/graph endpoint."""

    @pytest.mark.asyncio
    async def test_get_empty_graph(
        self, client: AsyncClient, test_session: AsyncSession
    ) -> None:
        """Test getting graph when no faces exist."""
        response = await client.get("/api/v1/faces/graph")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["nodes"] == []
        assert data["data"]["edges"] == []
        assert data["data"]["node_count"] == 0
        assert data["data"]["edge_count"] == 0
        assert data["data"]["is_empty"] is True
        assert data["data"]["has_connections"] is False

    @pytest.mark.asyncio
    async def test_get_graph_with_isolated_people(
        self, client: AsyncClient, face_repo, photo_repo
    ) -> None:
        """Test graph with people who have no relationships."""
        # Create 3 people, each in their own photo
        cluster1 = FaceClusterFactory.create(name="Alice")
        cluster2 = FaceClusterFactory.create(name="Bob")
        cluster3 = FaceClusterFactory.create(name="Charlie")

        saved_cluster1 = await face_repo.save_cluster(cluster1)
        saved_cluster2 = await face_repo.save_cluster(cluster2)
        saved_cluster3 = await face_repo.save_cluster(cluster3)

        photo1 = PhotoFactory.create()
        photo2 = PhotoFactory.create()
        photo3 = PhotoFactory.create()

        saved_photo1 = await photo_repo.save(photo1)
        saved_photo2 = await photo_repo.save(photo2)
        saved_photo3 = await photo_repo.save(photo3)

        face1 = FaceFactory.create(
            cluster_id=saved_cluster1.id.value, photo_id=saved_photo1.id.value
        )
        face2 = FaceFactory.create(
            cluster_id=saved_cluster2.id.value, photo_id=saved_photo2.id.value
        )
        face3 = FaceFactory.create(
            cluster_id=saved_cluster3.id.value, photo_id=saved_photo3.id.value
        )

        await face_repo.save_face(face1)
        await face_repo.save_face(face2)
        await face_repo.save_face(face3)

        response = await client.get("/api/v1/faces/graph")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["nodes"]) == 3
        assert len(data["data"]["edges"]) == 0
        assert data["data"]["node_count"] == 3
        assert data["data"]["edge_count"] == 0
        assert data["data"]["is_empty"] is False
        assert data["data"]["has_connections"] is False

        # Verify node data
        nodes = data["data"]["nodes"]
        names = {node["name"] for node in nodes}
        assert names == {"Alice", "Bob", "Charlie"}

    @pytest.mark.asyncio
    async def test_get_graph_with_relationships(
        self, client: AsyncClient, face_repo, photo_repo
    ) -> None:
        """Test graph with people who appear together in photos."""
        # Create 3 people
        cluster_alice = FaceClusterFactory.create(name="Alice")
        cluster_bob = FaceClusterFactory.create(name="Bob")
        cluster_charlie = FaceClusterFactory.create(name="Charlie")

        cluster_alice = await face_repo.save_cluster(cluster_alice)
        cluster_bob = await face_repo.save_cluster(cluster_bob)
        cluster_charlie = await face_repo.save_cluster(cluster_charlie)

        # Create photos with co-appearances
        # Photo 1: Alice and Bob
        photo1 = PhotoFactory.create()
        saved_photo1 = await photo_repo.save(photo1)
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_alice.id.value, photo_id=saved_photo1.id.value
            )
        )
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_bob.id.value, photo_id=saved_photo1.id.value
            )
        )

        # Photo 2: Alice and Bob (again)
        photo2 = PhotoFactory.create()
        saved_photo2 = await photo_repo.save(photo2)
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_alice.id.value, photo_id=saved_photo2.id.value
            )
        )
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_bob.id.value, photo_id=saved_photo2.id.value
            )
        )

        # Photo 3: Alice and Charlie
        photo3 = PhotoFactory.create()
        saved_photo3 = await photo_repo.save(photo3)
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_alice.id.value, photo_id=saved_photo3.id.value
            )
        )
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_charlie.id.value, photo_id=saved_photo3.id.value
            )
        )

        # Photo 4: Bob alone
        photo4 = PhotoFactory.create()
        saved_photo4 = await photo_repo.save(photo4)
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_bob.id.value, photo_id=saved_photo4.id.value
            )
        )

        response = await client.get("/api/v1/faces/graph")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Should have 3 nodes
        assert len(data["data"]["nodes"]) == 3
        assert data["data"]["node_count"] == 3

        # Should have 2 edges: Alice-Bob and Alice-Charlie
        assert len(data["data"]["edges"]) == 2
        assert data["data"]["edge_count"] == 2
        assert data["data"]["has_connections"] is True

        # Verify edge data
        edges = data["data"]["edges"]
        # Find Alice-Bob edge
        alice_bob_edge = next(
            (
                e
                for e in edges
                if (
                    (
                        e["person_a_id"] == str(cluster_alice.id.value)
                        and e["person_b_id"] == str(cluster_bob.id.value)
                    )
                    or (
                        e["person_a_id"] == str(cluster_bob.id.value)
                        and e["person_b_id"] == str(cluster_alice.id.value)
                    )
                )
            ),
            None,
        )
        assert alice_bob_edge is not None
        assert alice_bob_edge["shared_photo_count"] == 2

        # Find Alice-Charlie edge
        alice_charlie_edge = next(
            (
                e
                for e in edges
                if (
                    (
                        e["person_a_id"] == str(cluster_alice.id.value)
                        and e["person_b_id"] == str(cluster_charlie.id.value)
                    )
                    or (
                        e["person_a_id"] == str(cluster_charlie.id.value)
                        and e["person_b_id"] == str(cluster_alice.id.value)
                    )
                )
            ),
            None,
        )
        assert alice_charlie_edge is not None
        assert alice_charlie_edge["shared_photo_count"] == 1

    @pytest.mark.asyncio
    async def test_filter_graph_by_person(
        self, client: AsyncClient, face_repo, photo_repo
    ) -> None:
        """Test filtering graph to show only one person's network."""
        # Create 4 people with specific relationships
        cluster_alice = FaceClusterFactory.create(name="Alice")
        cluster_bob = FaceClusterFactory.create(name="Bob")
        cluster_charlie = FaceClusterFactory.create(name="Charlie")
        cluster_david = FaceClusterFactory.create(name="David")

        cluster_alice = await face_repo.save_cluster(cluster_alice)
        cluster_bob = await face_repo.save_cluster(cluster_bob)
        cluster_charlie = await face_repo.save_cluster(cluster_charlie)
        cluster_david = await face_repo.save_cluster(cluster_david)

        # Alice appears with Bob and Charlie
        photo1 = PhotoFactory.create()
        saved_photo1 = await photo_repo.save(photo1)
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_alice.id.value, photo_id=saved_photo1.id.value
            )
        )
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_bob.id.value, photo_id=saved_photo1.id.value
            )
        )

        photo2 = PhotoFactory.create()
        saved_photo2 = await photo_repo.save(photo2)
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_alice.id.value, photo_id=saved_photo2.id.value
            )
        )
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_charlie.id.value, photo_id=saved_photo2.id.value
            )
        )

        # David appears with Bob (not Alice)
        photo3 = PhotoFactory.create()
        saved_photo3 = await photo_repo.save(photo3)
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_david.id.value, photo_id=saved_photo3.id.value
            )
        )
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_bob.id.value, photo_id=saved_photo3.id.value
            )
        )

        # Filter by Alice
        response = await client.get(f"/api/v1/faces/graph?person_id={cluster_alice.id.value}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Should only show Alice, Bob, and Charlie (not David)
        assert len(data["data"]["nodes"]) == 3
        node_names = {node["name"] for node in data["data"]["nodes"]}
        assert node_names == {"Alice", "Bob", "Charlie"}

        # Should show 2 edges: Alice-Bob and Alice-Charlie
        assert len(data["data"]["edges"]) == 2

    @pytest.mark.asyncio
    async def test_filter_by_nonexistent_person(
        self, client: AsyncClient, test_session: AsyncSession
    ) -> None:
        """Test filtering by a person that doesn't exist."""
        fake_uuid = "00000000-0000-0000-0000-000000000001"
        response = await client.get(f"/api/v1/faces/graph?person_id={fake_uuid}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Should return empty graph
        assert data["data"]["nodes"] == []
        assert data["data"]["edges"] == []


class TestRelationshipPhotosAPI:
    """Tests for GET /api/v1/faces/relationships/{person_a_id}/{person_b_id}/photos endpoint."""

    @pytest.mark.asyncio
    async def test_get_relationship_photos(
        self, client: AsyncClient, face_repo, photo_repo
    ) -> None:
        """Test getting photos where two people appear together."""
        cluster_alice = FaceClusterFactory.create(name="Alice")
        cluster_bob = FaceClusterFactory.create(name="Bob")

        cluster_alice = await face_repo.save_cluster(cluster_alice)
        cluster_bob = await face_repo.save_cluster(cluster_bob)

        # Create 3 photos with both Alice and Bob
        photos_together = []
        for i in range(3):
            photo = PhotoFactory.create()
            saved_photo = await photo_repo.save(photo)
            await face_repo.save_face(
                FaceFactory.create(
                    cluster_id=cluster_alice.id.value, photo_id=saved_photo.id.value
                )
            )
            await face_repo.save_face(
                FaceFactory.create(
                    cluster_id=cluster_bob.id.value, photo_id=saved_photo.id.value
                )
            )
            photos_together.append(saved_photo)

        # Create a photo with only Alice (should not be included)
        photo_alice_only = PhotoFactory.create()
        saved_photo_alice_only = await photo_repo.save(photo_alice_only)
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_alice.id.value, photo_id=saved_photo_alice_only.id.value
            )
        )

        # Create a photo with only Bob (should not be included)
        photo_bob_only = PhotoFactory.create()
        saved_photo_bob_only = await photo_repo.save(photo_bob_only)
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_bob.id.value, photo_id=saved_photo_bob_only.id.value
            )
        )

        response = await client.get(
            f"/api/v1/faces/relationships/{cluster_alice.id.value}/{cluster_bob.id.value}/photos"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify person data
        assert data["data"]["person_a"]["name"] == "Alice"
        assert data["data"]["person_b"]["name"] == "Bob"

        # Verify shared photos
        assert data["data"]["shared_photo_count"] == 3
        assert len(data["data"]["shared_photos"]) == 3

        # Verify photo IDs match
        returned_photo_ids = {photo["id"] for photo in data["data"]["shared_photos"]}
        expected_photo_ids = {str(photo.id.value) for photo in photos_together}
        assert returned_photo_ids == expected_photo_ids

    @pytest.mark.asyncio
    async def test_get_relationship_photos_order_independent(
        self, client: AsyncClient, face_repo, photo_repo
    ) -> None:
        """Test that person_a and person_b order doesn't matter."""
        cluster_alice = FaceClusterFactory.create(name="Alice")
        cluster_bob = FaceClusterFactory.create(name="Bob")

        cluster_alice = await face_repo.save_cluster(cluster_alice)
        cluster_bob = await face_repo.save_cluster(cluster_bob)

        photo = PhotoFactory.create()
        saved_photo = await photo_repo.save(photo)
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_alice.id.value, photo_id=saved_photo.id.value
            )
        )
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_bob.id.value, photo_id=saved_photo.id.value
            )
        )

        # Try both orders
        response1 = await client.get(
            f"/api/v1/faces/relationships/{cluster_alice.id.value}/{cluster_bob.id.value}/photos"
        )
        response2 = await client.get(
            f"/api/v1/faces/relationships/{cluster_bob.id.value}/{cluster_alice.id.value}/photos"
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()["data"]
        data2 = response2.json()["data"]

        # Both should return the same photo count
        assert data1["shared_photo_count"] == data2["shared_photo_count"] == 1

    @pytest.mark.asyncio
    async def test_no_shared_photos(
        self, client: AsyncClient, face_repo, photo_repo
    ) -> None:
        """Test when two people have no photos together."""
        cluster_alice = FaceClusterFactory.create(name="Alice")
        cluster_bob = FaceClusterFactory.create(name="Bob")

        cluster_alice = await face_repo.save_cluster(cluster_alice)
        cluster_bob = await face_repo.save_cluster(cluster_bob)

        # Create photos with only one person each
        photo1 = PhotoFactory.create()
        saved_photo1 = await photo_repo.save(photo1)
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_alice.id.value, photo_id=saved_photo1.id.value
            )
        )

        photo2 = PhotoFactory.create()
        saved_photo2 = await photo_repo.save(photo2)
        await face_repo.save_face(
            FaceFactory.create(
                cluster_id=cluster_bob.id.value, photo_id=saved_photo2.id.value
            )
        )

        response = await client.get(
            f"/api/v1/faces/relationships/{cluster_alice.id.value}/{cluster_bob.id.value}/photos"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["shared_photo_count"] == 0
        assert data["data"]["shared_photos"] == []

    @pytest.mark.asyncio
    async def test_nonexistent_person(
        self, client: AsyncClient, face_repo
    ) -> None:
        """Test when one or both people don't exist."""
        cluster_alice = FaceClusterFactory.create(name="Alice")
        cluster_alice = await face_repo.save_cluster(cluster_alice)

        fake_uuid = "00000000-0000-0000-0000-000000000001"

        # Test with one nonexistent person
        response = await client.get(
            f"/api/v1/faces/relationships/{cluster_alice.id.value}/{fake_uuid}/photos"
        )
        assert response.status_code == 404

        # Test with both nonexistent
        response = await client.get(
            f"/api/v1/faces/relationships/{fake_uuid}/{fake_uuid}/photos"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_same_person_relationship(
        self, client: AsyncClient, face_repo
    ) -> None:
        """Test requesting relationship between same person (should fail)."""
        cluster_alice = FaceClusterFactory.create(name="Alice")
        cluster_alice = await face_repo.save_cluster(cluster_alice)

        response = await client.get(
            f"/api/v1/faces/relationships/{cluster_alice.id.value}/{cluster_alice.id.value}/photos"
        )

        # Should return 400 Bad Request
        assert response.status_code == 400
