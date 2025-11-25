"""Test fixtures for image-based tests."""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def test_images_dir():
    """
    Ensure test images are downloaded before running tests.

    Returns the path to the test images directory.
    Images are downloaded from Unsplash if they don't exist.
    """
    fixtures_dir = Path(__file__).parent
    images_dir = fixtures_dir / "images"
    download_script = fixtures_dir / "download_test_images.py"

    # Check if images already exist
    expected_categories = ["cats", "dogs", "raccoons", "ferrets"]
    expected_count_per_category = 5

    images_exist = all(
        (images_dir / category).exists()
        and len(list((images_dir / category).glob("*.jpg"))) >= expected_count_per_category
        for category in expected_categories
    )

    if not images_exist:
        print("\n📸 Test images not found. Downloading from Unsplash...")
        result = subprocess.run(
            [sys.executable, str(download_script)],
            capture_output=True,
            text=True, check=False,
        )

        if result.returncode != 0:
            pytest.fail(f"Failed to download test images:\n{result.stdout}\n{result.stderr}")

        print(result.stdout)

    return images_dir


@pytest.fixture(scope="session")
def cat_images(test_images_dir):
    """Return list of cat image paths."""
    cat_dir = test_images_dir / "cats"
    return sorted(cat_dir.glob("*.jpg"))


@pytest.fixture(scope="session")
def dog_images(test_images_dir):
    """Return list of dog image paths."""
    dog_dir = test_images_dir / "dogs"
    return sorted(dog_dir.glob("*.jpg"))


@pytest.fixture(scope="session")
def raccoon_images(test_images_dir):
    """Return list of raccoon image paths."""
    raccoon_dir = test_images_dir / "raccoons"
    return sorted(raccoon_dir.glob("*.jpg"))


@pytest.fixture(scope="session")
def ferret_images(test_images_dir):
    """Return list of ferret image paths."""
    ferret_dir = test_images_dir / "ferrets"
    return sorted(ferret_dir.glob("*.jpg"))


@pytest.fixture(scope="session")
def all_test_images(cat_images, dog_images, raccoon_images, ferret_images):
    """Return dict of all test images by category."""
    return {
        "cats": cat_images,
        "dogs": dog_images,
        "raccoons": raccoon_images,
        "ferrets": ferret_images,
    }
