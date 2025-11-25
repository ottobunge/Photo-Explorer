"""Model configuration and paths."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CLIPConfig:
    """CLIP model configuration."""

    # Model name from open_clip (e.g., "ViT-B-32", "ViT-L-14")
    # Default to ViT-L-14 for better quality (synced with app/config.py)
    model_name: str = "ViT-L-14"

    # Pretrained weights (e.g., "openai", "laion2b_s34b_b79k")
    pretrained: str = "openai"

    # Embedding dimension (depends on model)
    embedding_dim: int = 768

    # Device for inference ("cuda", "cpu", "mps")
    device: str = "cuda"

    @property
    def model_id(self) -> str:
        """Get unique identifier for this model configuration."""
        return f"{self.model_name}_{self.pretrained}"


@dataclass
class FaceConfig:
    """Face detection/recognition model configuration."""

    # InsightFace model name
    detection_model: str = "buffalo_l"

    # Recognition model for embeddings
    recognition_model: str = "arcface"

    # Minimum face size to detect (pixels)
    min_face_size: int = 20

    # Detection confidence threshold
    det_thresh: float = 0.5

    # Device for inference
    device: str = "cuda"


@dataclass
class ModelConfig:
    """Global model configuration."""

    # Base directory for model storage
    models_dir: Path = field(
        default_factory=lambda: Path.home() / ".cache" / "photo-explorer" / "models"
    )

    # CLIP configuration
    clip: CLIPConfig = field(default_factory=CLIPConfig)

    # Face detection/recognition configuration
    face: FaceConfig = field(default_factory=FaceConfig)

    def __post_init__(self) -> None:
        """Ensure directories exist."""
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.clip_dir.mkdir(parents=True, exist_ok=True)
        self.face_dir.mkdir(parents=True, exist_ok=True)

    @property
    def clip_dir(self) -> Path:
        """Directory for CLIP models."""
        return self.models_dir / "clip"

    @property
    def face_dir(self) -> Path:
        """Directory for face models."""
        return self.models_dir / "insightface"

    @classmethod
    def from_env(cls) -> "ModelConfig":
        """Create configuration from environment variables."""
        models_dir = Path(
            os.environ.get(
                "PHOTO_EXPLORER_MODELS_DIR",
                str(Path.home() / ".cache" / "photo-explorer" / "models"),
            )
        )

        clip_model = os.environ.get("PHOTO_EXPLORER_CLIP_MODEL", "ViT-L-14")
        clip_pretrained = os.environ.get("PHOTO_EXPLORER_CLIP_PRETRAINED", "openai")
        device = os.environ.get("PHOTO_EXPLORER_DEVICE", "cuda")

        # Map model names to embedding dimensions
        embedding_dims = {
            "ViT-B-32": 512,
            "ViT-B-16": 512,
            "ViT-L-14": 768,
            "ViT-L-14-336": 768,
            "ViT-H-14": 1024,
            "ViT-g-14": 1024,
        }

        return cls(
            models_dir=models_dir,
            clip=CLIPConfig(
                model_name=clip_model,
                pretrained=clip_pretrained,
                embedding_dim=embedding_dims.get(clip_model, 512),
                device=device,
            ),
            face=FaceConfig(
                device=device,
            ),
        )


# Singleton instance
_config: Optional[ModelConfig] = None


def get_model_config() -> ModelConfig:
    """Get the global model configuration."""
    global _config
    if _config is None:
        _config = ModelConfig.from_env()
    return _config


def reset_model_config() -> None:
    """Reset the global model configuration (for testing)."""
    global _config
    _config = None
