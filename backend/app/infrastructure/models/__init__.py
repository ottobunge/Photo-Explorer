"""Model management infrastructure."""

from .config import ModelConfig, get_model_config
from .downloader import ModelDownloader
from .clip import CLIPModelLoader
from .faces import FaceModelLoader
from .huggingface import (
    HuggingFaceModelBrowser,
    HFModelInfo,
    ModelTask,
    get_model_browser,
    RECOMMENDED_MODELS,
)
from .vision import (
    VisionModelType,
    VisionModelLoader,
    BLIP2ModelLoader,
    MoondreamModelLoader,
    ObjectDetectionLoader,
    SceneClassificationLoader,
    ImageCaption,
    DetectedObject,
    SceneClassification,
    get_vision_model,
    get_object_detector,
    get_scene_classifier,
)

__all__ = [
    # Config
    "ModelConfig",
    "get_model_config",
    "ModelDownloader",
    # CLIP
    "CLIPModelLoader",
    # Faces
    "FaceModelLoader",
    # HuggingFace
    "HuggingFaceModelBrowser",
    "HFModelInfo",
    "ModelTask",
    "get_model_browser",
    "RECOMMENDED_MODELS",
    # Vision
    "VisionModelType",
    "VisionModelLoader",
    "BLIP2ModelLoader",
    "MoondreamModelLoader",
    "ObjectDetectionLoader",
    "SceneClassificationLoader",
    "ImageCaption",
    "DetectedObject",
    "SceneClassification",
    "get_vision_model",
    "get_object_detector",
    "get_scene_classifier",
]
