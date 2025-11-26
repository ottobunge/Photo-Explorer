"""ML services adapter wrapping CLIP, InsightFace, and vision model loaders."""

import gc
import io
import logging
from typing import Optional

from PIL import Image

from app.application.ports.outbound.ml_services import (
    DetectedFace,
    DetectedObjectInfo,
    ImageAnalysis,
    MLServices,
)
from app.config import get_settings
from app.domain.value_objects import BoundingBox, Embedding, SceneClassification
from app.infrastructure.models.clip import CLIPModelLoader
from app.infrastructure.models.config import CLIPConfig, FaceConfig
from app.infrastructure.models.faces import FaceModelLoader
from app.infrastructure.models.vision import (
    ObjectDetectionLoader,
    SceneClassificationLoader,
    VisionModelLoader,
    get_object_detector,
    get_scene_classifier,
    get_vision_model,
)

logger = logging.getLogger(__name__)

# Global singleton for worker processes to avoid reloading models
_ml_services_instance: Optional["MLServicesAdapter"] = None


def get_ml_services() -> "MLServicesAdapter":
    """Get or create a singleton MLServicesAdapter instance.

    Use this in workers to avoid reloading models for each task.
    """
    global _ml_services_instance
    if _ml_services_instance is None:
        _ml_services_instance = MLServicesAdapter()
    return _ml_services_instance


class MLServicesAdapter(MLServices):
    """
    Adapter implementing MLServices using CLIP, InsightFace, and vision models.

    Wraps the existing model loaders to provide a unified interface
    for ML operations in the application.
    """

    def __init__(
        self,
        clip_config: Optional[CLIPConfig] = None,
        face_config: Optional[FaceConfig] = None,
    ) -> None:
        settings = get_settings()

        # Configure CLIP
        if clip_config is None:
            clip_config = CLIPConfig(
                model_name=settings.clip_model_name,
                pretrained=settings.clip_pretrained,
            )
        self._clip_config = clip_config
        self._clip_loader: Optional[CLIPModelLoader] = None

        # Configure face detection
        if face_config is None:
            face_config = FaceConfig()
        self._face_config = face_config
        self._face_loader: Optional[FaceModelLoader] = None

        # Vision models (lazy loaded)
        self._vision_loader: Optional[VisionModelLoader] = None
        self._object_detector: Optional[ObjectDetectionLoader] = None
        self._scene_classifier: Optional[SceneClassificationLoader] = None

        # Image processing settings
        self._thumbnail_size = settings.thumbnail_size
        self._face_crop_size = settings.face_crop_size

    @property
    def clip_loader(self) -> CLIPModelLoader:
        """Lazy-load CLIP model."""
        if self._clip_loader is None:
            self._clip_loader = CLIPModelLoader(self._clip_config)
        return self._clip_loader

    @property
    def face_loader(self) -> FaceModelLoader:
        """Lazy-load face detection model."""
        if self._face_loader is None:
            self._face_loader = FaceModelLoader(self._face_config)
        return self._face_loader

    @property
    def vision_loader(self) -> VisionModelLoader:
        """Lazy-load vision model."""
        if self._vision_loader is None:
            self._vision_loader = get_vision_model()
        return self._vision_loader

    @property
    def object_detector(self) -> ObjectDetectionLoader:
        """Lazy-load object detector."""
        if self._object_detector is None:
            self._object_detector = get_object_detector()
        return self._object_detector

    @property
    def scene_classifier(self) -> SceneClassificationLoader:
        """Lazy-load scene classifier."""
        if self._scene_classifier is None:
            self._scene_classifier = get_scene_classifier()
        return self._scene_classifier

    # CLIP operations

    async def encode_image(self, image_data: bytes) -> Embedding:
        """Generate CLIP embedding for an image."""
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_data))

        # Generate embedding using CLIP
        vector = self.clip_loader.encode_image(image)

        return Embedding.from_list(vector.tolist())

    async def encode_text(self, text: str) -> Embedding:
        """Generate CLIP embedding for text."""
        vector = self.clip_loader.encode_text(text)
        return Embedding.from_list(vector.tolist())

    # Vision LLM operations

    async def analyze_image(self, image_data: bytes) -> ImageAnalysis:
        """
        Analyze an image using vision models.

        Uses BLIP-2/Moondream for descriptions, DETR for object detection,
        and scene classification model for scene understanding.
        """
        image = Image.open(io.BytesIO(image_data))

        # Generate caption using vision LLM
        description = ""
        try:
            caption_result = await self.vision_loader.generate_caption(image)
            description = caption_result.caption
        except Exception as e:
            logger.warning(f"Failed to generate caption: {e}")

        # Detect objects
        detected_objects: list[DetectedObjectInfo] = []
        try:
            objects = await self.object_detector.detect_objects(image)
            for obj in objects:
                detected_objects.append(
                    DetectedObjectInfo(
                        label=obj.label,
                        confidence=obj.confidence,
                        bbox=BoundingBox(
                            x=obj.bbox[0],
                            y=obj.bbox[1],
                            width=obj.bbox[2],
                            height=obj.bbox[3],
                        ),
                    )
                )
        except Exception as e:
            logger.warning(f"Failed to detect objects: {e}")

        # Classify scene
        scene_classification = SceneClassification(
            scene_type="unknown",
            confidence=0.0,
            is_indoor=False,
        )
        try:
            scene_result = await self.scene_classifier.classify_scene(image)
            scene_classification = SceneClassification(
                scene_type=scene_result.scene_type,
                confidence=scene_result.confidence,
                is_indoor=scene_result.is_indoor,
            )
        except Exception as e:
            logger.warning(f"Failed to classify scene: {e}")
            # Fallback to CLIP-based classification
            try:
                scene_descriptions = [
                    "an indoor scene inside a building",
                    "an outdoor scene in nature or city",
                ]
                image_embedding = self.clip_loader.encode_image(image)
                indoor_score = self.clip_loader.similarity(
                    image_embedding, self.clip_loader.encode_text(scene_descriptions[0])
                )
                outdoor_score = self.clip_loader.similarity(
                    image_embedding, self.clip_loader.encode_text(scene_descriptions[1])
                )
                is_indoor = indoor_score > outdoor_score
                scene_classification = SceneClassification(
                    scene_type="indoor" if is_indoor else "outdoor",
                    confidence=float(max(indoor_score, outdoor_score)),
                    is_indoor=is_indoor,
                )
            except Exception as fallback_e:
                logger.warning(f"Fallback scene classification also failed: {fallback_e}")

        return ImageAnalysis(
            description=description,
            scene_classification=scene_classification,
            detected_objects=detected_objects,
        )

    async def generate_description(self, image_data: bytes, prompt: Optional[str] = None) -> str:
        """Generate a description for an image using vision LLM."""
        image = Image.open(io.BytesIO(image_data))
        caption_result = await self.vision_loader.generate_caption(image, prompt)
        return caption_result.caption

    async def answer_question(self, image_data: bytes, question: str) -> str:
        """Answer a question about an image using vision LLM."""
        image = Image.open(io.BytesIO(image_data))
        return await self.vision_loader.answer_question(image, question)

    async def detect_objects(self, image_data: bytes) -> list[DetectedObjectInfo]:
        """Detect objects in an image."""
        image = Image.open(io.BytesIO(image_data))
        objects = await self.object_detector.detect_objects(image)

        return [
            DetectedObjectInfo(
                label=obj.label,
                confidence=obj.confidence,
                bbox=BoundingBox(
                    x=obj.bbox[0],
                    y=obj.bbox[1],
                    width=obj.bbox[2],
                    height=obj.bbox[3],
                ),
            )
            for obj in objects
        ]

    async def classify_scene(self, image_data: bytes) -> SceneClassification:
        """Classify the scene in an image."""
        image = Image.open(io.BytesIO(image_data))
        scene_result = await self.scene_classifier.classify_scene(image)
        return SceneClassification(
            scene_type=scene_result.scene_type,
            confidence=scene_result.confidence,
            is_indoor=scene_result.is_indoor,
        )

    # Face detection operations

    async def detect_faces(self, image_data: bytes) -> list[DetectedFace]:
        """Detect faces in an image."""
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_data))

        # Detect faces using InsightFace
        detected = self.face_loader.detect_faces(image)

        results = []
        for face in detected:
            # face.bbox is a tuple (x1, y1, x2, y2)
            x1, y1, x2, y2 = face.bbox
            results.append(
                DetectedFace(
                    bbox=BoundingBox(
                        x=x1,
                        y=y1,
                        width=x2 - x1,
                        height=y2 - y1,
                    ),
                    embedding=Embedding.from_list(face.embedding.tolist()),
                    quality_score=face.confidence,  # Use confidence as quality score
                    detection_confidence=face.confidence,
                )
            )

        return results

    async def encode_face(self, face_image_data: bytes) -> Optional[Embedding]:
        """Generate embedding for a face image."""
        image = Image.open(io.BytesIO(face_image_data))

        # Detect face and get embedding
        detected = self.face_loader.detect_faces(image)
        if not detected:
            return None

        # Return embedding of first detected face
        return Embedding(vector=detected[0].embedding.tolist())

    # Image processing

    async def generate_thumbnail(
        self,
        image_data: bytes,
        size: tuple[int, int] = (400, 400),
    ) -> bytes:
        """Generate a thumbnail for an image."""
        image = Image.open(io.BytesIO(image_data))

        # Convert to RGB if necessary (for PNG with transparency, etc.)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        # Calculate thumbnail size maintaining aspect ratio
        image.thumbnail(size, Image.Resampling.LANCZOS)

        # Save to bytes
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=85, optimize=True)
        return output.getvalue()

    async def crop_face(
        self,
        image_data: bytes,
        bbox: BoundingBox,
        size: tuple[int, int] = (160, 160),
    ) -> bytes:
        """Crop and resize a face from an image."""
        image = Image.open(io.BytesIO(image_data))

        # Convert to RGB if necessary
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        # Get image dimensions
        img_width, img_height = image.size

        # Calculate absolute pixel coordinates from normalized bbox
        # (assuming bbox coordinates might be normalized 0-1 or absolute)
        if bbox.x <= 1 and bbox.y <= 1 and bbox.width <= 1 and bbox.height <= 1:
            # Normalized coordinates
            left = int(bbox.x * img_width)
            top = int(bbox.y * img_height)
            right = int((bbox.x + bbox.width) * img_width)
            bottom = int((bbox.y + bbox.height) * img_height)
        else:
            # Absolute coordinates
            left = int(bbox.x)
            top = int(bbox.y)
            right = int(bbox.x + bbox.width)
            bottom = int(bbox.y + bbox.height)

        # Add margin around face (10%)
        margin_x = int((right - left) * 0.1)
        margin_y = int((bottom - top) * 0.1)

        left = max(0, left - margin_x)
        top = max(0, top - margin_y)
        right = min(img_width, right + margin_x)
        bottom = min(img_height, bottom + margin_y)

        # Crop the face
        face_crop = image.crop((left, top, right, bottom))

        # Resize to target size
        face_crop = face_crop.resize(size, Image.Resampling.LANCZOS)

        # Save to bytes
        output = io.BytesIO()
        face_crop.save(output, format="JPEG", quality=90)
        return output.getvalue()

    async def encode_images_batch(
        self,
        images_data: list[bytes],
    ) -> list[Embedding]:
        """Generate CLIP embeddings for multiple images."""
        images = [Image.open(io.BytesIO(data)) for data in images_data]
        vectors = self.clip_loader.encode_images_batch(images)
        return [Embedding(vector=v.tolist()) for v in vectors]

    def get_clip_embedding_dim(self) -> int:
        """Get the dimensionality of CLIP embeddings."""
        return self.clip_loader.embedding_dim

    def get_face_embedding_dim(self) -> int:
        """Get the dimensionality of face embeddings."""
        return 512  # InsightFace uses 512-dim embeddings

    async def health_check(self) -> dict:
        """Check if ML models are loaded and working."""
        return {
            "clip_loaded": self._clip_loader is not None,
            "face_loaded": self._face_loader is not None,
            "clip_model": self._clip_config.model_name,
            "face_model": self._face_config.detection_model,
        }

    def cleanup(self) -> None:
        """
        Cleanup ML models and free resources.

        This is useful for graceful shutdown or when models need to be reloaded.
        Note: After calling this, the models will be lazy-loaded again on next use.
        """
        if self._clip_loader is not None:
            # CLIP models are typically lightweight, but we can clear them
            self._clip_loader = None
            logger.info("Cleaned up CLIP model loader")

        if self._face_loader is not None:
            # Face models can be memory-intensive
            self._face_loader = None
            logger.info("Cleaned up face model loader")

        if self._vision_loader is not None:
            self._vision_loader = None
            logger.info("Cleaned up vision model loader")

        if self._object_detector is not None:
            self._object_detector = None
            logger.info("Cleaned up object detector")

        if self._scene_classifier is not None:
            self._scene_classifier = None
            logger.info("Cleaned up scene classifier")


def cleanup_ml_services() -> None:
    """
    Cleanup the global ML services singleton.

    This should be called during worker shutdown or when models need to be reloaded.
    """
    global _ml_services_instance
    if _ml_services_instance is not None:
        _ml_services_instance.cleanup()
        _ml_services_instance = None
        logger.info("Cleaned up global ML services instance")
