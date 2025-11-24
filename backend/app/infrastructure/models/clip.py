"""CLIP model loading and embedding utilities."""

import logging
from pathlib import Path
from typing import Optional, Union

import numpy as np
from PIL import Image

from .config import CLIPConfig, ModelConfig, get_model_config

logger = logging.getLogger(__name__)


class CLIPModelLoader:
    """
    CLIP model loader for generating image and text embeddings.

    Uses open_clip for model loading and inference.
    """

    def __init__(self, config: Optional[Union[ModelConfig, CLIPConfig]] = None):
        # Handle both ModelConfig and CLIPConfig
        if config is None:
            self._model_config = get_model_config()
            self._clip_config = self._model_config.clip
        elif isinstance(config, CLIPConfig):
            self._clip_config = config
            self._model_config = get_model_config()
        else:
            self._model_config = config
            self._clip_config = config.clip

        self._model = None
        self._preprocess = None
        self._tokenizer = None
        self._device = None

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model is not None

    @property
    def embedding_dim(self) -> int:
        """Get the embedding dimension for the configured model."""
        return self._clip_config.embedding_dim

    @property
    def device(self) -> str:
        """Get the device being used."""
        return self._device or self._clip_config.device

    def load(self, force: bool = False) -> bool:
        """
        Load the CLIP model.

        Args:
            force: Force reload even if already loaded

        Returns:
            True if model loaded successfully
        """
        if self._model is not None and not force:
            return True

        try:
            import open_clip
            import torch

            model_name = self._clip_config.model_name
            pretrained = self._clip_config.pretrained

            logger.info(f"Loading CLIP model: {model_name} (pretrained: {pretrained})")

            # Determine device
            if self._clip_config.device == "cuda" and torch.cuda.is_available():
                self._device = "cuda"
            elif self._clip_config.device == "mps" and torch.backends.mps.is_available():
                self._device = "mps"
            else:
                self._device = "cpu"
                if self._clip_config.device != "cpu":
                    logger.warning(f"Requested device {self._clip_config.device} not available, using CPU")

            logger.info(f"Using device: {self._device}")

            # Load model - use model config's clip_dir for cache
            self._model, _, self._preprocess = open_clip.create_model_and_transforms(
                model_name,
                pretrained=pretrained,
                device=self._device,
                cache_dir=str(self._model_config.clip_dir),
            )
            self._tokenizer = open_clip.get_tokenizer(model_name)

            # Set to evaluation mode
            self._model.eval()

            logger.info(f"CLIP model loaded successfully on {self._device}")
            return True

        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            self._model = None
            self._preprocess = None
            self._tokenizer = None
            return False

    def unload(self) -> None:
        """Unload the model to free memory."""
        import gc

        self._model = None
        self._preprocess = None
        self._tokenizer = None

        # Try to free GPU memory
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

        gc.collect()
        logger.info("CLIP model unloaded")

    def encode_image(
        self,
        image: Union[Image.Image, Path, str],
        normalize: bool = True,
    ) -> Optional[np.ndarray]:
        """
        Generate embedding for an image.

        Args:
            image: PIL Image, or path to image file
            normalize: Whether to L2-normalize the embedding

        Returns:
            Embedding as numpy array, or None if failed
        """
        if not self.is_loaded:
            if not self.load():
                return None

        try:
            import torch

            # Load image if path provided
            if isinstance(image, (str, Path)):
                image = Image.open(image).convert("RGB")
            elif not isinstance(image, Image.Image):
                raise ValueError(f"Invalid image type: {type(image)}")

            # Ensure RGB
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Preprocess and encode
            image_tensor = self._preprocess(image).unsqueeze(0).to(self._device)

            with torch.no_grad():
                embedding = self._model.encode_image(image_tensor)

                if normalize:
                    embedding = embedding / embedding.norm(dim=-1, keepdim=True)

                embedding = embedding.cpu().numpy().squeeze()

            return embedding

        except Exception as e:
            logger.error(f"Failed to encode image: {e}")
            return None

    def encode_images(
        self,
        images: list[Union[Image.Image, Path, str]],
        normalize: bool = True,
        batch_size: int = 32,
    ) -> Optional[np.ndarray]:
        """
        Generate embeddings for multiple images.

        Args:
            images: List of PIL Images or paths
            normalize: Whether to L2-normalize embeddings
            batch_size: Batch size for processing

        Returns:
            Embeddings as numpy array (N x embedding_dim), or None if failed
        """
        if not self.is_loaded:
            if not self.load():
                return None

        try:
            import torch

            all_embeddings = []

            for i in range(0, len(images), batch_size):
                batch = images[i : i + batch_size]
                batch_tensors = []

                for img in batch:
                    if isinstance(img, (str, Path)):
                        img = Image.open(img).convert("RGB")
                    elif img.mode != "RGB":
                        img = img.convert("RGB")

                    batch_tensors.append(self._preprocess(img))

                batch_tensor = torch.stack(batch_tensors).to(self._device)

                with torch.no_grad():
                    embeddings = self._model.encode_image(batch_tensor)

                    if normalize:
                        embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)

                    all_embeddings.append(embeddings.cpu().numpy())

            return np.vstack(all_embeddings)

        except Exception as e:
            logger.error(f"Failed to encode images: {e}")
            return None

    def encode_text(
        self,
        text: Union[str, list[str]],
        normalize: bool = True,
    ) -> Optional[np.ndarray]:
        """
        Generate embedding(s) for text.

        Args:
            text: Text string or list of strings
            normalize: Whether to L2-normalize embeddings

        Returns:
            Embedding(s) as numpy array, or None if failed
        """
        if not self.is_loaded:
            if not self.load():
                return None

        try:
            import torch

            if isinstance(text, str):
                text = [text]

            tokens = self._tokenizer(text).to(self._device)

            with torch.no_grad():
                embeddings = self._model.encode_text(tokens)

                if normalize:
                    embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)

                embeddings = embeddings.cpu().numpy()

            # Return 1D array if single text
            if len(text) == 1:
                return embeddings.squeeze()

            return embeddings

        except Exception as e:
            logger.error(f"Failed to encode text: {e}")
            return None

    def compute_similarity(
        self,
        image_embedding: np.ndarray,
        text_embeddings: np.ndarray,
    ) -> np.ndarray:
        """
        Compute cosine similarity between image and text embeddings.

        Args:
            image_embedding: Single image embedding (1D)
            text_embeddings: Text embeddings (1D or 2D)

        Returns:
            Similarity scores
        """
        # Ensure 2D for matrix multiplication
        if image_embedding.ndim == 1:
            image_embedding = image_embedding.reshape(1, -1)
        if text_embeddings.ndim == 1:
            text_embeddings = text_embeddings.reshape(1, -1)

        # Cosine similarity (embeddings should already be normalized)
        similarity = image_embedding @ text_embeddings.T

        return similarity.squeeze()


# Singleton instance for convenience
_clip_loader: Optional[CLIPModelLoader] = None


def get_clip_loader() -> CLIPModelLoader:
    """Get the global CLIP model loader."""
    global _clip_loader
    if _clip_loader is None:
        _clip_loader = CLIPModelLoader()
    return _clip_loader


def encode_image(image: Union[Image.Image, Path, str]) -> Optional[np.ndarray]:
    """Convenience function to encode an image."""
    return get_clip_loader().encode_image(image)


def encode_text(text: Union[str, list[str]]) -> Optional[np.ndarray]:
    """Convenience function to encode text."""
    return get_clip_loader().encode_text(text)
