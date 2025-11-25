"""Integration tests for Photo API endpoints."""



class TestPhotoUploadAPI:
    """Tests for photo upload endpoint behavior."""

    async def test_upload_returns_201_for_valid_image(self, client, sample_image_bytes):
        """When uploading valid image, response should be 201 with photo data."""
        response = await client.post(
            "/api/v1/photos/upload",
            files={"files": ("beach.jpg", sample_image_bytes, "image/jpeg")},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["uploaded"]) == 1
        assert data["data"]["uploaded"][0]["filename"] == "beach.jpg"
        assert data["data"]["uploaded"][0]["status"] == "processing"

    async def test_upload_rejects_non_image_file(self, client):
        """When uploading non-image file, it should be in failed list."""
        response = await client.post(
            "/api/v1/photos/upload",
            files={"files": ("document.pdf", b"fake pdf content", "application/pdf")},
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["data"]["failed"]) == 1
        assert "Invalid file type" in data["data"]["failed"][0]["error"]

    async def test_upload_multiple_files(self, client, sample_image_bytes):
        """When uploading multiple images, all should be processed."""
        response = await client.post(
            "/api/v1/photos/upload",
            files=[
                ("files", ("photo1.jpg", sample_image_bytes, "image/jpeg")),
                ("files", ("photo2.jpg", sample_image_bytes, "image/jpeg")),
            ],
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["data"]["uploaded"]) == 2


class TestPhotoListAPI:
    """Tests for photo list endpoint behavior."""

    async def test_list_photos_returns_empty_initially(self, client):
        """When no photos exist, list should return empty array."""
        response = await client.get("/api/v1/photos")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["photos"] == []
        assert data["meta"]["total"] == 0

    async def test_list_photos_respects_pagination(self, client):
        """When pagination params provided, they should be in response meta."""
        response = await client.get("/api/v1/photos?page=2&per_page=10")

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["page"] == 2
        assert data["meta"]["per_page"] == 10


class TestPhotoDetailAPI:
    """Tests for photo detail endpoint behavior."""

    async def test_get_nonexistent_photo_returns_404(self, client):
        """When photo doesn't exist, response should be 404."""
        response = await client.get("/api/v1/photos/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    async def test_health_returns_healthy(self, client):
        """Health endpoint should return healthy status."""
        response = await client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
