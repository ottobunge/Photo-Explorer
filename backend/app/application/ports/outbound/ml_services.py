"""ML services port - Interface for machine learning operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from app.domain.value_objects import BoundingBox, Embedding, SceneClassification


@dataclass
class DetectedFace:
    """Result from face detection."""

    bbox: BoundingBox
    embedding: Embedding
    quality_score: float
    detection_confidence: float


@dataclass
class DetectedObjectInfo:
    """A detected object with bounding box."""

    label: str
    confidence: float
    bbox: BoundingBox


@dataclass
class ImageAnalysis:
    """Result from vision model analysis."""

    description: str
    scene_classification: SceneClassification
    detected_objects: list[DetectedObjectInfo] = field(default_factory=list)


class MLServices(ABC):
    """Interface for machine learning services."""

    # CLIP operations

    @abstractmethod
    async def encode_image(self, image_data: bytes) -> Embedding:
        """
        Generate CLIP embedding for an image.

        Args:
            image_data: Image bytes

        Returns:
            CLIP embedding vector
        """

    @abstractmethod
    async def encode_text(self, text: str) -> Embedding:
        """
        Generate CLIP embedding for text.

        Args:
            text: Text query

        Returns:
            CLIP embedding vector
        """

    # Vision LLM operations

    @abstractmethod
    async def analyze_image(self, image_data: bytes) -> ImageAnalysis:
        """
        Analyze an image using vision LLM.

        Generates description, scene classification, and detected objects.

        Args:
            image_data: Image bytes

        Returns:
            ImageAnalysis with description and classifications
        """

    @abstractmethod
    async def generate_description(self, image_data: bytes, prompt: Optional[str] = None) -> str:
        """
        Generate a description for an image using vision LLM.

        Args:
            image_data: Image bytes
            prompt: Optional custom prompt for the caption

        Returns:
            Generated description string
        """

    @abstractmethod
    async def answer_question(self, image_data: bytes, question: str) -> str:
        """
        Answer a question about an image using visual question answering.

        Args:
            image_data: Image bytes
            question: Question to answer about the image

        Returns:
            Answer string
        """

    @abstractmethod
    async def detect_objects(self, image_data: bytes) -> list[DetectedObjectInfo]:
        """
        Detect objects in an image using object detection model.

        Args:
            image_data: Image bytes

        Returns:
            List of detected objects with labels and bounding boxes
        """

    @abstractmethod
    async def classify_scene(self, image_data: bytes) -> SceneClassification:
        """
        Classify the scene in an image.

        Args:
            image_data: Image bytes

        Returns:
            Scene classification result
        """

    # Face detection operations

    @abstractmethod
    async def detect_faces(self, image_data: bytes) -> list[DetectedFace]:
        """
        Detect faces in an image.

        Args:
            image_data: Image bytes

        Returns:
            List of detected faces with embeddings
        """

    @abstractmethod
    async def encode_face(self, face_image_data: bytes) -> Optional[Embedding]:
        """
        Generate embedding for a face image.

        Args:
            face_image_data: Cropped face image bytes

        Returns:
            Face embedding vector or None if no face detected
        """

    # Thumbnail generation

    @abstractmethod
    async def generate_thumbnail(
        self,
        image_data: bytes,
        size: tuple[int, int] = (400, 400),
    ) -> bytes:
        """
        Generate a thumbnail for an image.

        Args:
            image_data: Original image bytes
            size: Target thumbnail size (width, height)

        Returns:
            Thumbnail image bytes
        """

    @abstractmethod
    async def crop_face(
        self,
        image_data: bytes,
        bbox: BoundingBox,
        size: tuple[int, int] = (160, 160),
    ) -> bytes:
        """
        Crop and resize a face from an image.

        Args:
            image_data: Original image bytes
            bbox: Face bounding box
            size: Target crop size

        Returns:
            Cropped face image bytes
        """
