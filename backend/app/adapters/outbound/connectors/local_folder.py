"""Local folder connector adapter."""

import asyncio
import hashlib
import logging
import os
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles
import aiofiles.os
import exifread
from PIL import Image

from app.domain.entities import Connector
from app.domain.entities.connector import ConnectorType

logger = logging.getLogger(__name__)

# Supported image extensions
SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".heic",
    ".heif",
    ".tiff",
    ".tif",
    ".raw",
    ".cr2",
    ".nef",
    ".arw",
}


class LocalFolderScanner:
    """
    Scanner for local folders.

    Walks directories to find image files and extract metadata.
    """

    def __init__(self, connector: Connector):
        if connector.type != ConnectorType.LOCAL:
            raise ValueError("Connector must be of type LOCAL")

        self.connector = connector
        self.path = Path(connector.config.get("path", ""))
        self.recursive = connector.config.get("recursive", True)
        self.auto_album = connector.config.get("auto_album", False)

        if not self.path.exists():
            raise ValueError(f"Path does not exist: {self.path}")
        if not self.path.is_dir():
            raise ValueError(f"Path is not a directory: {self.path}")

    def is_supported_image(self, file_path: Path) -> bool:
        """Check if a file is a supported image format."""
        return file_path.suffix.lower() in SUPPORTED_EXTENSIONS

    async def scan(self) -> AsyncIterator[dict]:
        """
        Scan the folder for image files.

        Yields dictionaries with file metadata for each image found.
        """
        logger.info(f"Starting scan of {self.path} (recursive={self.recursive})")

        if self.recursive:
            for root, dirs, files in os.walk(self.path):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith(".")]

                for filename in files:
                    if filename.startswith("."):
                        continue

                    file_path = Path(root) / filename
                    if self.is_supported_image(file_path):
                        try:
                            metadata = await self._extract_file_metadata(file_path)
                            yield metadata
                        except Exception as e:
                            logger.warning(f"Error processing {file_path}: {e}")
        else:
            for item in self.path.iterdir():
                if item.is_file() and not item.name.startswith("."):
                    if self.is_supported_image(item):
                        try:
                            metadata = await self._extract_file_metadata(item)
                            yield metadata
                        except Exception as e:
                            logger.warning(f"Error processing {item}: {e}")

    async def _extract_file_metadata(self, file_path: Path) -> dict:
        """Extract metadata from an image file."""
        stat = await aiofiles.os.stat(file_path)

        # Calculate file hash for change detection
        file_hash = await self._calculate_file_hash(file_path)

        # Get relative path from connector root
        relative_path = file_path.relative_to(self.path)

        # Determine subfolder for auto-album
        subfolder = None
        if self.auto_album and relative_path.parent != Path():
            subfolder = str(relative_path.parent)

        metadata = {
            "filename": file_path.name,
            "source_path": str(file_path.absolute()),
            "relative_path": str(relative_path),
            "file_size": stat.st_size,
            "file_hash": file_hash,
            "modified_at": datetime.fromtimestamp(stat.st_mtime),
            "subfolder": subfolder,
            "connector_id": self.connector.id.value,
            "connector_type": "local",
        }

        # Try to extract EXIF data
        try:
            exif_data = await self._extract_exif(file_path)
            if exif_data:
                metadata["exif"] = exif_data
                if exif_data.get("taken_at"):
                    metadata["taken_at"] = exif_data["taken_at"]
        except Exception as e:
            logger.debug(f"Could not extract EXIF from {file_path}: {e}")

        # Try to get image dimensions
        try:
            dimensions = await self._get_image_dimensions(file_path)
            if dimensions:
                metadata["width"] = dimensions[0]
                metadata["height"] = dimensions[1]
        except Exception as e:
            logger.debug(f"Could not get dimensions from {file_path}: {e}")

        # Determine MIME type
        metadata["mime_type"] = self._get_mime_type(file_path)

        return metadata

    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file for change detection."""
        hash_md5 = hashlib.md5()
        async with aiofiles.open(file_path, "rb") as f:
            # Read in chunks for large files
            while chunk := await f.read(8192):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    async def _extract_exif(self, file_path: Path) -> Optional[dict]:
        """Extract EXIF data from an image file."""

        def _read_exif(path: Path) -> Optional[dict]:
            with open(path, "rb") as f:
                tags = exifread.process_file(f, details=False)

            if not tags:
                return None

            result = {}

            # Camera info
            if "Image Make" in tags:
                result["camera_make"] = str(tags["Image Make"])
            if "Image Model" in tags:
                result["camera_model"] = str(tags["Image Model"])
            if "EXIF LensModel" in tags:
                result["lens_model"] = str(tags["EXIF LensModel"])

            # Capture settings
            if "EXIF FocalLength" in tags:
                try:
                    result["focal_length"] = float(tags["EXIF FocalLength"].values[0])
                except (IndexError, ValueError, TypeError):
                    pass

            if "EXIF FNumber" in tags:
                try:
                    result["aperture"] = float(tags["EXIF FNumber"].values[0])
                except (IndexError, ValueError, TypeError):
                    pass

            if "EXIF ISOSpeedRatings" in tags:
                try:
                    result["iso"] = int(str(tags["EXIF ISOSpeedRatings"]))
                except (ValueError, TypeError):
                    pass

            if "EXIF ExposureTime" in tags:
                try:
                    result["shutter_speed"] = str(tags["EXIF ExposureTime"])
                except (ValueError, TypeError):
                    pass

            if "EXIF Flash" in tags:
                result["flash"] = str(tags["EXIF Flash"])

            if "Image Orientation" in tags:
                try:
                    result["orientation"] = int(str(tags["Image Orientation"]))
                except (ValueError, TypeError):
                    pass

            # Date taken
            for date_tag in ["EXIF DateTimeOriginal", "EXIF DateTimeDigitized", "Image DateTime"]:
                if date_tag in tags:
                    try:
                        date_str = str(tags[date_tag])
                        result["taken_at"] = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                        break
                    except ValueError:
                        pass

            # GPS coordinates
            if "GPS GPSLatitude" in tags and "GPS GPSLongitude" in tags:
                try:
                    lat = self._convert_gps_to_decimal(
                        tags["GPS GPSLatitude"].values, str(tags.get("GPS GPSLatitudeRef", "N"))
                    )
                    lon = self._convert_gps_to_decimal(
                        tags["GPS GPSLongitude"].values, str(tags.get("GPS GPSLongitudeRef", "E"))
                    )
                    result["gps_latitude"] = lat
                    result["gps_longitude"] = lon

                    if "GPS GPSAltitude" in tags:
                        try:
                            alt = float(tags["GPS GPSAltitude"].values[0])
                            result["gps_altitude"] = alt
                        except (IndexError, ValueError, TypeError):
                            pass
                except (ValueError, TypeError, IndexError):
                    pass

            return result if result else None

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _read_exif, file_path)

    def _convert_gps_to_decimal(self, dms_values, ref: str) -> float:
        """Convert GPS DMS (degrees, minutes, seconds) to decimal."""
        d = float(dms_values[0])
        m = float(dms_values[1])
        s = float(dms_values[2])

        decimal = d + (m / 60.0) + (s / 3600.0)

        if ref in ["S", "W"]:
            decimal = -decimal

        return decimal

    async def _get_image_dimensions(self, file_path: Path) -> Optional[tuple[int, int]]:
        """Get image dimensions using PIL."""

        def _read_dimensions(path: Path) -> Optional[tuple[int, int]]:
            try:
                with Image.open(path) as img:
                    return img.size
            except Exception:
                return None

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _read_dimensions, file_path)

    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type based on file extension."""
        ext = file_path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
            ".heic": "image/heic",
            ".heif": "image/heif",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
            ".raw": "image/raw",
            ".cr2": "image/x-canon-cr2",
            ".nef": "image/x-nikon-nef",
            ".arw": "image/x-sony-arw",
        }
        return mime_types.get(ext, "image/jpeg")

    async def check_for_changes(
        self,
        known_files: dict[str, str],  # path -> hash mapping
    ) -> tuple[list[dict], list[str], list[str]]:
        """
        Check for new, modified, and deleted files.

        Args:
            known_files: Dictionary mapping file paths to their known hashes

        Returns:
            Tuple of (new_files, modified_files, deleted_files)
        """
        new_files = []
        modified_paths = []
        current_paths = set()

        async for metadata in self.scan():
            source_path = metadata["source_path"]
            current_paths.add(source_path)

            if source_path not in known_files:
                # New file
                new_files.append(metadata)
            elif known_files[source_path] != metadata["file_hash"]:
                # Modified file
                modified_paths.append(source_path)
                new_files.append(metadata)

        # Find deleted files
        deleted_paths = [path for path in known_files.keys() if path not in current_paths]

        return new_files, modified_paths, deleted_paths

    async def get_file_bytes(self, source_path: str) -> bytes:
        """Read file bytes from the filesystem."""
        async with aiofiles.open(source_path, "rb") as f:
            return await f.read()
