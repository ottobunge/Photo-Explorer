"""E2E test fixtures and helper utilities."""

import asyncio
import io
import logging
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, List, Optional
from uuid import UUID

import pytest
import pytest_asyncio
from celery import Celery
from celery.result import AsyncResult
from PIL import Image

# Import common fixtures from integration tests
from tests.integration.conftest import (
    test_db_engine,
    test_file_storage,
    test_session,
    test_vector_store,
)

logger = logging.getLogger(__name__)


# ===== Fixture Aliases =====


@pytest.fixture
def db_session(test_session):
    """Alias for test_session for consistency with API tests."""
    return test_session


# ===== Celery Worker for E2E Tests =====


class TestCeleryWorker:
    """Manage Celery worker lifecycle for E2E tests."""

    def __init__(self, celery_app: Celery, worker_concurrency: int = 2):
        """
        Initialize test worker.

        Args:
            celery_app: Celery application instance
            worker_concurrency: Number of concurrent worker processes
        """
        self.celery_app = celery_app
        self.worker_concurrency = worker_concurrency
        self.worker_thread: Optional[threading.Thread] = None
        self.worker: Optional[Any] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start Celery worker in a background thread."""
        if self.worker_thread is not None:
            logger.warning("Worker already started")
            return

        logger.info("Starting Celery worker for E2E tests...")

        def run_worker() -> None:
            """Run worker in background thread."""
            try:
                self.worker = self.celery_app.Worker(
                    concurrency=self.worker_concurrency,
                    loglevel=logging.INFO,
                    without_gossip=True,
                    without_mingle=True,
                    without_heartbeat=True,
                    queues=["default", "processing", "clustering", "dlq"],
                    pool="threads",  # Use thread pool for testing (no fork issues)
                )
                # Run worker until stop event is set
                self.worker.start()
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)

        self.worker_thread = threading.Thread(target=run_worker, daemon=True)
        self.worker_thread.start()

        # Wait for worker to be ready (max 10 seconds)
        for _ in range(100):
            if self.worker and self.worker.state in ("online", "ready"):
                logger.info("Celery worker ready")
                return
            time.sleep(0.1)

        logger.warning("Celery worker did not reach ready state within timeout")

    def stop(self) -> None:
        """Stop Celery worker."""
        if self.worker is None:
            return

        logger.info("Stopping Celery worker...")
        self._stop_event.set()

        # Send stop signal
        if self.worker:
            try:
                self.worker.stop()
            except Exception as e:
                logger.warning(f"Error stopping worker: {e}")

        # Wait for worker thread to finish (max 10 seconds)
        if self.worker_thread:
            self.worker_thread.join(timeout=10.0)

        self.worker = None
        self.worker_thread = None
        logger.info("Celery worker stopped")


@pytest.fixture(scope="session")
def celery_app_for_e2e():
    """Get Celery app configured for testing."""
    from app.adapters.inbound.workers.celery_app import celery_app

    # Configure for testing
    celery_app.conf.update(
        task_always_eager=False,  # Actually run tasks in worker
        task_eager_propagates=True,
        worker_prefetch_multiplier=1,
    )

    return celery_app


@pytest.fixture(scope="session", autouse=True)
def celery_worker(celery_app_for_e2e: Celery) -> None:
    """Start and stop Celery worker for entire E2E test session.

    This fixture starts a worker at session scope so it runs once for all tests.
    The autouse=True parameter ensures it runs automatically for all E2E tests.
    """
    worker_manager = TestCeleryWorker(celery_app_for_e2e, worker_concurrency=2)
    worker_manager.start()

    yield  # Run all tests with worker running

    worker_manager.stop()


# ===== Image Processing Helpers =====


async def generate_thumbnail(image_data: bytes, max_size: tuple[int, int] = (300, 300)) -> bytes:
    """
    Generate a thumbnail from image data.

    Args:
        image_data: Original image bytes
        max_size: Maximum dimensions (width, height)

    Returns:
        Thumbnail image bytes (JPEG format)
    """
    with Image.open(io.BytesIO(image_data)) as img:
        # Convert to RGB if needed (handles RGBA, P, etc.)
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Generate thumbnail (preserves aspect ratio)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Save to bytes
        thumb_buffer = io.BytesIO()
        img.save(thumb_buffer, format="JPEG", quality=85)
        return thumb_buffer.getvalue()


async def crop_face_from_image(
    image_data: bytes,
    bbox: "BoundingBox",  # type: ignore[name-defined]
) -> bytes:
    """
    Crop a face region from image data.

    Args:
        image_data: Original image bytes
        bbox: Bounding box with x, y, width, height attributes

    Returns:
        Cropped face image bytes (JPEG format)
    """
    with Image.open(io.BytesIO(image_data)) as img:
        # Crop using bbox coordinates
        cropped = img.crop((bbox.x, bbox.y, bbox.x + bbox.width, bbox.y + bbox.height))

        # Convert to RGB if needed
        if cropped.mode != "RGB":
            cropped = cropped.convert("RGB")

        # Save to bytes
        crop_buffer = io.BytesIO()
        cropped.save(crop_buffer, format="JPEG", quality=90)
        return crop_buffer.getvalue()


# ===== Helper Utilities for Async Task Testing =====


def wait_for_celery_task(
    task_id: str,
    expected_state: str = "SUCCESS",
    timeout: float = 30.0,
    poll_interval: float = 0.5,
) -> AsyncResult:
    """
    Wait for a Celery task to reach expected state.

    Args:
        task_id: Celery task ID
        expected_state: Expected task state (SUCCESS, FAILURE, RETRY, etc.)
        timeout: Maximum time to wait in seconds
        poll_interval: Time between checks in seconds

    Returns:
        Celery AsyncResult when task reaches expected state

    Raises:
        TimeoutError: If task does not reach expected state within timeout
    """
    from app.adapters.inbound.workers.celery_app import celery_app

    start_time = time.time()

    while True:
        # Check if we've exceeded timeout
        if time.time() - start_time > timeout:
            result = celery_app.AsyncResult(task_id)
            raise TimeoutError(
                f"Task {task_id} did not reach state '{expected_state}' within {timeout}s. "
                f"Current state: {result.state}, Ready: {result.ready()}"
            )

        # Check task state
        result = celery_app.AsyncResult(task_id)

        if result.state == expected_state:
            return result

        # If task failed but we weren't expecting failure
        if result.state == "FAILURE" and expected_state != "FAILURE":
            raise RuntimeError(
                f"Task {task_id} failed: {result.result}"
            )

        # Wait before next check
        time.sleep(poll_interval)


async def wait_for_celery_task_async(
    task_id: str,
    expected_state: str = "SUCCESS",
    timeout: float = 30.0,
    poll_interval: float = 0.5,
) -> AsyncResult:
    """
    Async version of wait_for_celery_task.

    Args:
        task_id: Celery task ID
        expected_state: Expected task state
        timeout: Maximum time to wait in seconds
        poll_interval: Time between checks in seconds

    Returns:
        Celery AsyncResult when task reaches expected state

    Raises:
        TimeoutError: If task does not reach expected state within timeout
    """
    from app.adapters.inbound.workers.celery_app import celery_app

    start_time = asyncio.get_event_loop().time()

    while True:
        # Check if we've exceeded timeout
        if asyncio.get_event_loop().time() - start_time > timeout:
            result = celery_app.AsyncResult(task_id)
            raise TimeoutError(
                f"Task {task_id} did not reach state '{expected_state}' within {timeout}s. "
                f"Current state: {result.state}, Ready: {result.ready()}"
            )

        # Check task state
        result = celery_app.AsyncResult(task_id)

        if result.state == expected_state:
            return result

        # If task failed but we weren't expecting failure
        if result.state == "FAILURE" and expected_state != "FAILURE":
            raise RuntimeError(
                f"Task {task_id} failed: {result.result}"
            )

        # Wait before next check
        await asyncio.sleep(poll_interval)


async def wait_for_condition(
    condition_fn: Callable[[], bool | Any],
    timeout: float = 30.0,
    poll_interval: float = 0.5,
    error_message: str = "Condition not met within timeout",
) -> Any:
    """
    Wait for a condition to become true.

    Args:
        condition_fn: Async or sync callable that returns truthy value when condition is met
        timeout: Maximum time to wait in seconds
        poll_interval: Time between checks in seconds
        error_message: Error message if timeout is reached

    Returns:
        The truthy value returned by condition_fn

    Raises:
        TimeoutError: If condition is not met within timeout
    """
    start_time = asyncio.get_event_loop().time()

    while True:
        # Check if we've exceeded timeout
        if asyncio.get_event_loop().time() - start_time > timeout:
            raise TimeoutError(f"{error_message} (waited {timeout}s)")

        # Evaluate condition
        if asyncio.iscoroutinefunction(condition_fn):
            result = await condition_fn()
        else:
            result = condition_fn()

        # If condition is met, return the result
        if result:
            return result

        # Wait before next check
        await asyncio.sleep(poll_interval)


async def wait_for_processing(
    photo_repo,
    photo_id: str,
    expected_status: str = "completed",
    timeout: float = 30.0,
) -> Any:
    """
    Wait for a photo to reach a specific processing status.

    Args:
        photo_repo: Photo repository instance
        photo_id: Photo ID to check
        expected_status: Expected processing status
        timeout: Maximum time to wait

    Returns:
        The photo entity when it reaches expected status

    Raises:
        TimeoutError: If photo doesn't reach expected status within timeout
    """

    async def check_status():
        photo = await photo_repo.find_by_id(photo_id)
        if photo and photo.processing_status == expected_status:
            return photo
        return None

    return await wait_for_condition(
        check_status,
        timeout=timeout,
        error_message=f"Photo {photo_id} did not reach status '{expected_status}'",
    )


async def wait_for_faces_detected(
    face_repo,
    photo_id: str,
    min_faces: int = 1,
    timeout: float = 30.0,
) -> list:
    """
    Wait for faces to be detected in a photo.

    Args:
        face_repo: Face repository instance
        photo_id: Photo ID to check
        min_faces: Minimum number of faces expected
        timeout: Maximum time to wait

    Returns:
        List of detected faces

    Raises:
        TimeoutError: If faces are not detected within timeout
    """

    async def check_faces():
        faces = await face_repo.find_faces_by_photo(photo_id)
        if len(faces) >= min_faces:
            return faces
        return None

    return await wait_for_condition(
        check_faces,
        timeout=timeout,
        error_message=f"At least {min_faces} face(s) not detected in photo {photo_id}",
    )


async def wait_for_cluster_assignment(
    face_repo,
    face_id: str,
    timeout: float = 30.0,
) -> Any:
    """
    Wait for a face to be assigned to a cluster.

    Args:
        face_repo: Face repository instance
        face_id: Face ID to check
        timeout: Maximum time to wait

    Returns:
        The face entity when it's assigned to a cluster

    Raises:
        TimeoutError: If face is not clustered within timeout
    """

    async def check_cluster():
        face = await face_repo.find_face_by_id(face_id)
        if face and face.cluster_id:
            return face
        return None

    return await wait_for_condition(
        check_cluster,
        timeout=timeout,
        error_message=f"Face {face_id} not assigned to cluster",
    )


# ===== Face Test Image Fixtures =====


@pytest.fixture(scope="session")
def face_test_images_dir() -> Path:
    """
    Ensure face test images are downloaded before running tests.

    Returns the path to the face test images directory.
    Images are downloaded from Unsplash if they don't exist.
    """
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    images_dir = fixtures_dir / "face-images"
    download_script = fixtures_dir / "download_face_test_images.py"

    # Check if images already exist (expecting 20 face images)
    expected_count = 20
    images_exist = (
        images_dir.exists() and len(list(images_dir.glob("face_*.jpg"))) >= expected_count
    )

    if not images_exist:
        print("\nFace test images not found. Downloading from Unsplash...")
        result = subprocess.run(
            [sys.executable, str(download_script)],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            error_msg = (
                "Failed to download face test images.\n"
                f"Script output:\n{result.stdout}\n{result.stderr}\n\n"
                "To fix:\n"
                "1. Check your internet connection\n"
                "2. Verify Unsplash API access\n"
                "3. Run manually: python tests/fixtures/download_face_test_images.py"
            )
            pytest.fail(error_msg)

        print(result.stdout)

    return images_dir


@pytest.fixture(scope="session")
def single_face_images(face_test_images_dir: Path) -> List[Path]:
    """Return list of single portrait images (face_001 to face_010)."""
    return sorted(face_test_images_dir.glob("face_00[1-9].jpg")) + sorted(
        face_test_images_dir.glob("face_010.jpg")
    )


@pytest.fixture(scope="session")
def multi_face_images(face_test_images_dir: Path) -> List[Path]:
    """Return list of group photos with multiple faces (face_011 to face_015)."""
    return sorted(face_test_images_dir.glob("face_01[1-5].jpg"))


@pytest.fixture(scope="session")
def profile_face_images(face_test_images_dir: Path) -> List[Path]:
    """Return list of profile/angled face images (face_016 to face_018)."""
    return sorted(face_test_images_dir.glob("face_01[6-8].jpg"))


@pytest.fixture(scope="session")
def all_face_images(face_test_images_dir: Path) -> List[Path]:
    """Return list of all face test images."""
    return sorted(face_test_images_dir.glob("face_*.jpg"))
