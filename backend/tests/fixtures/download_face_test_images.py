#!/usr/bin/env python3
"""
Download test images with faces for face detection and recognition testing.

This script downloads diverse portraits from Unsplash to test face detection,
face clustering, and face recognition functionality. Images use generic
filenames to avoid revealing content - testing relies on AI analysis.

Usage:
    python tests/fixtures/download_face_test_images.py [target_directory]

Total: 20 diverse portrait images for comprehensive face detection testing
"""

import hashlib
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Diverse portrait images from Unsplash (Public Domain / Unsplash License)
# Using generic face_NNN.jpg filenames - content revealed only through face detection
FACE_TEST_IMAGES = [
    # Single portraits - diverse ages, genders, ethnicities (10 images)
    ("face_001.jpg", "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800"),  # Young man
    ("face_002.jpg", "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=800"),  # Young woman
    ("face_003.jpg", "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=800"),  # Bearded man
    ("face_004.jpg", "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800"),  # Woman with curly hair
    ("face_005.jpg", "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=800"),  # Man in suit
    ("face_006.jpg", "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=800"),  # Woman with long hair
    ("face_007.jpg", "https://images.unsplash.com/photo-1547425260-76bcadfb4f2c?w=800"),  # Older man with glasses
    ("face_008.jpg", "https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?w=800"),  # Young woman outdoors
    ("face_009.jpg", "https://images.unsplash.com/photo-1463453091185-61582044d556?w=800"),  # Young man smiling
    ("face_010.jpg", "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=800"),  # Woman with glasses

    # Group photos - multiple faces (5 images)
    ("face_011.jpg", "https://images.unsplash.com/photo-1511632765486-a01980e01a18?w=800"),  # Group of friends
    ("face_012.jpg", "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=800"),  # Family photo
    ("face_013.jpg", "https://images.unsplash.com/photo-1543269865-cbf427effbad?w=800"),  # Friends laughing
    ("face_014.jpg", "https://images.unsplash.com/photo-1521575107034-e0fa0b594529?w=800"),  # Business team
    ("face_015.jpg", "https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=800"),  # Group selfie

    # Profile and angled faces (3 images)
    ("face_016.jpg", "https://images.unsplash.com/photo-1531123897727-8f129e1688ce?w=800"),  # Profile view
    ("face_017.jpg", "https://images.unsplash.com/photo-1522556189639-b150ed9c4330?w=800"),  # Three-quarter view
    ("face_018.jpg", "https://images.unsplash.com/photo-1525598912003-663126343e1f?w=800"),  # Angled portrait

    # Different lighting conditions (2 images)
    ("face_019.jpg", "https://images.unsplash.com/photo-1504257432389-52343af06ae3?w=800"),  # Studio lighting
    ("face_020.jpg", "https://images.unsplash.com/photo-1506919258185-6078bba55d2a?w=800"),  # Natural lighting
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
    """Download all face test images."""
    # Allow custom target directory via command line argument
    if len(sys.argv) > 1:
        images_dir = Path(sys.argv[1]).resolve()
    else:
        # Default to fixtures directory
        fixtures_dir = Path(__file__).parent
        images_dir = fixtures_dir / "face-images"

    # Create directory (flat structure, no subdirectories)
    images_dir.mkdir(parents=True, exist_ok=True)

    print("👤 Downloading face test images for face detection testing...")
    print(f"   Target directory: {images_dir}")
    print(f"   Total images: {len(FACE_TEST_IMAGES)}")
    print()

    downloaded = 0
    skipped = 0
    failed = 0

    for filename, url in FACE_TEST_IMAGES:
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

    print(f"✅ Complete! {total_available} face images available")
    print(f"   Downloaded: {downloaded}")
    print(f"   Skipped (already exist): {skipped}")

    if failed > 0:
        print(f"   Failed: {failed}")
        print()

    # Only fail if we have too few images for a meaningful test
    if total_available < 10:
        print("❌ Too few images available (need at least 10 for face detection tests).")
        print("   Some Unsplash URLs may have changed. Try updating the URLs.")
        sys.exit(1)
    elif failed > 0:
        print("⚠️  Some downloads failed, but we have enough for testing.")
    else:
        print("🎉 All face test images ready for face detection testing!")

    # Create a README
    readme_path = images_dir / "README.md"
    readme_path.write_text("""# Test Images for Face Detection

This directory contains 20 diverse portrait images downloaded from Unsplash for testing
face detection, face clustering, and face recognition functionality.

## Contents
20 images with generic filenames (face_001.jpg - face_020.jpg) containing:
- Single portraits (10 images) - diverse ages, genders, ethnicities
- Group photos (5 images) - multiple faces for clustering tests
- Profile and angled faces (3 images) - challenging detection angles
- Different lighting (2 images) - various lighting conditions

## Purpose
Generic filenames ensure face detection testing relies on AI analysis rather than
filename hints. Tests face detection accuracy, clustering, and recognition across:
- Different face angles and orientations
- Multiple faces in single image
- Various lighting and image quality
- Diverse demographics

## Use Cases
- Integration tests for face detection pipeline
- Face clustering algorithm validation
- Face recognition accuracy testing
- Performance benchmarking

## License
All images are from Unsplash and are free to use under the Unsplash License:
https://unsplash.com/license

## Regenerating
To re-download these images:
```bash
python tests/fixtures/download_face_test_images.py
```

Or specify custom directory:
```bash
python tests/fixtures/download_face_test_images.py /path/to/directory
```

## DO NOT COMMIT
These images should NOT be committed to git. They are automatically downloaded
during test setup and are excluded via .gitignore.
""")

    print(f"📝 Created README at {readme_path}")


if __name__ == "__main__":
    main()
