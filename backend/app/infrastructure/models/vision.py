"""Vision models for image captioning, object detection, and scene classification."""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Union

import torch
from PIL import Image

from .config import ModelConfig, get_model_config

logger = logging.getLogger(__name__)


class VisionModelType(str, Enum):
    """Supported vision model types."""
    BLIP2 = "blip2"
    LLAVA = "llava"
    MOONDREAM = "moondream"


@dataclass
class ImageCaption:
    """Result from image captioning."""
    caption: str
    confidence: Optional[float] = None


@dataclass
class DetectedObject:
    """A detected object in an image."""
    label: str
    confidence: float
    bbox: tuple[float, float, float, float]  # x, y, width, height (normalized)


@dataclass
class SceneClassification:
    """Scene classification result."""
    scene_type: str
    confidence: float
    is_indoor: bool
    attributes: list[str]


class VisionModelLoader(ABC):
    """Abstract base class for vision models."""

    @abstractmethod
    async def generate_caption(self, image: Image.Image, prompt: Optional[str] = None) -> ImageCaption:
        """Generate a caption for an image."""
        pass

    @abstractmethod
    async def answer_question(self, image: Image.Image, question: str) -> str:
        """Answer a question about an image."""
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        pass


class BLIP2ModelLoader(VisionModelLoader):
    """
    BLIP-2 model for image captioning and visual question answering.

    Uses Salesforce's BLIP-2 model which is efficient and produces good captions.
    """

    MODEL_ID = "Salesforce/blip2-opt-2.7b"
    MODEL_ID_SMALL = "Salesforce/blip2-opt-2.7b"  # Smaller version for limited memory

    def __init__(self, config: Optional[ModelConfig] = None, use_small: bool = False):
        self.config = config or get_model_config()
        self._model = None
        self._processor = None
        self._device = None
        self._model_id = self.MODEL_ID_SMALL if use_small else self.MODEL_ID

    def _get_device(self) -> str:
        """Determine the best available device."""
        if self._device is None:
            if torch.cuda.is_available():
                self._device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self._device = "mps"
            else:
                self._device = "cpu"
        return self._device

    async def load(self) -> None:
        """Load the BLIP-2 model."""
        if self._model is not None:
            return

        logger.info(f"Loading BLIP-2 model: {self._model_id}")

        def _load():
            from transformers import Blip2Processor, Blip2ForConditionalGeneration

            device = self._get_device()

            # Load with appropriate dtype based on device
            if device == "cuda":
                dtype = torch.float16
            else:
                dtype = torch.float32

            processor = Blip2Processor.from_pretrained(self._model_id)
            model = Blip2ForConditionalGeneration.from_pretrained(
                self._model_id,
                torch_dtype=dtype,
                device_map="auto" if device == "cuda" else None,
            )

            if device != "cuda":
                model = model.to(device)

            return processor, model

        loop = asyncio.get_event_loop()
        self._processor, self._model = await loop.run_in_executor(None, _load)

        logger.info(f"BLIP-2 loaded on {self._get_device()}")

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model is not None

    async def generate_caption(self, image: Image.Image, prompt: Optional[str] = None) -> ImageCaption:
        """Generate a caption for an image."""
        if not self.is_loaded():
            await self.load()

        def _generate():
            device = self._get_device()

            # Prepare inputs
            if prompt:
                inputs = self._processor(image, text=prompt, return_tensors="pt")
            else:
                inputs = self._processor(image, return_tensors="pt")

            # Move to device
            inputs = {k: v.to(device) for k, v in inputs.items()}

            # Generate caption
            with torch.no_grad():
                generated_ids = self._model.generate(
                    **inputs,
                    max_new_tokens=100,
                    num_beams=5,
                    early_stopping=True,
                )

            caption = self._processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
            return caption

        loop = asyncio.get_event_loop()
        caption = await loop.run_in_executor(None, _generate)

        return ImageCaption(caption=caption)

    async def answer_question(self, image: Image.Image, question: str) -> str:
        """Answer a question about an image."""
        if not self.is_loaded():
            await self.load()

        def _answer():
            device = self._get_device()

            # Format as VQA prompt
            prompt = f"Question: {question} Answer:"

            inputs = self._processor(image, text=prompt, return_tensors="pt")
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                generated_ids = self._model.generate(
                    **inputs,
                    max_new_tokens=50,
                    num_beams=3,
                )

            answer = self._processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()

            # Remove the prompt from the answer if present
            if answer.startswith(prompt):
                answer = answer[len(prompt):].strip()

            return answer

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _answer)


class MoondreamModelLoader(VisionModelLoader):
    """
    Moondream model - smaller and faster vision model.

    Good for resource-constrained environments.
    """

    MODEL_ID = "vikhyatk/moondream2"

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or get_model_config()
        self._model = None
        self._tokenizer = None
        self._device = None

    def _get_device(self) -> str:
        """Determine the best available device."""
        if self._device is None:
            if torch.cuda.is_available():
                self._device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self._device = "mps"
            else:
                self._device = "cpu"
        return self._device

    async def load(self) -> None:
        """Load the Moondream model."""
        if self._model is not None:
            return

        logger.info(f"Loading Moondream model: {self.MODEL_ID}")

        def _load():
            from transformers import AutoModelForCausalLM, AutoTokenizer

            device = self._get_device()

            tokenizer = AutoTokenizer.from_pretrained(self.MODEL_ID, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                self.MODEL_ID,
                trust_remote_code=True,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            ).to(device)

            return tokenizer, model

        loop = asyncio.get_event_loop()
        self._tokenizer, self._model = await loop.run_in_executor(None, _load)

        logger.info(f"Moondream loaded on {self._get_device()}")

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model is not None

    async def generate_caption(self, image: Image.Image, prompt: Optional[str] = None) -> ImageCaption:
        """Generate a caption for an image."""
        if not self.is_loaded():
            await self.load()

        def _generate():
            caption_prompt = prompt or "Describe this image in detail."
            enc_image = self._model.encode_image(image)
            caption = self._model.answer_question(enc_image, caption_prompt, self._tokenizer)
            return caption

        loop = asyncio.get_event_loop()
        caption = await loop.run_in_executor(None, _generate)

        return ImageCaption(caption=caption)

    async def answer_question(self, image: Image.Image, question: str) -> str:
        """Answer a question about an image."""
        if not self.is_loaded():
            await self.load()

        def _answer():
            enc_image = self._model.encode_image(image)
            answer = self._model.answer_question(enc_image, question, self._tokenizer)
            return answer

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _answer)


class ObjectDetectionLoader:
    """
    Object detection using DETR (DEtection TRansformer).

    Detects objects and their bounding boxes in images.
    """

    MODEL_ID = "facebook/detr-resnet-50"

    def __init__(self, config: Optional[ModelConfig] = None, threshold: float = 0.7):
        self.config = config or get_model_config()
        self.threshold = threshold
        self._model = None
        self._processor = None
        self._device = None

    def _get_device(self) -> str:
        """Determine the best available device."""
        if self._device is None:
            if torch.cuda.is_available():
                self._device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self._device = "mps"
            else:
                self._device = "cpu"
        return self._device

    async def load(self) -> None:
        """Load the DETR model."""
        if self._model is not None:
            return

        logger.info(f"Loading DETR model: {self.MODEL_ID}")

        def _load():
            from transformers import DetrImageProcessor, DetrForObjectDetection

            device = self._get_device()

            processor = DetrImageProcessor.from_pretrained(self.MODEL_ID)
            model = DetrForObjectDetection.from_pretrained(self.MODEL_ID)
            model = model.to(device)

            return processor, model

        loop = asyncio.get_event_loop()
        self._processor, self._model = await loop.run_in_executor(None, _load)

        logger.info(f"DETR loaded on {self._get_device()}")

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model is not None

    async def detect_objects(self, image: Image.Image) -> list[DetectedObject]:
        """Detect objects in an image."""
        if not self.is_loaded():
            await self.load()

        def _detect():
            device = self._get_device()

            inputs = self._processor(images=image, return_tensors="pt")
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._model(**inputs)

            # Post-process outputs
            target_sizes = torch.tensor([image.size[::-1]])  # height, width
            results = self._processor.post_process_object_detection(
                outputs, target_sizes=target_sizes, threshold=self.threshold
            )[0]

            detected = []
            for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
                box = box.tolist()
                label_name = self._model.config.id2label[label.item()]

                # Convert to normalized coordinates
                width, height = image.size
                x, y, x2, y2 = box
                norm_box = (
                    x / width,
                    y / height,
                    (x2 - x) / width,
                    (y2 - y) / height,
                )

                detected.append(DetectedObject(
                    label=label_name,
                    confidence=score.item(),
                    bbox=norm_box,
                ))

            return detected

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _detect)


class SceneClassificationLoader:
    """
    Scene classification using Places365 model.

    Classifies images into scene categories (indoor/outdoor, scene type).
    """

    MODEL_ID = "microsoft/resnet-50"  # Fallback, ideally use Places365-trained

    # Common scene categories
    INDOOR_SCENES = {
        "bedroom", "bathroom", "kitchen", "living_room", "dining_room",
        "office", "classroom", "library", "hospital", "restaurant",
        "cafe", "bar", "gym", "museum", "store", "mall", "hotel",
    }

    OUTDOOR_SCENES = {
        "beach", "mountain", "forest", "park", "garden", "street",
        "highway", "bridge", "building", "city", "village", "farm",
        "field", "lake", "river", "ocean", "sky", "desert", "snow",
    }

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or get_model_config()
        self._model = None
        self._processor = None
        self._device = None
        self._labels = None

    def _get_device(self) -> str:
        """Determine the best available device."""
        if self._device is None:
            if torch.cuda.is_available():
                self._device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self._device = "mps"
            else:
                self._device = "cpu"
        return self._device

    async def load(self) -> None:
        """Load the scene classification model."""
        if self._model is not None:
            return

        logger.info("Loading scene classification model")

        def _load():
            from transformers import AutoImageProcessor, AutoModelForImageClassification

            device = self._get_device()

            # Use a general image classification model
            # For better results, use a Places365-trained model
            processor = AutoImageProcessor.from_pretrained(self.MODEL_ID)
            model = AutoModelForImageClassification.from_pretrained(self.MODEL_ID)
            model = model.to(device)
            model.eval()

            return processor, model

        loop = asyncio.get_event_loop()
        self._processor, self._model = await loop.run_in_executor(None, _load)

        logger.info(f"Scene classifier loaded on {self._get_device()}")

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model is not None

    async def classify_scene(self, image: Image.Image, top_k: int = 5) -> SceneClassification:
        """Classify the scene in an image."""
        if not self.is_loaded():
            await self.load()

        def _classify():
            device = self._get_device()

            inputs = self._processor(images=image, return_tensors="pt")
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)

            # Get top predictions
            top_probs, top_indices = torch.topk(probs[0], k=min(top_k, len(probs[0])))

            top_labels = []
            for idx, prob in zip(top_indices, top_probs):
                label = self._model.config.id2label[idx.item()]
                top_labels.append((label, prob.item()))

            # Determine scene type from top prediction
            scene_type = top_labels[0][0] if top_labels else "unknown"
            confidence = top_labels[0][1] if top_labels else 0.0

            # Check if indoor or outdoor based on keywords
            scene_lower = scene_type.lower().replace("_", " ")
            is_indoor = any(indoor in scene_lower for indoor in self.INDOOR_SCENES)
            is_outdoor = any(outdoor in scene_lower for outdoor in self.OUTDOOR_SCENES)

            # Default to outdoor if unclear
            if not is_indoor and not is_outdoor:
                is_indoor = False

            # Extract attributes from other top labels
            attributes = [label for label, _ in top_labels[1:4]]

            return SceneClassification(
                scene_type=scene_type,
                confidence=confidence,
                is_indoor=is_indoor and not is_outdoor,
                attributes=attributes,
            )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _classify)


# Singleton instances
_vision_model: Optional[VisionModelLoader] = None
_object_detector: Optional[ObjectDetectionLoader] = None
_scene_classifier: Optional[SceneClassificationLoader] = None


def get_vision_model(model_type: Optional[VisionModelType] = None) -> VisionModelLoader:
    """Get the global vision model instance."""
    global _vision_model

    if model_type is None:
        model_type_str = os.environ.get("VISION_MODEL", "blip2")
        model_type = VisionModelType(model_type_str)

    if _vision_model is None or not isinstance(_vision_model, {
        VisionModelType.BLIP2: BLIP2ModelLoader,
        VisionModelType.MOONDREAM: MoondreamModelLoader,
    }.get(model_type, BLIP2ModelLoader)):
        if model_type == VisionModelType.BLIP2:
            _vision_model = BLIP2ModelLoader()
        elif model_type == VisionModelType.MOONDREAM:
            _vision_model = MoondreamModelLoader()
        else:
            _vision_model = BLIP2ModelLoader()

    return _vision_model


def get_object_detector() -> ObjectDetectionLoader:
    """Get the global object detector instance."""
    global _object_detector
    if _object_detector is None:
        _object_detector = ObjectDetectionLoader()
    return _object_detector


def get_scene_classifier() -> SceneClassificationLoader:
    """Get the global scene classifier instance."""
    global _scene_classifier
    if _scene_classifier is None:
        _scene_classifier = SceneClassificationLoader()
    return _scene_classifier
