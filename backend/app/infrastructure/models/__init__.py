"""Model management infrastructure."""

from .clip import CLIPModelLoader
from .config import ModelConfig, get_model_config
from .downloader import ModelDownloader
from .faces import FaceModelLoader
from .huggingface import (
    RECOMMENDED_MODELS,
    HFModelInfo,
    HuggingFaceModelBrowser,
    ModelTask,
    get_model_browser,
)
from .vision import (
    BLIP2ModelLoader,
    DetectedObject,
    ImageCaption,
    MoondreamModelLoader,
    ObjectDetectionLoader,
    SceneClassification,
    SceneClassificationLoader,
    VisionModelLoader,
    VisionModelType,
    get_object_detector,
    get_scene_classifier,
    get_vision_model,
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
