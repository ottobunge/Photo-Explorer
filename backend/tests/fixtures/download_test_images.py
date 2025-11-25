#!/usr/bin/env python3
"""
Download test images for semantic search testing.

This script downloads diverse images from Unsplash to test semantic search functionality.
Images use generic filenames to avoid revealing content - testing relies on AI analysis.
Images are downloaded to a flat directory structure.

Usage:
    python tests/fixtures/download_test_images.py [target_directory]

Total: 50 diverse images for comprehensive semantic search testing
"""

import hashlib
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Diverse images from Unsplash (Public Domain / Unsplash License)
# Using generic photo_NNN.jpg filenames - content revealed only through semantic search
TEST_IMAGES = [
    # Animals (15 images)
    ("photo_001.jpg", "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=800"),
    ("photo_002.jpg", "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=800"),
    ("photo_003.jpg", "https://images.unsplash.com/photo-1497752531616-c3afd9760a11?w=800"),
    ("photo_004.jpg", "https://images.unsplash.com/photo-1533738363-b7f9aef128ce?w=800"),
    ("photo_005.jpg", "https://images.unsplash.com/photo-1552053831-71594a27632d?w=800"),
    ("photo_006.jpg", "https://images.unsplash.com/photo-1568393691622-c7ba131d63b4?w=800"),
    ("photo_007.jpg", "https://images.unsplash.com/photo-1495360010541-f48722b34f7d?w=800"),
    ("photo_008.jpg", "https://images.unsplash.com/photo-1587300003388-59208cc962cb?w=800"),
    ("photo_009.jpg", "https://images.unsplash.com/photo-1551715130-b23fa4c642e3?w=800"),
    ("photo_010.jpg", "https://images.unsplash.com/photo-1470093851219-69951fcbb533?w=800"),  # Bird
    ("photo_011.jpg", "https://images.unsplash.com/photo-1535268647677-300dbf3d78d1?w=800"),  # Horse
    ("photo_012.jpg", "https://images.unsplash.com/photo-1560114928-40f1f1eb26a0?w=800"),  # Rabbit
    ("photo_013.jpg", "https://images.unsplash.com/photo-1484406566174-9da000fda645?w=800"),  # Fish
    ("photo_014.jpg", "https://images.unsplash.com/photo-1530595467537-0b5996c41f2d?w=800"),  # Elephant
    ("photo_015.jpg", "https://images.unsplash.com/photo-1551715373-1c8e6e7f4c4b?w=800"),  # Monkey

    # Nature & Landscapes (15 images)
    ("photo_016.jpg", "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800"),  # Mountain
    ("photo_017.jpg", "https://images.unsplash.com/photo-1439066615861-d1af74d74000?w=800"),  # Lake
    ("photo_018.jpg", "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=800"),  # Sunset
    ("photo_019.jpg", "https://images.unsplash.com/photo-1518837695005-2083093ee35b?w=800"),  # Ocean
    ("photo_020.jpg", "https://images.unsplash.com/photo-1502082553048-f009c37129b9?w=800"),  # Desert
    ("photo_021.jpg", "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800"),  # Forest
    ("photo_022.jpg", "https://images.unsplash.com/photo-1490682143684-14369e18dce8?w=800"),  # Beach
    ("photo_023.jpg", "https://images.unsplash.com/photo-1419242902214-272b3f66ee7a?w=800"),  # Snow
    ("photo_024.jpg", "https://images.unsplash.com/photo-1501594907352-04cda38ebc29?w=800"),  # Waterfall
    ("photo_025.jpg", "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=800"),  # Meadow
    ("photo_026.jpg", "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800"),  # Nature path
    ("photo_027.jpg", "https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=800"),  # Sky
    ("photo_028.jpg", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800"),  # Mountains
    ("photo_029.jpg", "https://images.unsplash.com/photo-1426604966848-d7adac402bff?w=800"),  # Tree
    ("photo_030.jpg", "https://images.unsplash.com/photo-1500835556837-99ac94a94552?w=800"),  # River

    # Urban & Architecture (10 images)
    ("photo_031.jpg", "https://images.unsplash.com/photo-1480714378408-67cf0d13bc1b?w=800"),  # City skyline
    ("photo_032.jpg", "https://images.unsplash.com/photo-1449824913935-59a10b8d2000?w=800"),  # Modern building
    ("photo_033.jpg", "https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?w=800"),  # Architecture
    ("photo_034.jpg", "https://images.unsplash.com/photo-1486870591958-9b9d0d1dda99?w=800"),  # Streets
    ("photo_035.jpg", "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=800"),  # Bridge
    ("photo_036.jpg", "https://images.unsplash.com/photo-1514565131-fce0801e5785?w=800"),  # Church
    ("photo_037.jpg", "https://images.unsplash.com/photo-1444723121867-7a241cacace9?w=800"),  # Highway
    ("photo_038.jpg", "https://images.unsplash.com/photo-1475855581690-80accde3ae2b?w=800"),  # Apartment
    ("photo_039.jpg", "https://images.unsplash.com/photo-1471623320832-752e8bbf8413?w=800"),  # Historic building
    ("photo_040.jpg", "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=800"),  # Window

    # Objects & Still Life (10 images)
    ("photo_041.jpg", "https://images.unsplash.com/photo-1452421822248-d4c2b47f0c81?w=800"),  # Coffee
    ("photo_042.jpg", "https://images.unsplash.com/photo-1481487196290-c152efe083f5?w=800"),  # Books
    ("photo_043.jpg", "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800"),  # Phone
    ("photo_044.jpg", "https://images.unsplash.com/photo-1484788984921-03950022c9ef?w=800"),  # Laptop
    ("photo_045.jpg", "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=800"),  # Food
    ("photo_046.jpg", "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=800"),  # Portrait
    ("photo_047.jpg", "https://images.unsplash.com/photo-1499728603263-13726abce5fd?w=800"),  # Music
    ("photo_048.jpg", "https://images.unsplash.com/photo-1491438590914-bc09fcaaf77a?w=800"),  # Plant
    ("photo_049.jpg", "https://images.unsplash.com/photo-1511367461989-f85a21fda167?w=800"),  # Camera
    ("photo_050.jpg", "https://images.unsplash.com/photo-1511919884226-fd3cad34687c?w=800"),  # Art
]


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

                # Calculate checksum for verification
                checksum = hashlib.md5(data).hexdigest()
                file_size_kb = len(data) / 1024
                print(f"✓ ({file_size_kb:.1f} KB)")
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
    # Allow custom target directory via command line argument
    if len(sys.argv) > 1:
        images_dir = Path(sys.argv[1]).resolve()
    else:
        # Default to fixtures directory
        fixtures_dir = Path(__file__).parent
        images_dir = fixtures_dir / "images"

    # Create directory (flat structure, no subdirectories)
    images_dir.mkdir(parents=True, exist_ok=True)

    print("📸 Downloading test images for semantic search...")
    print(f"   Target directory: {images_dir}")
    print(f"   Total images: {len(TEST_IMAGES)}")
    print()

    downloaded = 0
    skipped = 0
    failed = 0

    for filename, url in TEST_IMAGES:
        dest_path = images_dir / filename

        # Skip if already exists
        if dest_path.exists():
            print(f"  ⏭  {filename} (already exists)")
            skipped += 1
            continue

        print(f"  📥 {filename}...", end=" ")
        if download_file(url, dest_path):
            downloaded += 1
        else:
            failed += 1

    print()
    print("=" * 60)

    total_available = downloaded + skipped

    print(f"✅ Complete! {total_available} images available")
    print(f"   Downloaded: {downloaded}")
    print(f"   Skipped (already exist): {skipped}")

    if failed > 0:
        print(f"   Failed: {failed}")
        print()

    # Only fail if we have too few images for a meaningful demo
    if total_available < 20:
        print("❌ Too few images available (need at least 20 for demo).")
        print("   Some Unsplash URLs may have changed. Try updating the URLs.")
        sys.exit(1)
    elif failed > 0:
        print("⚠️  Some downloads failed, but we have enough for the demo.")
    else:
        print("🎉 All test images ready for semantic search testing!")

    # Create a README
    readme_path = images_dir / "README.md"
    readme_path.write_text("""# Test Images for Semantic Search

This directory contains 50 diverse test images downloaded from Unsplash for testing
semantic search functionality.

## Contents
50 images with generic filenames (photo_001.jpg - photo_050.jpg) containing:
- Animals (15 images) - various pets and wildlife
- Nature & Landscapes (15 images) - mountains, oceans, forests, etc.
- Urban & Architecture (10 images) - cities, buildings, bridges
- Objects & Still Life (10 images) - everyday items, food, technology

## Purpose
Generic filenames ensure semantic search testing relies on AI analysis rather than
filename hints. Tests queries like:
- "cat playing" → finds photo_001.jpg
- "mountain sunset" → finds photo_018.jpg
- "coffee cup" → finds photo_041.jpg

## License
All images are from Unsplash and are free to use under the Unsplash License:
https://unsplash.com/license

## Regenerating
To re-download these images:
```bash
python tests/fixtures/download_test_images.py
```

Or specify custom directory:
```bash
python tests/fixtures/download_test_images.py /path/to/directory
```

## DO NOT COMMIT
These images should NOT be committed to git. They are automatically downloaded
during test setup and are excluded via .gitignore.
""")

    print(f"📝 Created README at {readme_path}")


if __name__ == "__main__":
    main()
