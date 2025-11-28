"""Unit tests for ML Services adapter."""

from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
from PIL import Image

from app.adapters.outbound.ml.ml_services import MLServicesAdapter
from app.application.ports.outbound.ml_services import DetectedFace
from app.domain.value_objects import BoundingBox, Embedding
from app.infrastructure.models.config import CLIPConfig, FaceConfig


@pytest.fixture
def sample_image():
    """Create a sample PIL Image for testing."""
    # Create a simple 100x100 RGB image
    img = Image.new("RGB", (100, 100), color="red")
    return img


@pytest.fixture
def sample_image_bytes(sample_image):
    """Convert sample image to bytes."""
    buffer = BytesIO()
    sample_image.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def mock_clip_config():
    """Create a mock CLIP configuration."""
    return CLIPConfig(
        model_name="ViT-B-32",
        pretrained="openai",
    )


@pytest.fixture
def mock_face_config():
    """Create a mock Face configuration."""
    return FaceConfig()


class TestMLServicesInitialization:
    """Tests for MLServicesAdapter initialization."""

    def test_init_with_default_config(self):
        """When initializing without config, it should use defaults from settings."""
        with patch("app.adapters.outbound.ml.ml_services.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                clip_model_name="ViT-B-32",
                clip_pretrained="openai",
                thumbnail_size=(512, 512),
                face_crop_size=(224, 224),
            )

            ml_services = MLServicesAdapter()

            assert ml_services._clip_config is not None
            assert ml_services._face_config is not None
            # Models should not be loaded yet (lazy loading)
            assert ml_services._clip_loader is None
            assert ml_services._face_loader is None

    def test_init_with_custom_config(self, mock_clip_config, mock_face_config):
        """When initializing with custom config, it should be used."""
        with patch("app.adapters.outbound.ml.ml_services.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                thumbnail_size=(512, 512),
                face_crop_size=(224, 224),
            )

            ml_services = MLServicesAdapter(
                clip_config=mock_clip_config,
                face_config=mock_face_config,
            )

            assert ml_services._clip_config == mock_clip_config
            assert ml_services._face_config == mock_face_config


class TestMLServicesLazyLoading:
    """Tests for lazy loading of ML models."""

    @patch("app.adapters.outbound.ml.ml_services.CLIPModelLoader")
    def test_clip_loader_lazy_loads_on_first_access(self, mock_clip_loader_class):
        """When accessing clip_loader first time, it should be loaded."""
        with patch("app.adapters.outbound.ml.ml_services.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                clip_model_name="ViT-B-32",
                clip_pretrained="openai",
                thumbnail_size=(512, 512),
                face_crop_size=(224, 224),
            )

            ml_services = MLServicesAdapter()
            mock_loader_instance = MagicMock()
            mock_clip_loader_class.return_value = mock_loader_instance

            # First access should trigger loading
            loader = ml_services.clip_loader

            assert loader == mock_loader_instance
            mock_clip_loader_class.assert_called_once()

    @patch("app.adapters.outbound.ml.ml_services.CLIPModelLoader")
    def test_clip_loader_not_reloaded_on_subsequent_access(self, mock_clip_loader_class):
        """When accessing clip_loader multiple times, it should load once."""
        with patch("app.adapters.outbound.ml.ml_services.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                clip_model_name="ViT-B-32",
                clip_pretrained="openai",
                thumbnail_size=(512, 512),
                face_crop_size=(224, 224),
            )

            ml_services = MLServicesAdapter()
            mock_loader_instance = MagicMock()
            mock_clip_loader_class.return_value = mock_loader_instance

            # Access multiple times
            loader1 = ml_services.clip_loader
            loader2 = ml_services.clip_loader

            assert loader1 is loader2
            # Should only be called once due to lazy loading
            assert mock_clip_loader_class.call_count == 1

    @patch("app.adapters.outbound.ml.ml_services.FaceModelLoader")
    def test_face_loader_lazy_loads_on_first_access(self, mock_face_loader_class):
        """When accessing face_loader first time, it should be loaded."""
        with patch("app.adapters.outbound.ml.ml_services.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                clip_model_name="ViT-B-32",
                clip_pretrained="openai",
                thumbnail_size=(512, 512),
                face_crop_size=(224, 224),
            )

            ml_services = MLServicesAdapter()
            mock_loader_instance = MagicMock()
            mock_face_loader_class.return_value = mock_loader_instance

            # First access should trigger loading
            loader = ml_services.face_loader

            assert loader == mock_loader_instance
            mock_face_loader_class.assert_called_once()


class TestMLServicesTextEncoding:
    """Tests for text encoding functionality."""

    @pytest.mark.asyncio
    @patch("app.adapters.outbound.ml.ml_services.CLIPModelLoader")
    async def test_encode_text_returns_embedding(self, mock_clip_loader_class):
        """When encoding text, it should return an Embedding."""
        with patch("app.adapters.outbound.ml.ml_services.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                clip_model_name="ViT-B-32",
                clip_pretrained="openai",
                thumbnail_size=(512, 512),
                face_crop_size=(224, 224),
            )

            ml_services = MLServicesAdapter()

            # Mock the CLIP loader to return a fake embedding (numpy array)
            mock_loader = MagicMock()
            mock_loader.encode_text.return_value = np.array([0.1, 0.2, 0.3, 0.4])
            mock_clip_loader_class.return_value = mock_loader

            embedding = await ml_services.encode_text("a beautiful sunset over the ocean")

            assert isinstance(embedding, Embedding)
            assert list(embedding.values) == [0.1, 0.2, 0.3, 0.4]
            mock_loader.encode_text.assert_called_once_with("a beautiful sunset over the ocean")

    @pytest.mark.asyncio
    @patch("app.adapters.outbound.ml.ml_services.CLIPModelLoader")
    async def test_encode_text_handles_empty_string(self, mock_clip_loader_class):
        """When encoding empty text, it should handle gracefully."""
        with patch("app.adapters.outbound.ml.ml_services.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                clip_model_name="ViT-B-32",
                clip_pretrained="openai",
                thumbnail_size=(512, 512),
                face_crop_size=(224, 224),
            )

            ml_services = MLServicesAdapter()

            mock_loader = MagicMock()
            mock_loader.encode_text.return_value = np.array([0.0] * 512)
            mock_clip_loader_class.return_value = mock_loader

            embedding = await ml_services.encode_text("")

            assert isinstance(embedding, Embedding)
            mock_loader.encode_text.assert_called_once_with("")


class TestMLServicesImageEncoding:
    """Tests for image encoding functionality."""

    @pytest.mark.asyncio
    @patch("app.adapters.outbound.ml.ml_services.CLIPModelLoader")
    async def test_encode_image_from_bytes_returns_embedding(
        self, mock_clip_loader_class, sample_image_bytes
    ):
        """When encoding image from bytes, it should return an Embedding."""
        with patch("app.adapters.outbound.ml.ml_services.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                clip_model_name="ViT-B-32",
                clip_pretrained="openai",
                thumbnail_size=(512, 512),
                face_crop_size=(224, 224),
            )

            ml_services = MLServicesAdapter()

            mock_loader = MagicMock()
            mock_loader.encode_image.return_value = np.array([0.5, 0.6, 0.7, 0.8])
            mock_clip_loader_class.return_value = mock_loader

            embedding = await ml_services.encode_image(sample_image_bytes)

            assert isinstance(embedding, Embedding)
            assert list(embedding.values) == [0.5, 0.6, 0.7, 0.8]
            # Verify encode_image was called with a PIL Image
            mock_loader.encode_image.assert_called_once()
            call_args = mock_loader.encode_image.call_args[0]
            assert isinstance(call_args[0], Image.Image)



class TestMLServicesFaceDetection:
    """Tests for face detection functionality."""

    @pytest.mark.asyncio
    @patch("app.adapters.outbound.ml.ml_services.FaceModelLoader")
    async def test_detect_faces_returns_list_of_detected_faces(
        self, mock_face_loader_class, sample_image_bytes
    ):
        """When detecting faces, it should return list of DetectedFace."""
        with patch("app.adapters.outbound.ml.ml_services.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                clip_model_name="ViT-B-32",
                clip_pretrained="openai",
                thumbnail_size=(512, 512),
                face_crop_size=(224, 224),
            )

            ml_services = MLServicesAdapter()

            # Mock face detection to return faces with bboxes
            # The face loader returns objects with .bbox (tuple), .embedding (numpy array), and .confidence attributes
            mock_face = Mock()
            mock_face.bbox = (10, 20, 60, 80)  # x1, y1, x2, y2
            mock_face.embedding = np.array([0.1] * 512)
            mock_face.confidence = 0.95

            mock_loader = MagicMock()
            mock_loader.detect_faces.return_value = [mock_face]
            mock_face_loader_class.return_value = mock_loader

            faces = await ml_services.detect_faces(sample_image_bytes)

            assert len(faces) == 1
            assert isinstance(faces[0], DetectedFace)
            assert isinstance(faces[0].bbox, BoundingBox)
            assert faces[0].bbox.x == 10
            assert faces[0].bbox.y == 20
            assert faces[0].bbox.width == 50
            assert faces[0].bbox.height == 60
            assert faces[0].detection_confidence == 0.95
            assert faces[0].quality_score == 0.95
            assert isinstance(faces[0].embedding, Embedding)

    @pytest.mark.asyncio
    @patch("app.adapters.outbound.ml.ml_services.FaceModelLoader")
    async def test_detect_faces_with_no_faces_returns_empty_list(
        self, mock_face_loader_class, sample_image_bytes
    ):
        """When no faces detected, it should return empty list."""
        with patch("app.adapters.outbound.ml.ml_services.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                clip_model_name="ViT-B-32",
                clip_pretrained="openai",
                thumbnail_size=(512, 512),
                face_crop_size=(224, 224),
            )

            ml_services = MLServicesAdapter()

            mock_loader = MagicMock()
            mock_loader.detect_faces.return_value = []
            mock_face_loader_class.return_value = mock_loader

            faces = await ml_services.detect_faces(sample_image_bytes)

            assert faces == []


class TestMLServicesSingletonPattern:
    """Tests for singleton pattern in get_ml_services."""

    def test_get_ml_services_returns_singleton(self):
        """When calling get_ml_services multiple times, should return same instance."""
        # Import the module-level function
        # Reset global singleton for test isolation
        import app.adapters.outbound.ml.ml_services as ml_module
        from app.adapters.outbound.ml.ml_services import (
            get_ml_services,
        )

        ml_module._ml_services_instance = None

        with patch("app.adapters.outbound.ml.ml_services.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                clip_model_name="ViT-B-32",
                clip_pretrained="openai",
                thumbnail_size=(512, 512),
                face_crop_size=(224, 224),
            )

            instance1 = get_ml_services()
            instance2 = get_ml_services()

            assert instance1 is instance2

        # Clean up
        ml_module._ml_services_instance = None


class TestMLServicesErrorHandling:
    """Tests for error handling in ML services."""

    @pytest.mark.asyncio
    @patch("app.adapters.outbound.ml.ml_services.CLIPModelLoader")
    async def test_encode_text_propagates_model_errors(self, mock_clip_loader_class):
        """When model raises error, it should be propagated."""
        with patch("app.adapters.outbound.ml.ml_services.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                clip_model_name="ViT-B-32",
                clip_pretrained="openai",
                thumbnail_size=(512, 512),
                face_crop_size=(224, 224),
            )

            ml_services = MLServicesAdapter()

            mock_loader = MagicMock()
            mock_loader.encode_text.side_effect = RuntimeError("Model inference failed")
            mock_clip_loader_class.return_value = mock_loader

            with pytest.raises(RuntimeError) as exc:
                await ml_services.encode_text("test")

            assert "Model inference failed" in str(exc.value)

    def test_encode_image_from_bytes_handles_invalid_image(self):
        """When image bytes are invalid, it should raise error."""
        with patch("app.adapters.outbound.ml.ml_services.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                clip_model_name="ViT-B-32",
                clip_pretrained="openai",
                thumbnail_size=(512, 512),
                face_crop_size=(224, 224),
            )

            ml_services = MLServicesAdapter()

            invalid_bytes = b"not an image"

            with pytest.raises(Exception):  # PIL raises various exceptions
                ml_services.encode_image_from_bytes(invalid_bytes)
