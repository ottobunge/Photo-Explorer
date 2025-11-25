"""Model downloading utilities."""

import hashlib
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

from .config import ModelConfig, get_model_config

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Information about a downloadable model."""

    name: str
    url: str
    filename: str
    size_mb: float
    sha256: Optional[str] = None


# Known CLIP models and their OpenAI weights
CLIP_MODELS = {
    "ViT-B-32": ModelInfo(
        name="ViT-B-32 (OpenAI)",
        url="https://openaipublic.azureedge.net/clip/models/40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af/ViT-B-32.pt",
        filename="ViT-B-32.pt",
        size_mb=338,
        sha256="40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af",
    ),
    "ViT-B-16": ModelInfo(
        name="ViT-B-16 (OpenAI)",
        url="https://openaipublic.azureedge.net/clip/models/5806e77cd80f8b59890b7e101eabd078d9fb84e6937f9e85e4ecb61988df416f/ViT-B-16.pt",
        filename="ViT-B-16.pt",
        size_mb=335,
        sha256="5806e77cd80f8b59890b7e101eabd078d9fb84e6937f9e85e4ecb61988df416f",
    ),
    "ViT-L-14": ModelInfo(
        name="ViT-L-14 (OpenAI)",
        url="https://openaipublic.azureedge.net/clip/models/b8cca3fd41ae0c99ba7e8951adf17d267cdb84cd88be6f7c2e0eca1737a03836/ViT-L-14.pt",
        filename="ViT-L-14.pt",
        size_mb=890,
        sha256="b8cca3fd41ae0c99ba7e8951adf17d267cdb84cd88be6f7c2e0eca1737a03836",
    ),
    "ViT-L-14-336": ModelInfo(
        name="ViT-L-14@336px (OpenAI)",
        url="https://openaipublic.azureedge.net/clip/models/3035c92b350959924f9f00213499208652fc7ea050643e8b385c2dac08641f02/ViT-L-14-336px.pt",
        filename="ViT-L-14-336px.pt",
        size_mb=891,
        sha256="3035c92b350959924f9f00213499208652fc7ea050643e8b385c2dac08641f02",
    ),
}

# InsightFace model packs
INSIGHTFACE_MODELS = {
    "buffalo_l": ModelInfo(
        name="Buffalo L (Large)",
        url="https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip",
        filename="buffalo_l.zip",
        size_mb=326,
    ),
    "buffalo_m": ModelInfo(
        name="Buffalo M (Medium)",
        url="https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_m.zip",
        filename="buffalo_m.zip",
        size_mb=180,
    ),
    "buffalo_s": ModelInfo(
        name="Buffalo S (Small)",
        url="https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_s.zip",
        filename="buffalo_s.zip",
        size_mb=90,
    ),
    "buffalo_sc": ModelInfo(
        name="Buffalo SC (Small CPU)",
        url="https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_sc.zip",
        filename="buffalo_sc.zip",
        size_mb=45,
    ),
}


class ModelDownloader:
    """Utility for downloading and managing AI models."""

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or get_model_config()
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=300.0, follow_redirects=True)
        return self._client

    def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "ModelDownloader":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def download_file(
        self,
        url: str,
        dest_path: Path,
        expected_sha256: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        """
        Download a file with progress tracking and optional hash verification.

        Args:
            url: URL to download from
            dest_path: Destination file path
            expected_sha256: Expected SHA256 hash (optional)
            progress_callback: Callback for progress updates (downloaded, total)

        Returns:
            True if download succeeded and verified
        """
        client = self._get_client()

        # Create parent directory
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if file already exists and is valid
        if dest_path.exists() and expected_sha256:
            if self._verify_hash(dest_path, expected_sha256):
                logger.info(f"Model already exists and verified: {dest_path}")
                return True

        logger.info(f"Downloading {url} to {dest_path}")

        try:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))

                with open(dest_path, "wb") as f:
                    downloaded = 0
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)

            # Verify hash if provided
            if expected_sha256:
                if not self._verify_hash(dest_path, expected_sha256):
                    logger.error(f"Hash verification failed for {dest_path}")
                    dest_path.unlink()
                    return False

            logger.info(f"Successfully downloaded {dest_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            if dest_path.exists():
                dest_path.unlink()
            return False

    def _verify_hash(self, file_path: Path, expected_sha256: str) -> bool:
        """Verify SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest() == expected_sha256

    def download_clip_model(
        self,
        model_name: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Optional[Path]:
        """
        Download a CLIP model.

        Note: For open_clip models, they are downloaded automatically on first use.
        This method is for pre-downloading or for the original OpenAI CLIP models.

        Args:
            model_name: Model name (e.g., "ViT-B-32"). Defaults to config.
            progress_callback: Progress callback

        Returns:
            Path to downloaded model or None if failed
        """
        model_name = model_name or self.config.clip.model_name

        if model_name not in CLIP_MODELS:
            logger.warning(f"Unknown CLIP model: {model_name}. Will use open_clip auto-download.")
            return None

        model_info = CLIP_MODELS[model_name]
        dest_path = self.config.clip_dir / model_info.filename

        if self.download_file(
            url=model_info.url,
            dest_path=dest_path,
            expected_sha256=model_info.sha256,
            progress_callback=progress_callback,
        ):
            return dest_path
        return None

    def download_face_model(
        self,
        model_name: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Optional[Path]:
        """
        Download an InsightFace model pack.

        Args:
            model_name: Model name (e.g., "buffalo_l"). Defaults to config.
            progress_callback: Progress callback

        Returns:
            Path to model directory or None if failed
        """
        import zipfile

        model_name = model_name or self.config.face.detection_model

        if model_name not in INSIGHTFACE_MODELS:
            logger.error(f"Unknown InsightFace model: {model_name}")
            return None

        model_info = INSIGHTFACE_MODELS[model_name]
        model_dir = self.config.face_dir / "models" / model_name

        # Check if already extracted
        if model_dir.exists() and any(model_dir.iterdir()):
            logger.info(f"Face model already exists: {model_dir}")
            return model_dir

        zip_path = self.config.face_dir / model_info.filename

        if self.download_file(
            url=model_info.url,
            dest_path=zip_path,
            progress_callback=progress_callback,
        ):
            # Extract zip
            logger.info(f"Extracting {zip_path} to {model_dir}")
            model_dir.mkdir(parents=True, exist_ok=True)

            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(self.config.face_dir / "models")

                # Clean up zip
                zip_path.unlink()
                logger.info(f"Successfully extracted face model to {model_dir}")
                return model_dir

            except Exception as e:
                logger.error(f"Failed to extract {zip_path}: {e}")
                return None

        return None

    def download_all_models(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> dict[str, bool]:
        """
        Download all configured models.

        Args:
            progress_callback: Callback with (model_name, downloaded, total)

        Returns:
            Dict mapping model names to success status
        """
        results = {}

        # Download CLIP model
        clip_name = self.config.clip.model_name

        def clip_progress(d: int, t: int) -> None:
            if progress_callback:
                progress_callback(f"CLIP {clip_name}", d, t)

        clip_path = self.download_clip_model(progress_callback=clip_progress)
        results[f"clip:{clip_name}"] = clip_path is not None

        # Download face model
        face_name = self.config.face.detection_model

        def face_progress(d: int, t: int) -> None:
            if progress_callback:
                progress_callback(f"Face {face_name}", d, t)

        face_path = self.download_face_model(progress_callback=face_progress)
        results[f"face:{face_name}"] = face_path is not None

        return results

    def list_available_models(self) -> dict[str, list[ModelInfo]]:
        """List all available models for download."""
        return {
            "clip": list(CLIP_MODELS.values()),
            "face": list(INSIGHTFACE_MODELS.values()),
        }

    def list_downloaded_models(self) -> dict[str, list[str]]:
        """List all downloaded models."""
        downloaded = {"clip": [], "face": []}

        # Check CLIP models
        if self.config.clip_dir.exists():
            for model_name, model_info in CLIP_MODELS.items():
                model_path = self.config.clip_dir / model_info.filename
                if model_path.exists():
                    downloaded["clip"].append(model_name)

        # Check face models
        face_models_dir = self.config.face_dir / "models"
        if face_models_dir.exists():
            for model_name in INSIGHTFACE_MODELS.keys():
                model_dir = face_models_dir / model_name
                if model_dir.exists() and any(model_dir.iterdir()):
                    downloaded["face"].append(model_name)

        return downloaded

    def get_model_status(self) -> dict[str, dict]:
        """Get status of all models."""
        downloaded = self.list_downloaded_models()

        return {
            "clip": {
                "configured": self.config.clip.model_name,
                "downloaded": downloaded["clip"],
                "ready": self.config.clip.model_name in downloaded["clip"],
            },
            "face": {
                "configured": self.config.face.detection_model,
                "downloaded": downloaded["face"],
                "ready": self.config.face.detection_model in downloaded["face"],
            },
        }


def print_progress(model_name: str, downloaded: int, total: int) -> None:
    """Print download progress to stdout."""
    if total > 0:
        pct = (downloaded / total) * 100
        bar_len = 40
        filled = int(bar_len * downloaded / total)
        bar = "=" * filled + "-" * (bar_len - filled)
        print(f"\r{model_name}: [{bar}] {pct:.1f}%", end="", flush=True)
        if downloaded >= total:
            print()
    else:
        mb = downloaded / (1024 * 1024)
        print(f"\r{model_name}: {mb:.1f} MB downloaded", end="", flush=True)


def main() -> None:
    """CLI for downloading models."""
    import argparse

    parser = argparse.ArgumentParser(description="Download AI models for Photo Explorer")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download all configured models",
    )
    parser.add_argument(
        "--clip",
        type=str,
        help="Download specific CLIP model (e.g., ViT-B-32, ViT-L-14)",
    )
    parser.add_argument(
        "--face",
        type=str,
        help="Download specific face model (e.g., buffalo_l, buffalo_s)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available models",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show model download status",
    )

    args = parser.parse_args()

    with ModelDownloader() as downloader:
        if args.list:
            print("\nAvailable Models:")
            print("=" * 50)
            available = downloader.list_available_models()

            print("\nCLIP Models:")
            for model in available["clip"]:
                print(f"  - {model.name} ({model.size_mb:.0f} MB)")

            print("\nFace Models:")
            for model in available["face"]:
                print(f"  - {model.name} ({model.size_mb:.0f} MB)")
            return

        if args.status:
            print("\nModel Status:")
            print("=" * 50)
            status = downloader.get_model_status()

            print("\nCLIP:")
            print(f"  Configured: {status['clip']['configured']}")
            print(f"  Downloaded: {', '.join(status['clip']['downloaded']) or 'None'}")
            print(f"  Ready: {'Yes' if status['clip']['ready'] else 'No'}")

            print("\nFace Detection:")
            print(f"  Configured: {status['face']['configured']}")
            print(f"  Downloaded: {', '.join(status['face']['downloaded']) or 'None'}")
            print(f"  Ready: {'Yes' if status['face']['ready'] else 'No'}")
            return

        if args.all:
            print("\nDownloading all configured models...")
            results = downloader.download_all_models(progress_callback=print_progress)
            print("\nResults:")
            for name, success in results.items():
                status = "OK" if success else "FAILED"
                print(f"  {name}: {status}")
            return

        if args.clip:
            print(f"\nDownloading CLIP model: {args.clip}")

            def progress(d: int, t: int) -> None:
                print_progress(args.clip, d, t)

            path = downloader.download_clip_model(args.clip, progress_callback=progress)
            if path:
                print(f"Downloaded to: {path}")
            else:
                print("Download failed!")
                sys.exit(1)
            return

        if args.face:
            print(f"\nDownloading face model: {args.face}")

            def progress(d: int, t: int) -> None:
                print_progress(args.face, d, t)

            path = downloader.download_face_model(args.face, progress_callback=progress)
            if path:
                print(f"Downloaded to: {path}")
            else:
                print("Download failed!")
                sys.exit(1)
            return

        # Default: show help
        parser.print_help()


if __name__ == "__main__":
    main()
