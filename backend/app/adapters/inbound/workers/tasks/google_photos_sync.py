"""Google Photos sync tasks for background execution."""

import asyncio
import logging
import os
from datetime import datetime
from uuid import UUID

import httpx
from sqlalchemy.exc import OperationalError

from app.adapters.inbound.workers.celery_app import celery_app
from app.adapters.inbound.workers.exceptions import (
    AuthenticationError,
    InvalidDataError,
    NetworkError,
    PermanentError,
    RateLimitError,
    TokenRefreshError,
    TransientError,
)
from app.adapters.outbound.connectors.google_photos import (
    GooglePhotosClient,
    GooglePhotosPickerClient,
)
from app.adapters.outbound.ml import get_ml_services
from app.adapters.outbound.persistence.postgres import (
    ConnectorRepositoryPostgres,
    PhotoRepositoryPostgres,
)
from app.adapters.outbound.persistence.qdrant import QdrantVectorStore
from app.adapters.outbound.storage import LocalFileStorage, SecureTokenStorage
from app.domain.entities import Photo
from app.domain.entities.connector import ConnectorStatus, ConnectorType, SyncStats

logger = logging.getLogger(__name__)


def get_google_credentials(connector_config: dict) -> tuple[str, str]:
    """
    Get Google OAuth credentials.

    First checks connector config, then falls back to environment variables.

    Args:
        connector_config: Connector configuration dict

    Returns:
        Tuple of (client_id, client_secret)

    Raises:
        ValueError: If credentials are not found
    """
    client_id = connector_config.get("client_id") or os.environ.get("GOOGLE_API_CLIENT_ID")
    client_secret = connector_config.get("client_secret") or os.environ.get(
        "GOOGLE_API_CLIENT_SECRET"
    )

    if not client_id or not client_secret:
        raise ValueError(
            "Google OAuth credentials not found. "
            "Set GOOGLE_API_CLIENT_ID and GOOGLE_API_CLIENT_SECRET environment variables "
            "or configure them in the connector settings."
        )

    return client_id, client_secret


def run_async(coro):
    """Helper to run async code in sync context.

    Creates a new event loop for each call without setting it as the global
    event loop to avoid race conditions in multi-threaded Celery workers.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    name="google_photos_sync.sync_google_photos",
    autoretry_for=(
        TransientError,
        NetworkError,
        RateLimitError,
        TokenRefreshError,
        OperationalError,
    ),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    retry_backoff_max=600,
    time_limit=3600,  # 1 hour hard limit
    soft_time_limit=3000,  # 50 minutes soft limit
)
def sync_google_photos_task(self, connector_id: str) -> dict:
    """
    Sync photos from Google Photos.

    Timeouts: 50 min soft, 1 hour hard.

    Fetches new photos from Google Photos API and creates local references.
    Automatically retries on network errors, rate limits, and transient failures
    with exponential backoff.

    Args:
        connector_id: UUID of the Google Photos connector

    Returns:
        Dictionary with sync results

    Raises:
        PermanentError: For authentication failures and invalid configurations
        TransientError: For network issues and temporary service unavailability
        RateLimitError: When API rate limit is exceeded (will retry with backoff)
    """
    try:
        return run_async(_sync_google_photos_async(connector_id))
    except (AuthenticationError, InvalidDataError):
        logger.error(
            f"Permanent error syncing Google Photos {connector_id}, will not retry",
            exc_info=True,
            extra={"connector_id": connector_id},
        )
        raise
    except (TransientError, NetworkError, RateLimitError, TokenRefreshError) as e:
        logger.warning(
            f"Transient error syncing Google Photos {connector_id}, will retry",
            extra={
                "connector_id": connector_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "retries": self.request.retries,
            },
        )
        raise
    except Exception as e:
        logger.exception(
            f"Unexpected error syncing Google Photos {connector_id}",
            extra={"connector_id": connector_id},
        )
        raise PermanentError(f"Unexpected sync error: {e!s}", {"connector_id": connector_id})


async def _sync_google_photos_async(connector_id: str) -> dict:
    """Async implementation of Google Photos sync."""
    from app.adapters.outbound.persistence.postgres.database import get_worker_session_context

    connector_uuid = UUID(connector_id)
    started_at = datetime.utcnow()

    async with get_worker_session_context() as session:
        connector_repo = ConnectorRepositoryPostgres(session)
        photo_repo = PhotoRepositoryPostgres(session)

        # Get connector
        connector = await connector_repo.find_by_id(connector_uuid)
        if not connector:
            return {"status": "error", "message": "Connector not found"}

        if connector.type != ConnectorType.GOOGLE_PHOTOS:
            return {"status": "error", "message": "Not a Google Photos connector"}

        # Get OAuth credentials (from config or environment)
        try:
            client_id, client_secret = get_google_credentials(connector.config)
        except ValueError as e:
            return {"status": "error", "message": str(e)}

        # Load tokens from secure storage
        token_storage = SecureTokenStorage()
        tokens = await token_storage.load_tokens(f"google_photos_{connector_id}")

        if not tokens:
            connector.set_error("Not authenticated - OAuth tokens not found")
            await connector_repo.save(connector)
            logger.error(f"No tokens found for connector {connector_id}")
            return {"status": "error", "message": "Not authenticated"}

        # Log token info for debugging (not the actual token values!)
        logger.info(
            f"Loaded tokens for connector {connector_id}: "
            f"scopes={tokens.scopes}, expires_at={tokens.expires_at}"
        )

        # Mark as syncing
        connector.set_syncing()
        await connector_repo.save(connector)

        try:
            # Create Google Photos client
            client = GooglePhotosClient(
                client_id=client_id,
                client_secret=client_secret,
                access_token=tokens.access_token,
                refresh_token=tokens.refresh_token,
            )

            # Get existing photos for this connector
            existing_photos = await photo_repo.find_by_connector(connector_uuid, limit=100000)
            known_external_ids = {
                p.external_id: p.id.value for p in existing_photos if p.external_id
            }

            # Use mutable counters during sync (SyncStats is frozen/immutable)
            sync_counters = {
                "total_items": 0,
                "indexed": 0,
                "skipped": 0,
                "failed": 0,
            }

            try:
                # Iterate through all photos from Google Photos
                async for metadata in client.iter_all_photos():
                    sync_counters["total_items"] += 1

                    # Check if photo already exists
                    if metadata.external_id in known_external_ids:
                        sync_counters["skipped"] += 1
                        continue

                    try:
                        # Create new photo reference
                        photo = Photo.create_from_connector(
                            filename=metadata.filename or f"photo_{metadata.external_id}",
                            connector_type="google_photos",
                            connector_id=connector_uuid,
                            external_id=metadata.external_id,
                            source_path=None,  # Google Photos doesn't have local path
                        )

                        # Set metadata from Google Photos API
                        photo.set_metadata(
                            mime_type=metadata.mime_type,
                            file_size=None,  # Not provided by API
                            width=metadata.width,
                            height=metadata.height,
                            taken_at=metadata.taken_at,
                        )

                        # Set description if available
                        if metadata.description:
                            photo.description = metadata.description

                        # Save photo
                        photo = await photo_repo.save(photo)
                        sync_counters["indexed"] += 1

                        logger.debug(f"Indexed Google Photos item: {metadata.external_id}")

                        # Note: Don't queue processing tasks here - Google Photos
                        # images need to be fetched first. Processing will happen
                        # when the photo is viewed or explicitly fetched.

                    except Exception as e:
                        logger.error(f"Error indexing {metadata.external_id}: {e}")
                        sync_counters["failed"] += 1

                # If tokens were refreshed, save them
                if client._access_token != tokens.access_token:
                    from app.application.ports.outbound import OAuthTokens

                    new_tokens = OAuthTokens(
                        access_token=client._access_token,
                        refresh_token=client._refresh_token,
                        token_type="Bearer",
                        expires_at=client._token_expires_at,
                        scopes=GooglePhotosClient.SCOPES,
                    )
                    try:
                        await token_storage.save_tokens(f"google_photos_{connector_id}", new_tokens)
                    except Exception as token_err:
                        logger.error(
                            f"Failed to save refreshed tokens for connector {connector_id}: {token_err}",
                            extra={
                                "connector_id": connector_id,
                                "error": str(token_err),
                                "error_type": type(token_err).__name__,
                            },
                            exc_info=True,
                        )
                        # Don't fail the sync task if token save fails - the sync completed successfully
                        # The tokens will be refreshed again on the next sync

            finally:
                await client.close()

            # Create final immutable SyncStats value object
            stats = SyncStats(
                total_items=sync_counters["total_items"],
                indexed=sync_counters["indexed"],
                skipped=sync_counters["skipped"],
                failed=sync_counters["failed"],
                started_at=started_at,
                completed_at=datetime.utcnow(),
            )

            # Update connector with sync stats
            connector.record_sync(stats)
            await connector_repo.save(connector)

            logger.info(
                f"Google Photos sync complete for {connector.name}: "
                f"{stats.indexed} new, {stats.skipped} skipped, {stats.failed} failed"
            )

            return {
                "status": "completed",
                "connector_id": connector_id,
                "total_items": stats.total_items,
                "indexed": stats.indexed,
                "skipped": stats.skipped,
                "failed": stats.failed,
                "duration_seconds": stats.duration_seconds,
            }

        except Exception as e:
            logger.exception(
                f"Error syncing Google Photos connector {connector_id}: {e}",
                extra={
                    "connector_id": connector_id,
                    "connector_name": connector.name if connector else "unknown",
                    "error_type": type(e).__name__,
                },
            )
            connector.set_error(str(e))
            await connector_repo.save(connector)
            return {"status": "error", "message": str(e)}


@celery_app.task(
    bind=True,
    name="google_photos_sync.refresh_photo_url",
    autoretry_for=(
        TransientError,
        NetworkError,
        RateLimitError,
        TokenRefreshError,
        OperationalError,
    ),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    time_limit=3600,  # 1 hour hard limit
    soft_time_limit=3000,  # 50 minutes soft limit
)
def refresh_photo_url_task(self, photo_id: str) -> dict:
    """
    Refresh the baseUrl for a Google Photos image.

    Timeouts: 50 min soft, 1 hour hard.

    Google Photos baseUrls expire after 60 minutes, so this task
    fetches a fresh URL when needed.

    Args:
        photo_id: UUID of the photo

    Returns:
        Dictionary with the fresh URL or error
    """
    return run_async(_refresh_photo_url_async(photo_id))


async def _refresh_photo_url_async(photo_id: str) -> dict:
    """Async implementation of URL refresh."""
    from app.adapters.outbound.persistence.postgres.database import get_worker_session_context

    photo_uuid = UUID(photo_id)

    async with get_worker_session_context() as session:
        photo_repo = PhotoRepositoryPostgres(session)
        connector_repo = ConnectorRepositoryPostgres(session)

        # Get photo
        photo = await photo_repo.find_by_id(photo_uuid)
        if not photo:
            return {"status": "error", "message": "Photo not found"}

        if photo.connector_type != "google_photos":
            return {"status": "error", "message": "Not a Google Photos photo"}

        if not photo.connector_id or not photo.external_id:
            return {"status": "error", "message": "Missing connector info"}

        # Get connector
        connector = await connector_repo.find_by_id(photo.connector_id)
        if not connector:
            return {"status": "error", "message": "Connector not found"}

        # Get credentials (from config or environment)
        try:
            client_id, client_secret = get_google_credentials(connector.config)
        except ValueError as e:
            return {"status": "error", "message": str(e)}

        token_storage = SecureTokenStorage()
        tokens = await token_storage.load_tokens(f"google_photos_{photo.connector_id}")

        if not tokens:
            return {"status": "error", "message": "Not authenticated"}

        try:
            client = GooglePhotosClient(
                client_id=client_id,
                client_secret=client_secret,
                access_token=tokens.access_token,
                refresh_token=tokens.refresh_token,
            )

            try:
                # Get fresh photo metadata with new baseUrl
                url = await client.get_photo_url(photo.external_id)

                if url:
                    return {
                        "status": "completed",
                        "photo_id": photo_id,
                        "url": url,
                    }
                else:
                    return {"status": "error", "message": "Photo not found in Google Photos"}

            finally:
                await client.close()

        except Exception as e:
            logger.error(f"Error refreshing URL for photo {photo_id}: {e}")
            return {"status": "error", "message": str(e)}


@celery_app.task(
    bind=True,
    name="google_photos_sync.fetch_photo_bytes",
    autoretry_for=(
        TransientError,
        NetworkError,
        RateLimitError,
        TokenRefreshError,
        OperationalError,
        OSError,
    ),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    time_limit=3600,  # 1 hour hard limit
    soft_time_limit=3000,  # 50 minutes soft limit
)
def fetch_google_photo_bytes_task(self, photo_id: str) -> dict:
    """
    Fetch and store photo bytes from Google Photos.

    Timeouts: 50 min soft, 1 hour hard.

    Downloads the original photo and stores it locally for processing.

    Args:
        photo_id: UUID of the photo

    Returns:
        Dictionary with result
    """
    return run_async(_fetch_photo_bytes_async(photo_id))


async def _fetch_photo_bytes_async(photo_id: str) -> dict:
    """Async implementation of photo bytes fetching."""
    from app.adapters.outbound.persistence.postgres.database import get_worker_session_context

    photo_uuid = UUID(photo_id)

    async with get_worker_session_context() as session:
        photo_repo = PhotoRepositoryPostgres(session)
        connector_repo = ConnectorRepositoryPostgres(session)

        # Get photo
        photo = await photo_repo.find_by_id(photo_uuid)
        if not photo:
            return {"status": "error", "message": "Photo not found"}

        if photo.connector_type != "google_photos":
            return {"status": "error", "message": "Not a Google Photos photo"}

        if not photo.connector_id or not photo.external_id:
            return {"status": "error", "message": "Missing connector info"}

        # Get connector
        connector = await connector_repo.find_by_id(photo.connector_id)
        if not connector:
            return {"status": "error", "message": "Connector not found"}

        # Get credentials (from config or environment)
        try:
            client_id, client_secret = get_google_credentials(connector.config)
        except ValueError as e:
            return {"status": "error", "message": str(e)}

        token_storage = SecureTokenStorage()
        tokens = await token_storage.load_tokens(f"google_photos_{photo.connector_id}")

        if not tokens:
            return {"status": "error", "message": "Not authenticated"}

        try:
            client = GooglePhotosClient(
                client_id=client_id,
                client_secret=client_secret,
                access_token=tokens.access_token,
                refresh_token=tokens.refresh_token,
            )

            try:
                # Fetch photo bytes
                photo_bytes = await client.get_photo_bytes(photo.external_id)

                if not photo_bytes:
                    return {"status": "error", "message": "Could not fetch photo"}

                # Store the photo using file storage
                from app.adapters.outbound.storage import LocalFileStorage

                file_storage = LocalFileStorage()
                storage_path = await file_storage.save_photo(
                    photo.id.value, photo_bytes, photo.mime_type or "image/jpeg"
                )

                # Update photo with storage path
                photo.storage_path = storage_path
                await photo_repo.save(photo)

                return {
                    "status": "completed",
                    "photo_id": photo_id,
                    "storage_path": storage_path,
                    "size": len(photo_bytes),
                }

            finally:
                await client.close()

        except Exception as e:
            logger.error(f"Error fetching bytes for photo {photo_id}: {e}")
            return {"status": "error", "message": str(e)}


@celery_app.task(
    name="google_photos_sync.schedule_periodic_sync",
    autoretry_for=(TransientError, OperationalError, ConnectionError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},  # Fewer retries for scheduled task
)
def schedule_google_photos_sync() -> dict:
    """
    Scheduled task to sync all enabled Google Photos connectors.

    This should be called periodically (e.g., hourly) by Celery Beat.
    """
    return run_async(_schedule_periodic_sync_async())


async def _schedule_periodic_sync_async() -> dict:
    """Schedule sync for all enabled Google Photos connectors."""
    from app.adapters.outbound.persistence.postgres.database import get_worker_session_context

    async with get_worker_session_context() as session:
        connector_repo = ConnectorRepositoryPostgres(session)

        # Find all enabled Google Photos connectors
        connectors = await connector_repo.find_by_type(ConnectorType.GOOGLE_PHOTOS)
        enabled = [c for c in connectors if c.enabled]

        queued = 0
        for connector in enabled:
            # Don't sync if already syncing
            if connector.status == ConnectorStatus.SYNCING:
                continue

            sync_google_photos_task.delay(str(connector.id.value))
            queued += 1

        logger.info(f"Queued {queued} Google Photos sync tasks")
        return {"status": "completed", "queued": queued}


# ===================
# Picker API Tasks
# ===================


@celery_app.task(
    bind=True,
    name="google_photos_sync.import_picker_photos",
    autoretry_for=(
        TransientError,
        NetworkError,
        RateLimitError,
        TokenRefreshError,
        OperationalError,
        OSError,
    ),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    time_limit=3600,  # 1 hour hard limit
    soft_time_limit=3000,  # 50 minutes soft limit
)
def import_picker_photos_task(self, connector_id: str, session_id: str) -> dict:
    """
    Import photos from a Google Photos Picker session.

    Timeouts: 50 min soft, 1 hour hard.

    This task retrieves the photos selected by the user in the Picker UI
    and creates local photo references for them.

    Args:
        connector_id: UUID of the Google Photos connector
        session_id: ID of the Picker session

    Returns:
        Dictionary with import results
    """
    return run_async(_import_picker_photos_async(connector_id, session_id))


async def _import_picker_photos_async(connector_id: str, session_id: str) -> dict:
    """Async implementation of Picker photos import."""
    from app.adapters.outbound.persistence.postgres.database import get_worker_session_context

    connector_uuid = UUID(connector_id)
    started_at = datetime.utcnow()

    async with get_worker_session_context() as session:
        connector_repo = ConnectorRepositoryPostgres(session)
        photo_repo = PhotoRepositoryPostgres(session)

        # Get connector
        connector = await connector_repo.find_by_id(connector_uuid)
        if not connector:
            return {"status": "error", "message": "Connector not found"}

        if connector.type != ConnectorType.GOOGLE_PHOTOS:
            return {"status": "error", "message": "Not a Google Photos connector"}

        # Get OAuth credentials
        try:
            client_id, client_secret = get_google_credentials(connector.config)
        except ValueError as e:
            return {"status": "error", "message": str(e)}

        # Load tokens
        token_storage = SecureTokenStorage()
        tokens = await token_storage.load_tokens(f"google_photos_{connector_id}")

        if not tokens:
            connector.set_error("Not authenticated - OAuth tokens not found")
            await connector_repo.save(connector)
            return {"status": "error", "message": "Not authenticated"}

        logger.info(f"Importing photos from picker session {session_id}")

        # Mark as syncing
        connector.set_syncing()
        await connector_repo.save(connector)

        try:
            # Create Picker client
            client = GooglePhotosPickerClient(
                client_id=client_id,
                client_secret=client_secret,
                access_token=tokens.access_token,
                refresh_token=tokens.refresh_token,
            )

            # Get existing photos for this connector to avoid duplicates
            existing_photos = await photo_repo.find_by_connector(connector_uuid, limit=100000)
            known_external_ids = {
                p.external_id: p.id.value for p in existing_photos if p.external_id
            }

            # Use mutable counters during sync (SyncStats is frozen/immutable)
            sync_counters = {
                "total_items": 0,
                "indexed": 0,
                "skipped": 0,
                "failed": 0,
            }

            # Initialize services ONCE for all photos (singletons, no cleanup needed)
            ml_services = get_ml_services()
            vector_store = QdrantVectorStore()
            file_storage = LocalFileStorage()

            try:
                # Iterate through all selected photos
                async for item in client.iter_all_media_items(session_id):
                    sync_counters["total_items"] += 1

                    # Check if photo already exists
                    if item.id in known_external_ids:
                        sync_counters["skipped"] += 1
                        continue

                    try:
                        # Create new photo reference
                        photo = Photo.create_from_connector(
                            filename=item.filename or f"photo_{item.id}",
                            connector_type="google_photos",
                            connector_id=connector_uuid,
                            external_id=item.id,
                            source_path=None,
                        )

                        # Set metadata
                        photo.set_metadata(
                            mime_type=item.mime_type,
                            file_size=None,
                            width=item.width,
                            height=item.height,
                            taken_at=item.creation_time,
                        )

                        # Fetch image and generate thumbnail + embeddings
                        if item.base_url:
                            image_data = None
                            try:
                                # Request a medium-sized image for processing
                                # 512px is good for CLIP and face detection
                                image_url = f"{item.base_url}=w512-h512"

                                # Need to include auth token for accessing the image
                                headers = {"Authorization": f"Bearer {client._access_token}"}

                                async with httpx.AsyncClient() as http_client:
                                    response = await http_client.get(
                                        image_url, headers=headers, timeout=30.0
                                    )
                                    response.raise_for_status()
                                    image_data = response.content

                                # Save as thumbnail (using pre-initialized file_storage)
                                thumbnail_path = await file_storage.save_thumbnail(
                                    image_data, str(photo.id.value)
                                )
                                photo.thumbnail_path = thumbnail_path

                                logger.debug(f"Saved thumbnail for {item.id}")
                            except Exception as thumb_err:
                                logger.warning(f"Failed to fetch image for {item.id}: {thumb_err}")

                            # Generate CLIP embedding if we have image data
                            # (using pre-initialized ml_services and vector_store)
                            if image_data:
                                try:
                                    embedding = await ml_services.encode_image(image_data)
                                    await vector_store.store_photo_embedding(
                                        photo.id.value,
                                        embedding,
                                        payload={
                                            "filename": photo.filename,
                                            "connector_type": photo.connector_type,
                                        },
                                    )
                                    photo.set_processing_status("completed")
                                    logger.debug(f"Generated embedding for {item.id}")
                                except Exception as emb_err:
                                    logger.warning(
                                        f"Failed to generate embedding for {item.id}: {emb_err}"
                                    )
                                    # Continue without embedding

                        # Save photo
                        photo = await photo_repo.save(photo)
                        sync_counters["indexed"] += 1

                        logger.debug(f"Indexed Google Photos item: {item.id}")

                    except Exception as e:
                        logger.error(f"Error indexing {item.id}: {e}")
                        sync_counters["failed"] += 1

                # Clean up the session
                try:
                    await client.delete_session(session_id)
                except Exception as e:
                    logger.warning(f"Failed to delete picker session: {e}")

            finally:
                await client.close()

            # Create final immutable SyncStats value object
            stats = SyncStats(
                total_items=sync_counters["total_items"],
                indexed=sync_counters["indexed"],
                skipped=sync_counters["skipped"],
                failed=sync_counters["failed"],
                started_at=started_at,
                completed_at=datetime.utcnow(),
            )

            # Update connector with sync stats
            connector.record_sync(stats)
            await connector_repo.save(connector)

            logger.info(
                f"Google Photos picker import complete for {connector.name}: "
                f"{stats.indexed} new, {stats.skipped} skipped, {stats.failed} failed"
            )

            return {
                "status": "completed",
                "connector_id": connector_id,
                "session_id": session_id,
                "total_items": stats.total_items,
                "indexed": stats.indexed,
                "skipped": stats.skipped,
                "failed": stats.failed,
                "duration_seconds": stats.duration_seconds,
            }

        except Exception as e:
            logger.exception(
                f"Error importing from picker session {session_id}: {e}",
                extra={
                    "connector_id": connector_id,
                    "session_id": session_id,
                    "error_type": type(e).__name__,
                },
            )
            connector.set_error(str(e))
            await connector_repo.save(connector)
            return {"status": "error", "message": str(e)}
