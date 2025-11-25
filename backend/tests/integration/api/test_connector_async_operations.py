"""Integration tests for async connector operations (Sprint 2 Item 16).

Tests async endpoints to ensure they return correct HTTP status codes:
- POST /api/v1/connectors/{id}/reprocess - Should return 202 Accepted
- POST /api/v1/connectors/{id}/sync - Should return 202 Accepted

Following TDD approach:
1. RED: Write tests expecting 202 status codes
2. GREEN: Update endpoints to return 202
3. VERIFY: Ensure Celery tasks are queued
"""

import pytest
from uuid import uuid4

from httpx import AsyncClient

from app.domain.entities.connector import Connector, ConnectorStatus


class TestAsyncEndpointStatusCodes:
    """Tests for async endpoint HTTP status codes."""

    @pytest.mark.asyncio
    async def test_reprocess_returns_202_accepted(
        self, client: AsyncClient, connector_repo
    ):
        """Reprocess endpoint should return 202 Accepted (async operation)."""
        # Given: connector with photos
        connector = Connector.create_upload(upload_path="/uploads")
        saved = await connector_repo.save(connector)

        # When: trigger reprocess
        response = await client.post(f"/api/v1/connectors/{saved.id.value}/reprocess")

        # Then: should return 202 Accepted
        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_sync_returns_202_accepted(
        self, client: AsyncClient, connector_repo
    ):
        """Sync endpoint should return 202 Accepted (async operation)."""
        # Given: local connector
        connector = Connector.create_local(path="/photos", name="Test")
        saved = await connector_repo.save(connector)

        # When: trigger sync
        response = await client.post(f"/api/v1/connectors/{saved.id.value}/sync")

        # Then: should return 202 Accepted
        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_reprocess_response_includes_task_info(
        self, client: AsyncClient, connector_repo
    ):
        """Reprocess response should include task information."""
        # Given: connector
        connector = Connector.create_local(path="/photos", name="Test")
        saved = await connector_repo.save(connector)

        # When: trigger reprocess
        response = await client.post(f"/api/v1/connectors/{saved.id.value}/reprocess")

        # Then: should include task info
        assert response.status_code == 202
        data = response.json()

        # Response should include status, message, and task_id
        assert "status" in data
        assert data["status"] == "accepted"
        assert "message" in data
        assert "task_id" in data
        assert data["task_id"] is not None

    @pytest.mark.asyncio
    async def test_sync_response_includes_task_id(
        self, client: AsyncClient, connector_repo
    ):
        """Sync response should include task ID."""
        # Given: Google Photos connector
        connector = Connector.create_google_photos(name="Google Photos")
        connector.status = ConnectorStatus.CONNECTED
        saved = await connector_repo.save(connector)

        # When: trigger sync
        response = await client.post(f"/api/v1/connectors/{saved.id.value}/sync")

        # Then: should include task_id
        assert response.status_code == 202
        data = response.json()

        assert "status" in data
        assert data["status"] == "accepted"
        assert "message" in data
        assert "task_id" in data
        assert data["task_id"] is not None

    @pytest.mark.asyncio
    async def test_sync_rejects_upload_connector_with_400(
        self, client: AsyncClient, connector_repo
    ):
        """Sync should reject upload connector with 400 Bad Request."""
        # Given: upload connector (cannot be synced)
        connector = Connector.create_upload(upload_path="/uploads")
        saved = await connector_repo.save(connector)

        # When: try to sync upload connector
        response = await client.post(f"/api/v1/connectors/{saved.id.value}/sync")

        # Then: should return 400 Bad Request
        assert response.status_code == 400
        data = response.json()

        # Should include error message about upload connector
        assert "error" in data
        assert "upload" in data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_reprocess_queues_celery_task(
        self, client: AsyncClient, connector_repo
    ):
        """Reprocess should queue a Celery task."""
        # Given: connector
        connector = Connector.create_upload(upload_path="/uploads")
        saved = await connector_repo.save(connector)

        # When: trigger reprocess
        response = await client.post(f"/api/v1/connectors/{saved.id.value}/reprocess")

        # Then: should queue task and return task ID
        assert response.status_code == 202
        data = response.json()

        # Task ID should be a valid UUID-like string or Celery task ID
        task_id = data.get("task_id")
        assert task_id is not None
        assert isinstance(task_id, str)
        assert len(task_id) > 0

    @pytest.mark.asyncio
    async def test_sync_queues_celery_task(
        self, client: AsyncClient, connector_repo
    ):
        """Sync should queue appropriate Celery task based on connector type."""
        # Given: local connector
        connector = Connector.create_local(path="/photos", name="Local")
        saved = await connector_repo.save(connector)

        # When: trigger sync
        response = await client.post(f"/api/v1/connectors/{saved.id.value}/sync")

        # Then: should queue task and return task ID
        assert response.status_code == 202
        data = response.json()

        # Task ID should be present and valid
        task_id = data.get("task_id")
        assert task_id is not None
        assert isinstance(task_id, str)
        assert len(task_id) > 0


# Fixtures


@pytest.fixture
async def connector_repo(db_session):
    """Provide ConnectorRepository instance."""
    from app.adapters.outbound.persistence.postgres.repositories.connector_repository import (
        ConnectorRepositoryPostgres,
    )

    return ConnectorRepositoryPostgres(db_session)
