#!/usr/bin/env python3
"""
Download test images for semantic search testing.

This script downloads a small dataset of animal photos from public sources
to test semantic search functionality. Images are downloaded to tests/fixtures/images/
and should NOT be committed to git.

Usage:
    python tests/fixtures/download_test_images.py

Animals included: cats, dogs, raccoons, ferrets (5 images each, 20 total)
"""

import hashlib
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Public domain / Creative Commons images from various sources
TEST_IMAGES = {
    "cats": [
        ("cat_1.jpg", "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=800"),
        ("cat_2.jpg", "https://images.unsplash.com/photo-1533738363-b7f9aef128ce?w=800"),
        ("cat_3.jpg", "https://images.unsplash.com/photo-1495360010541-f48722b34f7d?w=800"),
        ("cat_4.jpg", "https://images.unsplash.com/photo-1529778873920-4da4926a72c2?w=800"),
        ("cat_5.jpg", "https://images.unsplash.com/photo-1543852786-1cf6624b9987?w=800"),
    ],
    "dogs": [
        ("dog_1.jpg", "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=800"),
        ("dog_2.jpg", "https://images.unsplash.com/photo-1552053831-71594a27632d?w=800"),
        ("dog_3.jpg", "https://images.unsplash.com/photo-1587300003388-59208cc962cb?w=800"),
        ("dog_4.jpg", "https://images.unsplash.com/photo-1561037404-61cd46aa615b?w=800"),
        ("dog_5.jpg", "https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?w=800"),
    ],
    "raccoons": [
        ("raccoon_1.jpg", "https://images.unsplash.com/photo-1497752531616-c3afd9760a11?w=800"),
        ("raccoon_2.jpg", "https://images.unsplash.com/photo-1609621838510-5ad474b7d25d?w=800"),
        ("raccoon_3.jpg", "https://images.unsplash.com/photo-1606518155919-89a1bcddee3d?w=800"),
        ("raccoon_4.jpg", "https://images.unsplash.com/photo-1604076947583-5fb7dcb4e486?w=800"),
        ("raccoon_5.jpg", "https://images.unsplash.com/photo-1612171527719-4372f2eb0340?w=800"),
    ],
    "ferrets": [
        ("ferret_1.jpg", "https://images.unsplash.com/photo-1601758282760-4c27d2e0f8f9?w=800"),
        ("ferret_2.jpg", "https://images.unsplash.com/photo-1589952283406-b53a7d1347e8?w=800"),
        ("ferret_3.jpg", "https://images.unsplash.com/photo-1568393691622-c7ba131d63b4?w=800"),
        ("ferret_4.jpg", "https://images.unsplash.com/photo-1545486332-9e0999c535b2?w=800"),
        ("ferret_5.jpg", "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=800"),
    ],
}


def download_file(url: str, dest_path: Path, retries: int = 3) -> bool:
    """Download a file from URL to destination path."""
    for attempt in range(retries):
        try:
            # Add headers to avoid being blocked
            req = Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; PhotoExplorerTests/1.0)'
                }
            )

            with urlopen(req, timeout=30) as response:
                data = response.read()
                dest_path.write_bytes(data)

                # Calculate checksum
                checksum = hashlib.md5(data).hexdigest()
                print(f"  ✓ Downloaded {dest_path.name} ({len(data)} bytes, md5: {checksum[:8]}...)")
                return True

        except (URLError, HTTPError) as e:
            if attempt < retries - 1:
                print(f"  ⚠ Attempt {attempt + 1} failed: {e}, retrying...")
            else:
                print(f"  ✗ Failed to download {url}: {e}")
                return False
        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            return False

    return False


def main():
    """Download all test images."""
    # Get the fixtures directory
    fixtures_dir = Path(__file__).parent
    images_dir = fixtures_dir / "images"

    # Create directories
    images_dir.mkdir(exist_ok=True)

    print("📸 Downloading test images for semantic search...")
    print(f"   Target directory: {images_dir}")
    print()

    total_images = sum(len(images) for images in TEST_IMAGES.values())
    downloaded = 0
    skipped = 0
    failed = 0

    for category, images in TEST_IMAGES.items():
        category_dir = images_dir / category
        category_dir.mkdir(exist_ok=True)

        print(f"📁 {category.upper()}")

        for filename, url in images:
            dest_path = category_dir / filename

            # Skip if already exists
            if dest_path.exists():
                print(f"  ⏭  {filename} (already exists)")
                skipped += 1
                continue

            if download_file(url, dest_path):
                downloaded += 1
            else:
                failed += 1

    print()
    print("=" * 60)
    print(f"✅ Complete! Downloaded {downloaded} images")
    print(f"   Skipped (already exist): {skipped}")
    if failed > 0:
        print(f"   Failed: {failed}")
        print()
        print("⚠  Some downloads failed. You may want to retry.")
        sys.exit(1)
    else:
        print()
        print("🎉 All test images ready for semantic search testing!")

    # Create a README
    readme_path = images_dir / "README.md"
    readme_path.write_text("""# Test Images for Semantic Search

This directory contains test images downloaded from Unsplash for testing semantic search functionality.

## Contents
- **cats/** - 5 cat photos
- **dogs/** - 5 dog photos
- **raccoons/** - 5 raccoon photos
- **ferrets/** - 5 ferret photos

## License
All images are from Unsplash and are free to use under the Unsplash License:
https://unsplash.com/license

## Regenerating
To re-download these images:
```bash
python tests/fixtures/download_test_images.py
```

## DO NOT COMMIT
These images should NOT be committed to git. They are automatically downloaded
during test setup and are excluded via .gitignore.
""")

    print(f"📝 Created README at {readme_path}")


if __name__ == "__main__":
    main()
