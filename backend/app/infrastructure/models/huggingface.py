"""Hugging Face model browser and downloader."""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from huggingface_hub import (
    HfApi,
    hf_hub_download,
    list_repo_files,
    model_info as get_model_info,
    snapshot_download,
)
from huggingface_hub.utils import RepositoryNotFoundError, RevisionNotFoundError

from .config import ModelConfig, get_model_config

logger = logging.getLogger(__name__)


class ModelTask(str, Enum):
    """Supported model tasks for Photo Explorer."""

    IMAGE_EMBEDDING = "image-embedding"
    TEXT_EMBEDDING = "text-embedding"
    ZERO_SHOT_IMAGE = "zero-shot-image-classification"
    FACE_DETECTION = "face-detection"
    OBJECT_DETECTION = "object-detection"
    IMAGE_SEGMENTATION = "image-segmentation"


# Recommended models for each task
RECOMMENDED_MODELS: dict[ModelTask, list[str]] = {
    ModelTask.IMAGE_EMBEDDING: [
        "openai/clip-vit-base-patch32",
        "openai/clip-vit-base-patch16",
        "openai/clip-vit-large-patch14",
        "laion/CLIP-ViT-B-32-laion2B-s34B-b79K",
        "laion/CLIP-ViT-L-14-laion2B-s32B-b82K",
        "laion/CLIP-ViT-H-14-laion2B-s32B-b79K",
    ],
    ModelTask.ZERO_SHOT_IMAGE: [
        "openai/clip-vit-base-patch32",
        "openai/clip-vit-large-patch14-336",
        "google/siglip-base-patch16-224",
        "google/siglip-large-patch16-256",
    ],
    ModelTask.FACE_DETECTION: [
        "deepinsight/buffalo_l",
        "deepinsight/buffalo_m",
        "deepinsight/buffalo_s",
    ],
    ModelTask.OBJECT_DETECTION: [
        "facebook/detr-resnet-50",
        "facebook/detr-resnet-101",
        "hustvl/yolos-tiny",
    ],
}


@dataclass
class HFModelInfo:
    """Information about a Hugging Face model."""

    model_id: str
    author: str
    model_name: str
    pipeline_tag: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    downloads: int = 0
    likes: int = 0
    last_modified: Optional[datetime] = None
    library_name: Optional[str] = None
    size_bytes: Optional[int] = None
    sha: Optional[str] = None
    private: bool = False
    gated: bool = False
    files: list[str] = field(default_factory=list)
    siblings: list[dict] = field(default_factory=list)

    @property
    def size_mb(self) -> Optional[float]:
        """Get size in megabytes."""
        if self.size_bytes:
            return self.size_bytes / (1024 * 1024)
        return None

    @property
    def is_clip(self) -> bool:
        """Check if this is a CLIP-style model."""
        return "clip" in self.model_id.lower() or "clip" in self.tags

    @property
    def is_transformers(self) -> bool:
        """Check if this uses the transformers library."""
        return self.library_name == "transformers"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "model_id": self.model_id,
            "author": self.author,
            "model_name": self.model_name,
            "pipeline_tag": self.pipeline_tag,
            "tags": self.tags,
            "downloads": self.downloads,
            "likes": self.likes,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "library_name": self.library_name,
            "size_mb": self.size_mb,
            "private": self.private,
            "gated": self.gated,
            "files": self.files,
        }


@dataclass
class DownloadProgress:
    """Progress information for a download."""

    model_id: str
    status: str  # "pending", "downloading", "completed", "failed"
    progress: float  # 0.0 to 1.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    current_file: Optional[str] = None
    error: Optional[str] = None


class HuggingFaceModelBrowser:
    """Browser and downloader for Hugging Face models."""

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or get_model_config()
        self._api = HfApi()
        self._downloads: dict[str, DownloadProgress] = {}

    @property
    def models_dir(self) -> Path:
        """Get the models directory."""
        return self.config.models_dir / "huggingface"

    def _ensure_models_dir(self) -> Path:
        """Ensure models directory exists."""
        self.models_dir.mkdir(parents=True, exist_ok=True)
        return self.models_dir

    async def search_models(
        self,
        query: str,
        task: Optional[ModelTask] = None,
        limit: int = 20,
        sort: str = "downloads",
    ) -> list[HFModelInfo]:
        """
        Search for models on Hugging Face.

        Args:
            query: Search query
            task: Filter by task type
            limit: Maximum results to return
            sort: Sort by (downloads, likes, lastModified)

        Returns:
            List of matching models
        """
        try:
            # Run in thread pool since HfApi is synchronous
            loop = asyncio.get_event_loop()

            # Build filter
            filter_str = None
            if task:
                filter_str = task.value

            models = await loop.run_in_executor(
                None,
                lambda: list(self._api.list_models(
                    search=query,
                    filter=filter_str,
                    sort=sort,
                    direction=-1,
                    limit=limit,
                ))
            )

            return [self._parse_model_info(m) for m in models]

        except Exception as e:
            logger.error(f"Failed to search models: {e}")
            return []

    async def get_model_info(self, model_id: str) -> Optional[HFModelInfo]:
        """
        Get detailed information about a model.

        Args:
            model_id: Model ID (e.g., "openai/clip-vit-base-patch32")

        Returns:
            Model information or None if not found
        """
        try:
            loop = asyncio.get_event_loop()

            info = await loop.run_in_executor(
                None,
                lambda: get_model_info(model_id)
            )

            # Get file list
            files = await loop.run_in_executor(
                None,
                lambda: list_repo_files(model_id)
            )

            model_info = self._parse_model_info(info)
            model_info.files = list(files)

            # Calculate total size from siblings
            if hasattr(info, "siblings") and info.siblings:
                total_size = sum(
                    s.size for s in info.siblings
                    if hasattr(s, "size") and s.size
                )
                model_info.size_bytes = total_size

            return model_info

        except RepositoryNotFoundError:
            logger.warning(f"Model not found: {model_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return None

    def _parse_model_info(self, info: Any) -> HFModelInfo:
        """Parse HuggingFace model info into our dataclass."""
        model_id = info.id if hasattr(info, "id") else str(info.modelId)
        parts = model_id.split("/", 1)
        author = parts[0] if len(parts) > 1 else ""
        model_name = parts[1] if len(parts) > 1 else parts[0]

        return HFModelInfo(
            model_id=model_id,
            author=author,
            model_name=model_name,
            pipeline_tag=getattr(info, "pipeline_tag", None),
            tags=list(getattr(info, "tags", [])),
            downloads=getattr(info, "downloads", 0) or 0,
            likes=getattr(info, "likes", 0) or 0,
            last_modified=getattr(info, "lastModified", None),
            library_name=getattr(info, "library_name", None),
            sha=getattr(info, "sha", None),
            private=getattr(info, "private", False),
            gated=getattr(info, "gated", False) if hasattr(info, "gated") else False,
        )

    async def download_model(
        self,
        model_id: str,
        revision: str = "main",
        allow_patterns: Optional[list[str]] = None,
        ignore_patterns: Optional[list[str]] = None,
    ) -> Optional[Path]:
        """
        Download a model from Hugging Face.

        Args:
            model_id: Model ID (e.g., "openai/clip-vit-base-patch32")
            revision: Git revision (branch, tag, or commit)
            allow_patterns: Only download files matching these patterns
            ignore_patterns: Skip files matching these patterns

        Returns:
            Path to downloaded model directory or None if failed
        """
        self._ensure_models_dir()

        # Initialize progress tracking
        self._downloads[model_id] = DownloadProgress(
            model_id=model_id,
            status="downloading",
            progress=0.0,
        )

        try:
            loop = asyncio.get_event_loop()

            # Default ignore patterns for large unnecessary files
            if ignore_patterns is None:
                ignore_patterns = [
                    "*.msgpack",
                    "*.h5",
                    "*.ot",
                    "*.tflite",
                    "*.onnx",  # Unless specifically needed
                    "flax_model.msgpack",
                    "tf_model.h5",
                ]

            # For CLIP models, we mainly need .bin and config files
            if allow_patterns is None and "clip" in model_id.lower():
                allow_patterns = [
                    "*.json",
                    "*.txt",
                    "*.bin",
                    "*.safetensors",
                    "tokenizer*",
                    "preprocessor*",
                ]

            local_dir = self.models_dir / model_id.replace("/", "--")

            # Download snapshot
            path = await loop.run_in_executor(
                None,
                lambda: snapshot_download(
                    repo_id=model_id,
                    revision=revision,
                    local_dir=str(local_dir),
                    allow_patterns=allow_patterns,
                    ignore_patterns=ignore_patterns,
                )
            )

            self._downloads[model_id] = DownloadProgress(
                model_id=model_id,
                status="completed",
                progress=1.0,
            )

            logger.info(f"Successfully downloaded model: {model_id}")
            return Path(path)

        except Exception as e:
            logger.error(f"Failed to download model {model_id}: {e}")
            self._downloads[model_id] = DownloadProgress(
                model_id=model_id,
                status="failed",
                progress=0.0,
                error=str(e),
            )
            return None

    async def download_file(
        self,
        model_id: str,
        filename: str,
        revision: str = "main",
    ) -> Optional[Path]:
        """
        Download a specific file from a model repository.

        Args:
            model_id: Model ID
            filename: File to download
            revision: Git revision

        Returns:
            Path to downloaded file or None if failed
        """
        self._ensure_models_dir()

        try:
            loop = asyncio.get_event_loop()

            local_dir = self.models_dir / model_id.replace("/", "--")

            path = await loop.run_in_executor(
                None,
                lambda: hf_hub_download(
                    repo_id=model_id,
                    filename=filename,
                    revision=revision,
                    local_dir=str(local_dir),
                )
            )

            return Path(path)

        except Exception as e:
            logger.error(f"Failed to download {filename} from {model_id}: {e}")
            return None

    def get_download_progress(self, model_id: str) -> Optional[DownloadProgress]:
        """Get the download progress for a model."""
        return self._downloads.get(model_id)

    def list_downloaded_models(self) -> list[str]:
        """List all downloaded model IDs."""
        downloaded = []
        if self.models_dir.exists():
            for path in self.models_dir.iterdir():
                if path.is_dir():
                    # Convert directory name back to model ID
                    model_id = path.name.replace("--", "/")
                    downloaded.append(model_id)
        return downloaded

    def get_model_path(self, model_id: str) -> Optional[Path]:
        """Get the local path for a downloaded model."""
        local_dir = self.models_dir / model_id.replace("/", "--")
        if local_dir.exists():
            return local_dir
        return None

    def is_model_downloaded(self, model_id: str) -> bool:
        """Check if a model is downloaded."""
        return self.get_model_path(model_id) is not None

    async def delete_model(self, model_id: str) -> bool:
        """Delete a downloaded model."""
        import shutil

        local_dir = self.models_dir / model_id.replace("/", "--")
        if local_dir.exists():
            try:
                shutil.rmtree(local_dir)
                logger.info(f"Deleted model: {model_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete model {model_id}: {e}")
                return False
        return False

    def get_recommended_models(self, task: Optional[ModelTask] = None) -> dict[str, list[str]]:
        """Get recommended models, optionally filtered by task."""
        if task:
            return {task.value: RECOMMENDED_MODELS.get(task, [])}
        return {t.value: models for t, models in RECOMMENDED_MODELS.items()}


# Singleton instance
_browser: Optional[HuggingFaceModelBrowser] = None


def get_model_browser() -> HuggingFaceModelBrowser:
    """Get the global model browser instance."""
    global _browser
    if _browser is None:
        _browser = HuggingFaceModelBrowser()
    return _browser


# CLI interface
def main() -> None:
    """CLI for Hugging Face model operations."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Hugging Face Model Browser")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for models")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--task", help="Filter by task")
    search_parser.add_argument("--limit", type=int, default=10, help="Max results")

    # Info command
    info_parser = subparsers.add_parser("info", help="Get model info")
    info_parser.add_argument("model_id", help="Model ID (e.g., openai/clip-vit-base-patch32)")

    # Download command
    download_parser = subparsers.add_parser("download", help="Download a model")
    download_parser.add_argument("model_id", help="Model ID to download")

    # List command
    subparsers.add_parser("list", help="List downloaded models")

    # Recommended command
    rec_parser = subparsers.add_parser("recommended", help="Show recommended models")
    rec_parser.add_argument("--task", help="Filter by task")

    args = parser.parse_args()

    browser = get_model_browser()

    if args.command == "search":
        task = ModelTask(args.task) if args.task else None
        results = asyncio.run(browser.search_models(args.query, task=task, limit=args.limit))

        print(f"\nFound {len(results)} models:\n")
        for model in results:
            print(f"  {model.model_id}")
            print(f"    Downloads: {model.downloads:,}  Likes: {model.likes}")
            if model.pipeline_tag:
                print(f"    Task: {model.pipeline_tag}")
            print()

    elif args.command == "info":
        info = asyncio.run(browser.get_model_info(args.model_id))

        if info:
            print(f"\nModel: {info.model_id}")
            print(f"Author: {info.author}")
            print(f"Downloads: {info.downloads:,}")
            print(f"Likes: {info.likes}")
            if info.pipeline_tag:
                print(f"Task: {info.pipeline_tag}")
            if info.library_name:
                print(f"Library: {info.library_name}")
            if info.size_mb:
                print(f"Size: {info.size_mb:.1f} MB")
            if info.tags:
                print(f"Tags: {', '.join(info.tags[:10])}")
            if info.files:
                print(f"\nFiles ({len(info.files)}):")
                for f in info.files[:20]:
                    print(f"  - {f}")
                if len(info.files) > 20:
                    print(f"  ... and {len(info.files) - 20} more")
            print()
        else:
            print(f"Model not found: {args.model_id}")

    elif args.command == "download":
        print(f"Downloading {args.model_id}...")
        path = asyncio.run(browser.download_model(args.model_id))

        if path:
            print(f"Downloaded to: {path}")
        else:
            print("Download failed!")

    elif args.command == "list":
        downloaded = browser.list_downloaded_models()

        if downloaded:
            print("\nDownloaded models:")
            for model_id in downloaded:
                print(f"  - {model_id}")
        else:
            print("No models downloaded yet.")

    elif args.command == "recommended":
        task = ModelTask(args.task) if args.task else None
        recommended = browser.get_recommended_models(task)

        print("\nRecommended models:")
        for task_name, models in recommended.items():
            print(f"\n  {task_name}:")
            for model in models:
                downloaded = browser.is_model_downloaded(model)
                status = " [downloaded]" if downloaded else ""
                print(f"    - {model}{status}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
