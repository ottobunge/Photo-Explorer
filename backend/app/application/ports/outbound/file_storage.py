"""File storage port - Interface for file system operations.

Security Model:
- All storage paths are relative to designated storage directories (photos, thumbnails, faces)
- Path traversal attacks using ".." are rejected
- Absolute paths are rejected
- Symlinks that escape storage directories are rejected
- All paths are canonicalized before use

Implementations MUST enforce these security properties.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Optional


class FileStorage(ABC):
    """Interface for file storage operations.

    All implementations must enforce the following security guarantees:

    1. Path Containment: All file operations are restricted to designated
       storage directories (photos, thumbnails, faces). No file outside
       these directories can be accessed or modified.

    2. Path Traversal Prevention: Paths containing ".." components are
       rejected to prevent directory traversal attacks.

    3. Absolute Path Rejection: Absolute paths (/etc/passwd, C:\\Windows\\)
       are rejected. Only relative paths within storage directories are allowed.

    4. Symlink Safety: Symlinks that resolve outside the storage directory
       are rejected, preventing symlink escapes.

    5. Canonical Resolution: All paths are resolved to their canonical form
       using resolve(), eliminating . and .. references before validation.

    These guarantees prevent attackers from accessing files outside the
    intended storage directories, even with malicious path inputs.
    """

    @abstractmethod
    async def save_photo(
        self,
        file: BinaryIO,
        filename: str,
    ) -> str:
        """
        Save a photo file to storage.

        Args:
            file: File-like object containing the image data
            filename: Original filename

        Returns:
            The storage path for the saved file
        """

    @abstractmethod
    async def save_thumbnail(
        self,
        image_data: bytes,
        photo_id: str,
    ) -> str:
        """
        Save a thumbnail image.

        Args:
            image_data: Thumbnail image bytes
            photo_id: The photo's unique identifier

        Returns:
            The storage path for the thumbnail
        """

    @abstractmethod
    async def save_face_crop(
        self,
        image_data: bytes,
        face_id: str,
    ) -> str:
        """
        Save a cropped face image.

        Args:
            image_data: Face crop image bytes
            face_id: The face's unique identifier

        Returns:
            The storage path for the face crop
        """

    @abstractmethod
    async def get_file(self, path: str) -> Optional[bytes]:
        """Read a file from storage.

        The path must be relative and safe. Absolute paths and path
        traversal attempts are rejected.

        Args:
            path: The relative storage path (must not contain ".." or be absolute)

        Returns:
            File bytes or None if not found

        Raises:
            PathSecurityError: If path contains security vulnerabilities
        """

    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """Delete a file from storage.

        The path must be relative and safe. Absolute paths and path
        traversal attempts are rejected.

        Args:
            path: The relative storage path (must not contain ".." or be absolute)

        Returns:
            True if deleted, False if not found

        Raises:
            PathSecurityError: If path contains security vulnerabilities
        """

    @abstractmethod
    async def file_exists(self, path: str) -> bool:
        """Check if a file exists.

        The path must be relative and safe. Absolute paths and path
        traversal attempts are rejected.

        Args:
            path: The relative storage path (must not contain ".." or be absolute)

        Returns:
            True if file exists

        Raises:
            PathSecurityError: If path contains security vulnerabilities
        """

    @abstractmethod
    async def read_source_file(self, source_path: str) -> Optional[bytes]:
        """Read a file from a connector source path.

        This method is used to read files from local connector source paths
        (e.g., photos in watched folders). The implementation must validate
        that the source path is within registered/allowed directories.

        Security considerations:
        - Path must be validated against registered connector folders
        - Path traversal attempts must be rejected
        - Symlinks that escape allowed directories must be rejected

        Args:
            source_path: The absolute source path from a local connector

        Returns:
            File bytes or None if not found or not allowed

        Raises:
            PathSecurityError: If path is outside allowed directories
        """

    @abstractmethod
    def get_absolute_path(self, storage_path: str) -> Path:
        """Get the absolute filesystem path for a storage path.

        The path is validated for security before returning. Absolute paths
        and path traversal attempts are rejected.

        Args:
            storage_path: The relative storage path (must not contain ".." or be absolute)

        Returns:
            Absolute Path object within a storage directory

        Raises:
            PathSecurityError: If path contains security vulnerabilities
        """
