"""
Simplified integration tests for Google Photos Picker flow.

Focuses on core functionality with proper API method names.
"""

import httpx
import pytest
import respx

from app.adapters.outbound.connectors.google_photos import GooglePhotosPickerClient


class TestPickerBasicFlow:
    """Test basic picker workflow."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_and_get_session(self):
        """Test creating and retrieving a session."""
        session_id = "test-session-123"

        # Mock session creation
        respx.post("https://photospicker.googleapis.com/v1/sessions").mock(
            return_value=httpx.Response(
                200,
                json={"id": session_id, "pickerUri": f"https://photos.google.com/picker/{session_id}"},
            )
        )

        # Mock session retrieval
        respx.get(f"https://photospicker.googleapis.com/v1/sessions/{session_id}").mock(
            return_value=httpx.Response(200, json={"id": session_id, "mediaItemsSet": True})
        )

        client = GooglePhotosPickerClient(
            client_id="test", client_secret="test", access_token="test"
        )

        # Create session
        session = await client.create_session()
        assert session.id == session_id

        # Get session status
        session_status = await client.get_session(session_id)
        assert session_status.media_items_set is True

        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_error_handling(self):
        """Test error handling with 401."""
        respx.post("https://photospicker.googleapis.com/v1/sessions").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )

        client = GooglePhotosPickerClient(
            client_id="test", client_secret="test", access_token="bad_token"
        )

        with pytest.raises(httpx.HTTPStatusError):
            await client.create_session()

        await client.close()
