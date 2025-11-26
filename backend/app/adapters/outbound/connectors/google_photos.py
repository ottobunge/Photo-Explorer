"""Google Photos connector adapter."""

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import httpx

from app.application.ports.outbound import OAuthTokens, PhotoSource, RemotePhotoMetadata

logger = logging.getLogger(__name__)


@dataclass
class PickerSession:
    """Represents a Google Photos Picker session."""

    id: str
    picker_uri: str
    media_items_set: bool = False
    poll_interval_seconds: int = 5
    expire_time: Optional[datetime] = None


@dataclass
class PickerMediaItem:
    """Media item from the Picker API."""

    id: str
    base_url: str
    mime_type: str
    filename: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    creation_time: Optional[datetime] = None


class GooglePhotosPickerClient:
    """
    Google Photos Picker API client.

    Uses the Picker API which is available for new projects (unlike the Library API).
    Users select photos manually through the Google Photos app.
    """

    PICKER_BASE_URL = "https://photospicker.googleapis.com/v1"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

    # Picker API scope - available for new projects
    SCOPES = [
        "https://www.googleapis.com/auth/photospicker.mediaitems.readonly",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._token_expires_at: Optional[datetime] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    def set_tokens(self, access_token: str, refresh_token: Optional[str] = None) -> None:
        """Set the access and refresh tokens."""
        self._access_token = access_token
        if refresh_token:
            self._refresh_token = refresh_token

    async def get_user_info(self) -> Optional[dict]:
        """Get the authenticated user's info from Google."""
        if not self._access_token:
            return None

        client = await self._get_client()
        try:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

    def get_auth_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """Generate the OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "access_type": "offline",
            "prompt": "consent",
        }
        if state:
            params["state"] = state

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.AUTH_URL}?{query}"

    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        """Exchange authorization code for tokens."""
        client = await self._get_client()

        response = await client.post(
            self.TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        data = response.json()

        expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])

        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token", self._refresh_token)
        self._token_expires_at = expires_at

        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            token_type=data["token_type"],
            expires_at=expires_at,
            scopes=data.get("scope", "").split(),
        )

    async def refresh_tokens(self) -> OAuthTokens:
        """Refresh the access token using the refresh token."""
        if not self._refresh_token:
            raise ValueError("No refresh token available")

        client = await self._get_client()

        response = await client.post(
            self.TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        data = response.json()

        expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])

        self._access_token = data["access_token"]
        self._token_expires_at = expires_at

        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=self._refresh_token,
            token_type=data["token_type"],
            expires_at=expires_at,
            scopes=data.get("scope", "").split(),
        )

    async def _ensure_valid_token(self) -> str:
        """Ensure we have a valid access token."""
        if not self._access_token:
            raise ValueError("Not authenticated")

        if self._token_expires_at and datetime.utcnow() >= self._token_expires_at:
            await self.refresh_tokens()

        return self._access_token

    async def _make_picker_request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict:
        """Make an authenticated request to the Google Photos Picker API."""
        token = await self._ensure_valid_token()
        client = await self._get_client()

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        url = f"{self.PICKER_BASE_URL}/{endpoint}"
        response = await client.request(method, url, headers=headers, **kwargs)

        if not response.is_success:
            logger.error(
                f"Google Photos Picker API error: {response.status_code} {response.reason_phrase}\n"
                f"URL: {url}\n"
                f"Response body: {response.text}"
            )

        response.raise_for_status()

        return response.json()

    async def create_session(self) -> PickerSession:
        """
        Create a new Picker session.

        Returns a session with a pickerUri that users should open to select photos.
        """
        # Configure the picker session
        session_config = {
            # Allow selecting multiple media items
            "allowedMediaTypes": ["PHOTO", "VIDEO"],
            # Enable multi-select
            "selectionMode": "MULTI_SELECT"
        }

        data = await self._make_picker_request("POST", "sessions", json=session_config)

        expire_time = None
        if expire_str := data.get("expireTime"):
            try:
                expire_time = datetime.fromisoformat(expire_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        poll_interval = 5
        if polling_config := data.get("pollingConfig"):
            if interval := polling_config.get("pollInterval"):
                # Parse duration string like "5s"
                poll_interval = int(interval.rstrip("s"))

        return PickerSession(
            id=data["id"],
            picker_uri=data["pickerUri"],
            media_items_set=data.get("mediaItemsSet", False),
            poll_interval_seconds=poll_interval,
            expire_time=expire_time,
        )

    async def get_session(self, session_id: str) -> PickerSession:
        """
        Get the current status of a Picker session.

        Poll this to check when the user has finished selecting photos.
        Note: The pickerUri is only returned on session creation, not on status polls.
        """
        data = await self._make_picker_request("GET", f"sessions/{session_id}")

        # Debug logging to see what Google returns
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Google Picker API response for session {session_id}: {data}")

        expire_time = None
        if expire_str := data.get("expireTime"):
            try:
                expire_time = datetime.fromisoformat(expire_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        poll_interval = 5
        if polling_config := data.get("pollingConfig"):
            if interval := polling_config.get("pollInterval"):
                poll_interval = int(interval.rstrip("s"))

        return PickerSession(
            id=data.get("id", session_id),
            # pickerUri is only in create response, not in status polls
            picker_uri=data.get("pickerUri", ""),
            media_items_set=data.get("mediaItemsSet", False),
            poll_interval_seconds=poll_interval,
            expire_time=expire_time,
        )

    async def delete_session(self, session_id: str) -> None:
        """Delete a Picker session after retrieving media items."""
        await self._make_picker_request("DELETE", f"sessions/{session_id}")

    async def list_media_items(
        self,
        session_id: str,
        page_size: int = 100,
        page_token: Optional[str] = None,
    ) -> tuple[list[PickerMediaItem], Optional[str]]:
        """
        List media items selected in a Picker session.

        Only call this after mediaItemsSet is True.
        """
        params = {"sessionId": session_id, "pageSize": min(page_size, 100)}
        if page_token:
            params["pageToken"] = page_token

        data = await self._make_picker_request("GET", "mediaItems", params=params)

        items = []
        for item in data.get("mediaItems", []):
            media_file = item.get("mediaFile", {})

            creation_time = None
            if create_str := media_file.get("createTime"):
                try:
                    creation_time = datetime.fromisoformat(create_str.replace("Z", "+00:00"))
                except ValueError:
                    pass

            items.append(
                PickerMediaItem(
                    id=item["id"],
                    base_url=media_file.get("baseUrl", ""),
                    mime_type=media_file.get("mimeType", ""),
                    filename=media_file.get("filename"),
                    width=media_file.get("width"),
                    height=media_file.get("height"),
                    camera_make=media_file.get("cameraMake"),
                    camera_model=media_file.get("cameraModel"),
                    creation_time=creation_time,
                )
            )

        return items, data.get("nextPageToken")

    async def iter_all_media_items(
        self,
        session_id: str,
        page_size: int = 100,
    ) -> AsyncIterator[PickerMediaItem]:
        """Iterate over all media items selected in a Picker session."""
        page_token = None

        while True:
            items, next_token = await self.list_media_items(
                session_id=session_id,
                page_size=page_size,
                page_token=page_token,
            )

            for item in items:
                yield item

            if not next_token:
                break

            page_token = next_token

    async def get_photo_bytes(
        self,
        base_url: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> bytes:
        """
        Fetch photo bytes from a base URL.

        Base URLs expire after 60 minutes.
        """
        url = base_url
        if width and height:
            url = f"{url}=w{width}-h{height}"
        elif width:
            url = f"{url}=w{width}"
        elif height:
            url = f"{url}=h{height}"
        else:
            url = f"{url}=d"  # Download original

        client = await self._get_client()
        response = await client.get(url)
        response.raise_for_status()

        return response.content


class GooglePhotosClient(PhotoSource):
    """
    Google Photos Library API client (DEPRECATED for new projects).

    Note: As of March 2023, this API is not available for new Google Cloud projects.
    Use GooglePhotosPickerClient instead.
    """

    BASE_URL = "https://photoslibrary.googleapis.com/v1"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

    SCOPES = [
        "https://www.googleapis.com/auth/photoslibrary.readonly",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._token_expires_at: Optional[datetime] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    def set_tokens(self, access_token: str, refresh_token: Optional[str] = None) -> None:
        """Set the access and refresh tokens."""
        self._access_token = access_token
        if refresh_token:
            self._refresh_token = refresh_token

    async def get_user_info(self) -> Optional[dict]:
        """Get the authenticated user's info from Google."""
        if not self._access_token:
            return None

        client = await self._get_client()
        try:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

    def get_auth_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """Generate the OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "access_type": "offline",
            "prompt": "consent",
        }
        if state:
            params["state"] = state

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.AUTH_URL}?{query}"

    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        """Exchange authorization code for tokens."""
        client = await self._get_client()

        response = await client.post(
            self.TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        data = response.json()

        expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])

        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token", self._refresh_token)
        self._token_expires_at = expires_at

        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            token_type=data["token_type"],
            expires_at=expires_at,
            scopes=data.get("scope", "").split(),
        )

    async def refresh_tokens(self) -> OAuthTokens:
        """Refresh the access token using the refresh token."""
        if not self._refresh_token:
            raise ValueError("No refresh token available")

        client = await self._get_client()

        response = await client.post(
            self.TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        data = response.json()

        expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])

        self._access_token = data["access_token"]
        self._token_expires_at = expires_at

        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=self._refresh_token,
            token_type=data["token_type"],
            expires_at=expires_at,
            scopes=data.get("scope", "").split(),
        )

    async def _ensure_valid_token(self) -> str:
        """Ensure we have a valid access token."""
        if not self._access_token:
            raise ValueError("Not authenticated")

        if self._token_expires_at and datetime.utcnow() >= self._token_expires_at:
            await self.refresh_tokens()

        return self._access_token

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict:
        """Make an authenticated request to the Google Photos API."""
        token = await self._ensure_valid_token()
        client = await self._get_client()

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        url = f"{self.BASE_URL}/{endpoint}"
        response = await client.request(method, url, headers=headers, **kwargs)

        if not response.is_success:
            # Log detailed error info for debugging
            logger.error(
                f"Google Photos API error: {response.status_code} {response.reason_phrase}\n"
                f"URL: {url}\n"
                f"Response body: {response.text}"
            )

        response.raise_for_status()

        return response.json()

    def _parse_media_item(self, item: dict) -> RemotePhotoMetadata:
        """Parse a media item from the API response."""
        media_metadata = item.get("mediaMetadata", {})
        photo_metadata = media_metadata.get("photo", {})

        taken_at = None
        if creation_time := media_metadata.get("creationTime"):
            try:
                taken_at = datetime.fromisoformat(creation_time.replace("Z", "+00:00"))
            except ValueError:
                pass

        return RemotePhotoMetadata(
            external_id=item["id"],
            filename=item.get("filename", ""),
            mime_type=item.get("mimeType", ""),
            width=int(media_metadata.get("width", 0)) or None,
            height=int(media_metadata.get("height", 0)) or None,
            taken_at=taken_at,
            description=item.get("description"),
            camera_make=photo_metadata.get("cameraMake"),
            camera_model=photo_metadata.get("cameraModel"),
            focal_length=photo_metadata.get("focalLength"),
            aperture=photo_metadata.get("apertureFNumber"),
            iso=photo_metadata.get("isoEquivalent"),
            exposure_time=photo_metadata.get("exposureTime"),
            base_url=item.get("baseUrl"),
            product_url=item.get("productUrl"),
        )

    async def list_photos(
        self,
        page_size: int = 100,
        page_token: Optional[str] = None,
    ) -> tuple[list[RemotePhotoMetadata], Optional[str]]:
        """List photos from Google Photos."""
        params = {"pageSize": min(page_size, 100)}
        if page_token:
            params["pageToken"] = page_token

        data = await self._make_request("GET", "mediaItems", params=params)

        photos = [self._parse_media_item(item) for item in data.get("mediaItems", [])]
        next_token = data.get("nextPageToken")

        return photos, next_token

    async def iter_all_photos(
        self,
        page_size: int = 100,
    ) -> AsyncIterator[RemotePhotoMetadata]:
        """Iterate over all photos from Google Photos."""
        page_token = None

        while True:
            photos, next_token = await self.list_photos(
                page_size=page_size,
                page_token=page_token,
            )

            for photo in photos:
                yield photo

            if not next_token:
                break

            page_token = next_token

    async def get_photo(self, external_id: str) -> Optional[RemotePhotoMetadata]:
        """Get a single photo by its external ID."""
        try:
            data = await self._make_request("GET", f"mediaItems/{external_id}")
            return self._parse_media_item(data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def get_photo_bytes(
        self,
        external_id: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Optional[bytes]:
        """Fetch the actual photo bytes."""
        photo = await self.get_photo(external_id)
        if not photo or not photo.base_url:
            return None

        # Build URL with size parameters
        url = photo.base_url
        if width and height:
            url = f"{url}=w{width}-h{height}"
        elif width:
            url = f"{url}=w{width}"
        elif height:
            url = f"{url}=h{height}"
        else:
            url = f"{url}=d"  # Download original

        client = await self._get_client()
        response = await client.get(url)
        response.raise_for_status()

        return response.content

    async def get_photo_url(
        self,
        external_id: str,
        width: int = 2048,
        height: int = 2048,
    ) -> Optional[str]:
        """Get a fresh URL for viewing a photo."""
        photo = await self.get_photo(external_id)
        if not photo or not photo.base_url:
            return None

        return f"{photo.base_url}=w{width}-h{height}"

    async def get_thumbnail_url(
        self,
        external_id: str,
        width: int = 400,
        height: int = 400,
    ) -> Optional[str]:
        """Get a fresh URL for a photo thumbnail."""
        return await self.get_photo_url(external_id, width, height)
