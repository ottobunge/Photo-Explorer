"""E2E test fixtures and helper utilities."""

import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import pytest
import pytest_asyncio

# Import common fixtures from integration tests
from tests.integration.conftest import (
    test_db_engine,
    test_file_storage,
    test_session,
    test_vector_store,
)


# ===== Helper Utilities for Async Task Testing =====


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
def face_test_images_dir():
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
        print("\n👤 Face test images not found. Downloading from Unsplash...")
        result = subprocess.run(
            [sys.executable, str(download_script)],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            pytest.fail(f"Failed to download face test images:\n{result.stdout}\n{result.stderr}")

        print(result.stdout)

    return images_dir


@pytest.fixture(scope="session")
def single_face_images(face_test_images_dir):
    """Return list of single portrait images (face_001 to face_010)."""
    return sorted(face_test_images_dir.glob("face_00[1-9].jpg")) + sorted(
        face_test_images_dir.glob("face_010.jpg")
    )


@pytest.fixture(scope="session")
def multi_face_images(face_test_images_dir):
    """Return list of group photos with multiple faces (face_011 to face_015)."""
    return sorted(face_test_images_dir.glob("face_01[1-5].jpg"))


@pytest.fixture(scope="session")
def profile_face_images(face_test_images_dir):
    """Return list of profile/angled face images (face_016 to face_018)."""
    return sorted(face_test_images_dir.glob("face_01[6-8].jpg"))


@pytest.fixture(scope="session")
def all_face_images(face_test_images_dir):
    """Return list of all face test images."""
    return sorted(face_test_images_dir.glob("face_*.jpg"))
