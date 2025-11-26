"""
Integration tests for Google Photos Picker flow.

Tests the full workflow:
1. Create session
2. Poll for status
3. Import photos when mediaItemsSet=true
4. Handle session expiration
5. Test error recovery (network failures, invalid sessions)

Uses httpx mock for simulating Google Photos Picker API responses.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import httpx
import pytest
import respx

from app.adapters.outbound.connectors.google_photos import (
    GooglePhotosPickerClient,
    PickerMediaItem,
    PickerSession,
)


class TestPickerFlowEndToEnd:
    """Test complete picker workflow end-to-end."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_session_success(self):
        """Test creating a new picker session successfully."""
        # Mock the Picker API session creation endpoint
        session_id = "test-session-123"
        picker_uri = f"https://photos.google.com/picker/{session_id}"
        expire_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()

        respx.post("https://photospicker.googleapis.com/v1/sessions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": session_id,
                    "pickerUri": picker_uri,
                    "pollInterval": "5s",
                    "expireTime": expire_time,
                },
            )
        )

        # Create client and session
        client = GooglePhotosPickerClient(
            client_id="test_client_id",
            client_secret="test_secret",
            access_token="test_access_token",
        )

        session = await client.create_session()

        # Verify session created
        assert session is not None
        assert session.id == session_id
        assert session.picker_uri == picker_uri
        assert session.media_items_set is False
        assert session.poll_interval_seconds == 5

        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_session_before_selection(self):
        """Test polling session before user selects photos."""
        session_id = "test-session-123"

        # Mock poll endpoint - no media items selected yet
        respx.get(f"https://photospicker.googleapis.com/v1/sessions/{session_id}").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": session_id,
                    "mediaItemsSet": False,
                },
            )
        )

        client = GooglePhotosPickerClient(
            client_id="test_client_id",
            client_secret="test_secret",
            access_token="test_access_token",
        )

        # Poll session
        session = await client.get_session(session_id)

        assert media_items_set is False

        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_session_after_selection(self):
        """Test polling session after user selects photos."""
        session_id = "test-session-123"

        # Mock poll endpoint - media items selected
        respx.get(f"https://photospicker.googleapis.com/v1/sessions/{session_id}").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": session_id,
                    "mediaItemsSet": True,
                },
            )
        )

        client = GooglePhotosPickerClient(
            client_id="test_client_id",
            client_secret="test_secret",
            access_token="test_access_token",
        )

        session = await client.get_session(session_id)

        assert media_items_set is True

        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_iter_all_media_items(self):
        """Test fetching selected media items from session."""
        session_id = "test-session-123"

        # Mock media items endpoint
        respx.get(f"https://photospicker.googleapis.com/v1/sessions/{session_id}/mediaItems").mock(
            return_value=httpx.Response(
                200,
                json={
                    "mediaItems": [
                        {
                            "id": "photo-1",
                            "baseUrl": "https://example.com/photo1.jpg",
                            "mimeType": "image/jpeg",
                            "filename": "IMG_001.jpg",
                            "mediaMetadata": {
                                "width": "1920",
                                "height": "1080",
                                "creationTime": "2024-01-15T10:30:00Z",
                                "cameraMake": "Canon",
                                "cameraModel": "EOS R5",
                            },
                        },
                        {
                            "id": "photo-2",
                            "baseUrl": "https://example.com/photo2.jpg",
                            "mimeType": "image/jpeg",
                            "filename": "IMG_002.jpg",
                            "mediaMetadata": {
                                "width": "3840",
                                "height": "2160",
                                "creationTime": "2024-01-15T11:00:00Z",
                            },
                        },
                    ]
                },
            )
        )

        client = GooglePhotosPickerClient(
            client_id="test_client_id",
            client_secret="test_secret",
            access_token="test_access_token",
        )

        media_items = []
        async for item in client.iter_all_media_items(session_id):
            media_items.append(item)

        # Verify media items
        assert len(media_items) == 2
        assert media_items[0].id == "photo-1"
        assert media_items[0].filename == "IMG_001.jpg"
        assert media_items[0].width == 1920
        assert media_items[0].height == 1080
        assert media_items[0].camera_make == "Canon"
        assert media_items[0].camera_model == "EOS R5"

        assert media_items[1].id == "photo-2"
        assert media_items[1].width == 3840
        assert media_items[1].height == 2160

        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_complete_picker_workflow(self):
        """
        Test the complete picker workflow end-to-end.

        1. Create session
        2. Poll until mediaItemsSet=true
        3. Fetch selected media items
        """
        session_id = "test-session-complete"
        picker_uri = f"https://photos.google.com/picker/{session_id}"

        # Mock session creation
        respx.post("https://photospicker.googleapis.com/v1/sessions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": session_id,
                    "pickerUri": picker_uri,
                    "pollInterval": "1s",  # Short interval for testing
                },
            )
        )

        # Mock polling - first call returns false, second returns true
        poll_responses = [
            httpx.Response(200, json={"id": session_id, "mediaItemsSet": False}),
            httpx.Response(200, json={"id": session_id, "mediaItemsSet": True}),
        ]
        respx.get(f"https://photospicker.googleapis.com/v1/sessions/{session_id}").mock(
            side_effect=poll_responses
        )

        # Mock media items
        respx.get(f"https://photospicker.googleapis.com/v1/sessions/{session_id}/mediaItems").mock(
            return_value=httpx.Response(
                200,
                json={
                    "mediaItems": [
                        {
                            "id": "photo-complete-1",
                            "baseUrl": "https://example.com/photo.jpg",
                            "mimeType": "image/jpeg",
                            "filename": "vacation.jpg",
                        }
                    ]
                },
            )
        )

        client = GooglePhotosPickerClient(
            client_id="test_client_id",
            client_secret="test_secret",
            access_token="test_access_token",
        )

        # Step 1: Create session
        session = await client.create_session()
        assert session.id == session_id

        # Step 2: Poll until media items set
        # First poll returns false
        media_set = await client.get_session(session_id)
        assert session.media_items_set is False

        # Second poll returns true
        media_set = await client.get_session(session_id)
        assert session.media_items_set is True

        # Step 3: Fetch media items
        media_items = []
        async for item in client.iter_all_media_items(session_id):
            media_items.append(item)

        assert len(media_items) == 1
        assert media_items[0].id == "photo-complete-1"
        assert media_items[0].filename == "vacation.jpg"

        await client.close()


class TestPickerErrorHandling:
    """Test error handling in picker flow."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_session_creation_network_error(self):
        """Test handling network errors during session creation."""
        # Mock network error
        respx.post("https://photospicker.googleapis.com/v1/sessions").mock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        client = GooglePhotosPickerClient(
            client_id="test_client_id",
            client_secret="test_secret",
            access_token="test_access_token",
        )

        # Should raise exception
        with pytest.raises(httpx.ConnectError):
            await client.create_session()

        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_session_creation_unauthorized(self):
        """Test handling unauthorized errors (invalid token)."""
        # Mock 401 Unauthorized
        respx.post("https://photospicker.googleapis.com/v1/sessions").mock(
            return_value=httpx.Response(
                401,
                json={"error": {"code": 401, "message": "Invalid token"}},
            )
        )

        client = GooglePhotosPickerClient(
            client_id="test_client_id",
            client_secret="test_secret",
            access_token="invalid_token",
        )

        with pytest.raises(httpx.HTTPStatusError):
            await client.create_session()

        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_poll_invalid_session(self):
        """Test polling an invalid/expired session."""
        session_id = "invalid-session-id"

        # Mock 404 Not Found
        respx.get(f"https://photospicker.googleapis.com/v1/sessions/{session_id}").mock(
            return_value=httpx.Response(
                404,
                json={"error": {"code": 404, "message": "Session not found"}},
            )
        )

        client = GooglePhotosPickerClient(
            client_id="test_client_id",
            client_secret="test_secret",
            access_token="test_access_token",
        )

        with pytest.raises(httpx.HTTPStatusError):
            await client.get_session(session_id)

        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_session_expiration_handling(self):
        """Test handling expired sessions."""
        session_id = "expired-session"

        # Mock expired session
        respx.get(f"https://photospicker.googleapis.com/v1/sessions/{session_id}").mock(
            return_value=httpx.Response(
                410,  # Gone - session expired
                json={"error": {"code": 410, "message": "Session expired"}},
            )
        )

        client = GooglePhotosPickerClient(
            client_id="test_client_id",
            client_secret="test_secret",
            access_token="test_access_token",
        )

        # Should handle 410 Gone appropriately
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await client.get_session(session_id)

        assert exc_info.value.response.status_code == 410

        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_network_retry_on_timeout(self):
        """Test retry behavior on network timeouts."""
        session_id = "timeout-test"

        # First request times out, second succeeds
        responses = [
            httpx.TimeoutException("Request timed out"),
            httpx.Response(200, json={"id": session_id, "mediaItemsSet": True}),
        ]

        respx.get(f"https://photospicker.googleapis.com/v1/sessions/{session_id}").mock(
            side_effect=responses
        )

        client = GooglePhotosPickerClient(
            client_id="test_client_id",
            client_secret="test_secret",
            access_token="test_access_token",
        )

        # First attempt should fail
        with pytest.raises(httpx.TimeoutException):
            await client.get_session(session_id)

        # Second attempt should succeed (retry)
        media_set = await client.get_session(session_id)
        assert session.media_items_set is True

        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_media_items_pagination(self):
        """Test handling paginated media items responses."""
        session_id = "pagination-test"

        # Mock paginated responses
        respx.get(f"https://photospicker.googleapis.com/v1/sessions/{session_id}/mediaItems").mock(
            return_value=httpx.Response(
                200,
                json={
                    "mediaItems": [
                        {
                            "id": "photo-1",
                            "baseUrl": "https://example.com/photo1.jpg",
                            "mimeType": "image/jpeg",
                        }
                    ],
                    "nextPageToken": "page2-token",
                },
            )
        )

        respx.get(
            f"https://photospicker.googleapis.com/v1/sessions/{session_id}/mediaItems",
            params={"pageToken": "page2-token"},
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "mediaItems": [
                        {
                            "id": "photo-2",
                            "baseUrl": "https://example.com/photo2.jpg",
                            "mimeType": "image/jpeg",
                        }
                    ]
                },
            )
        )

        client = GooglePhotosPickerClient(
            client_id="test_client_id",
            client_secret="test_secret",
            access_token="test_access_token",
        )

        # Fetch all media items
        media_items = []
        async for item in client.iter_all_media_items(session_id):
            media_items.append(item)

        # Should get items from both pages
        assert len(media_items) == 2
        assert media_items[0].id == "photo-1"
        assert media_items[1].id == "photo-2"

        await client.close()


class TestPickerPollingStrategy:
    """Test polling strategy and timing."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_polling_with_exponential_backoff(self):
        """
        Test that polling can implement exponential backoff.

        This is a behavioral test for how clients should poll the API.
        """
        session_id = "backoff-test"

        # Mock multiple poll responses
        poll_count = 0

        def poll_response(request):
            nonlocal poll_count
            poll_count += 1
            # Return false for first 3 polls, then true
            media_set = poll_count > 3
            return httpx.Response(200, json={"id": session_id, "mediaItemsSet": media_set})

        respx.get(f"https://photospicker.googleapis.com/v1/sessions/{session_id}").mock(
            side_effect=poll_response
        )

        client = GooglePhotosPickerClient(
            client_id="test_client_id",
            client_secret="test_secret",
            access_token="test_access_token",
        )

        # Simulate polling with backoff
        max_polls = 5
        poll_intervals = [1, 2, 4, 8]  # Exponential backoff in seconds (for testing, use ms)
        media_set = False

        for i in range(max_polls):
            media_set = await client.get_session(session_id)
            if session.media_items_set:
                break
            # In real implementation, wait for backoff interval
            # await asyncio.sleep(poll_intervals[min(i, len(poll_intervals) - 1)])

        assert session.media_items_set is True
        assert poll_count == 4  # Should have polled 4 times before getting true

        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_max_polling_attempts(self):
        """Test that polling respects max attempts to avoid infinite loops."""
        session_id = "max-attempts-test"

        # Always return false (user never selects)
        respx.get(f"https://photospicker.googleapis.com/v1/sessions/{session_id}").mock(
            return_value=httpx.Response(200, json={"id": session_id, "mediaItemsSet": False})
        )

        client = GooglePhotosPickerClient(
            client_id="test_client_id",
            client_secret="test_secret",
            access_token="test_access_token",
        )

        # Poll with max attempts
        max_attempts = 3
        attempts = 0
        media_set = False

        for _ in range(max_attempts):
            attempts += 1
            media_set = await client.get_session(session_id)
            if session.media_items_set:
                break

        assert attempts == max_attempts
        assert session.media_items_set is False

        await client.close()
