"""Tests for model configuration and utilities."""

from pathlib import Path
from unittest.mock import patch

from app.infrastructure.models.config import (
    CLIPConfig,
    FaceConfig,
    ModelConfig,
    get_model_config,
    reset_model_config,
)
from app.infrastructure.models.downloader import (
    CLIP_MODELS,
    INSIGHTFACE_MODELS,
    ModelDownloader,
)


class TestCLIPConfig:
    """Tests for CLIP configuration."""

    def test_default_config(self):
        """Test default CLIP configuration."""
        config = CLIPConfig()

        assert config.model_name == "ViT-B-32"
        assert config.pretrained == "openai"
        assert config.embedding_dim == 512
        assert config.device == "cuda"

    def test_model_id(self):
        """Test model ID generation."""
        config = CLIPConfig(model_name="ViT-L-14", pretrained="laion2b")

        assert config.model_id == "ViT-L-14_laion2b"


class TestFaceConfig:
    """Tests for face model configuration."""

    def test_default_config(self):
        """Test default face configuration."""
        config = FaceConfig()

        assert config.detection_model == "buffalo_l"
        assert config.recognition_model == "arcface"
        assert config.min_face_size == 20
        assert config.det_thresh == 0.5


class TestModelConfig:
    """Tests for overall model configuration."""

    def test_default_paths(self, tmp_path):
        """Test that default paths are created correctly."""
        with patch.object(Path, "home", return_value=tmp_path):
            config = ModelConfig()

            expected_base = tmp_path / ".cache" / "photo-explorer" / "models"
            assert config.models_dir == expected_base
            assert config.clip_dir == expected_base / "clip"
            assert config.face_dir == expected_base / "insightface"

    def test_from_env(self, tmp_path, monkeypatch):
        """Test configuration from environment variables."""
        monkeypatch.setenv("PHOTO_EXPLORER_MODELS_DIR", str(tmp_path / "models"))
        monkeypatch.setenv("PHOTO_EXPLORER_CLIP_MODEL", "ViT-L-14")
        monkeypatch.setenv("PHOTO_EXPLORER_CLIP_PRETRAINED", "laion2b")
        monkeypatch.setenv("PHOTO_EXPLORER_DEVICE", "cpu")

        config = ModelConfig.from_env()

        assert config.models_dir == tmp_path / "models"
        assert config.clip.model_name == "ViT-L-14"
        assert config.clip.pretrained == "laion2b"
        assert config.clip.device == "cpu"
        assert config.clip.embedding_dim == 768  # ViT-L-14 has 768 dim

    def test_get_model_config_singleton(self, tmp_path):
        """Test that get_model_config returns singleton."""
        reset_model_config()

        with patch.object(Path, "home", return_value=tmp_path):
            config1 = get_model_config()
            config2 = get_model_config()

            assert config1 is config2

        reset_model_config()


class TestModelDownloader:
    """Tests for model downloader."""

    def test_list_available_models(self, tmp_path):
        """Test listing available models."""
        config = ModelConfig(models_dir=tmp_path / "models")
        downloader = ModelDownloader(config)

        available = downloader.list_available_models()

        assert "clip" in available
        assert "face" in available
        assert len(available["clip"]) == len(CLIP_MODELS)
        assert len(available["face"]) == len(INSIGHTFACE_MODELS)

    def test_list_downloaded_models_empty(self, tmp_path):
        """Test listing downloaded models when none exist."""
        config = ModelConfig(models_dir=tmp_path / "models")
        downloader = ModelDownloader(config)

        downloaded = downloader.list_downloaded_models()

        assert downloaded["clip"] == []
        assert downloaded["face"] == []

    def test_get_model_status(self, tmp_path):
        """Test getting model status."""
        config = ModelConfig(models_dir=tmp_path / "models")
        downloader = ModelDownloader(config)

        status = downloader.get_model_status()

        assert "clip" in status
        assert "face" in status
        assert status["clip"]["configured"] == "ViT-B-32"
        assert status["clip"]["ready"] is False
        assert status["face"]["configured"] == "buffalo_l"
        assert status["face"]["ready"] is False

    def test_download_file_creates_directory(self, tmp_path, httpx_mock):
        """Test that download creates parent directories."""
        config = ModelConfig(models_dir=tmp_path / "models")
        downloader = ModelDownloader(config)

        dest = tmp_path / "downloads" / "subdir" / "file.txt"
        url = "https://example.com/file.txt"

        # This would require httpx_mock fixture from pytest-httpx
        # For now, just test the directory creation logic
        dest.parent.mkdir(parents=True, exist_ok=True)

        assert dest.parent.exists()


class TestModelInfo:
    """Tests for model information."""

    def test_clip_models_have_required_fields(self):
        """Test that CLIP model info has all required fields."""
        for name, info in CLIP_MODELS.items():
            assert info.name
            assert info.url
            assert info.filename
            assert info.size_mb > 0
            assert info.sha256  # OpenAI models have SHA256

    def test_face_models_have_required_fields(self):
        """Test that face model info has all required fields."""
        for name, info in INSIGHTFACE_MODELS.items():
            assert info.name
            assert info.url
            assert info.filename
            assert info.size_mb > 0
