"""Face detection and recognition model utilities."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import numpy as np
from PIL import Image

from .config import ModelConfig, FaceConfig, get_model_config

logger = logging.getLogger(__name__)


@dataclass
class DetectedFace:
    """A detected face with bounding box and embedding."""

    # Bounding box (x1, y1, x2, y2)
    bbox: tuple[int, int, int, int]

    # Detection confidence score
    confidence: float

    # Face embedding (512-dimensional for ArcFace)
    embedding: Optional[np.ndarray] = None

    # Facial landmarks (5 points: left eye, right eye, nose, left mouth, right mouth)
    landmarks: Optional[np.ndarray] = None

    # Age estimation (if available)
    age: Optional[int] = None

    # Gender estimation (if available)
    gender: Optional[str] = None

    @property
    def width(self) -> int:
        """Face bounding box width."""
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> int:
        """Face bounding box height."""
        return self.bbox[3] - self.bbox[1]

    @property
    def area(self) -> int:
        """Face bounding box area in pixels."""
        return self.width * self.height

    @property
    def center(self) -> tuple[int, int]:
        """Center point of face bounding box."""
        return (
            (self.bbox[0] + self.bbox[2]) // 2,
            (self.bbox[1] + self.bbox[3]) // 2,
        )


class FaceModelLoader:
    """
    Face detection and recognition model loader.

    Uses InsightFace for detection and recognition.
    """

    def __init__(self, config: Optional[Union[ModelConfig, FaceConfig]] = None):
        # Handle both ModelConfig and FaceConfig
        if config is None:
            self._model_config = get_model_config()
            self._face_config = self._model_config.face
        elif isinstance(config, FaceConfig):
            self._face_config = config
            self._model_config = get_model_config()
        else:
            self._model_config = config
            self._face_config = config.face

        self._app = None
        self._device = None

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._app is not None

    @property
    def embedding_dim(self) -> int:
        """Get the face embedding dimension (512 for ArcFace)."""
        return 512

    def load(self, force: bool = False) -> bool:
        """
        Load the face detection/recognition models.

        Args:
            force: Force reload even if already loaded

        Returns:
            True if models loaded successfully
        """
        if self._app is not None and not force:
            return True

        try:
            import insightface
            from insightface.app import FaceAnalysis

            model_name = self._face_config.detection_model
            models_dir = str(self._model_config.face_dir / "models")

            logger.info(f"Loading face model: {model_name}")

            # Determine providers based on device
            if self._face_config.device == "cuda":
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                self._device = "cuda"
            else:
                providers = ["CPUExecutionProvider"]
                self._device = "cpu"

            # Initialize face analysis
            self._app = FaceAnalysis(
                name=model_name,
                root=models_dir,
                providers=providers,
            )

            # Prepare with detection size
            self._app.prepare(
                ctx_id=0 if self._device == "cuda" else -1,
                det_thresh=self._face_config.det_thresh,
                det_size=(640, 640),
            )

            logger.info(f"Face model loaded successfully on {self._device}")
            return True

        except Exception as e:
            logger.error(f"Failed to load face model: {e}")
            self._app = None
            return False

    def unload(self) -> None:
        """Unload the models to free memory."""
        import gc

        self._app = None

        # Try to free GPU memory
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

        gc.collect()
        logger.info("Face model unloaded")

    def detect_faces(
        self,
        image: Union[Image.Image, Path, str, np.ndarray],
        min_face_size: Optional[int] = None,
        max_faces: Optional[int] = None,
    ) -> list[DetectedFace]:
        """
        Detect faces in an image.

        Args:
            image: PIL Image, path, or numpy array (BGR or RGB)
            min_face_size: Minimum face size to detect (pixels)
            max_faces: Maximum number of faces to return

        Returns:
            List of detected faces with embeddings
        """
        if not self.is_loaded:
            if not self.load():
                return []

        try:
            import cv2

            # Load and convert image
            if isinstance(image, (str, Path)):
                img_array = cv2.imread(str(image))
            elif isinstance(image, Image.Image):
                img_array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            elif isinstance(image, np.ndarray):
                # Assume BGR if 3 channels
                img_array = image
            else:
                raise ValueError(f"Invalid image type: {type(image)}")

            # Run detection
            faces = self._app.get(img_array)

            # Filter by minimum face size
            min_size = min_face_size or self._face_config.min_face_size
            faces = [f for f in faces if (f.bbox[2] - f.bbox[0]) >= min_size]

            # Sort by face size (largest first)
            faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)

            # Limit number of faces
            if max_faces:
                faces = faces[:max_faces]

            # Convert to DetectedFace objects
            detected = []
            for face in faces:
                bbox = tuple(int(x) for x in face.bbox)

                detected.append(DetectedFace(
                    bbox=bbox,
                    confidence=float(face.det_score),
                    embedding=face.embedding if hasattr(face, "embedding") else None,
                    landmarks=face.landmark_2d_106 if hasattr(face, "landmark_2d_106") else face.landmark,
                    age=int(face.age) if hasattr(face, "age") else None,
                    gender="male" if hasattr(face, "gender") and face.gender == 1 else "female" if hasattr(face, "gender") else None,
                ))

            return detected

        except Exception as e:
            logger.error(f"Failed to detect faces: {e}")
            return []

    def get_face_embedding(
        self,
        image: Union[Image.Image, Path, str, np.ndarray],
        face_bbox: Optional[tuple[int, int, int, int]] = None,
    ) -> Optional[np.ndarray]:
        """
        Get embedding for a face in an image.

        Args:
            image: Image containing the face
            face_bbox: Optional bounding box to crop to

        Returns:
            Face embedding (512-dim) or None if no face found
        """
        if face_bbox:
            # Crop image to face region
            if isinstance(image, (str, Path)):
                image = Image.open(image)
            elif isinstance(image, np.ndarray):
                image = Image.fromarray(image)

            x1, y1, x2, y2 = face_bbox
            image = image.crop((x1, y1, x2, y2))

        faces = self.detect_faces(image, max_faces=1)

        if faces and faces[0].embedding is not None:
            return faces[0].embedding

        return None

    def compare_faces(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
    ) -> float:
        """
        Compare two face embeddings.

        Args:
            embedding1: First face embedding
            embedding2: Second face embedding

        Returns:
            Cosine similarity (0-1, higher is more similar)
        """
        # Normalize embeddings
        emb1 = embedding1 / np.linalg.norm(embedding1)
        emb2 = embedding2 / np.linalg.norm(embedding2)

        # Cosine similarity
        similarity = np.dot(emb1, emb2)

        # Convert to 0-1 range
        return float((similarity + 1) / 2)

    def find_matching_faces(
        self,
        query_embedding: np.ndarray,
        face_embeddings: np.ndarray,
        threshold: float = 0.5,
    ) -> list[tuple[int, float]]:
        """
        Find faces matching a query embedding.

        Args:
            query_embedding: Query face embedding
            face_embeddings: Array of face embeddings to search (N x 512)
            threshold: Minimum similarity threshold

        Returns:
            List of (index, similarity) tuples for matches above threshold
        """
        if len(face_embeddings) == 0:
            return []

        # Normalize
        query = query_embedding / np.linalg.norm(query_embedding)
        embeddings = face_embeddings / np.linalg.norm(face_embeddings, axis=1, keepdims=True)

        # Compute similarities
        similarities = embeddings @ query

        # Convert to 0-1 range
        similarities = (similarities + 1) / 2

        # Find matches above threshold
        matches = []
        for i, sim in enumerate(similarities):
            if sim >= threshold:
                matches.append((i, float(sim)))

        # Sort by similarity (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches


# Singleton instance for convenience
_face_loader: Optional[FaceModelLoader] = None


def get_face_loader() -> FaceModelLoader:
    """Get the global face model loader."""
    global _face_loader
    if _face_loader is None:
        _face_loader = FaceModelLoader()
    return _face_loader


def detect_faces(image: Union[Image.Image, Path, str]) -> list[DetectedFace]:
    """Convenience function to detect faces in an image."""
    return get_face_loader().detect_faces(image)
