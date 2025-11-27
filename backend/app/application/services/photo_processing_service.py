"""Photo processing service - Business logic for photo processing workflows."""

import aiofiles
import logging
from typing import Optional
from uuid import UUID

import numpy as np
from numpy.typing import NDArray

from app.application.ports.outbound import (
    FaceRepository,
    FileStorage,
    MLServices,
    PhotoRepository,
    VectorStore,
)
from app.application.services.types import ImageAnalysisDict, VectorStoreFacePayload, VectorStorePhotoPayload
from app.domain.entities import Face, Photo
from app.domain.exceptions import EntityNotFoundException
from app.domain.value_objects import Embedding

logger = logging.getLogger(__name__)


class ProcessingResult:
    """Result from photo processing."""

    def __init__(
        self,
        status: str,
        photo_id: str,
        thumbnail_path: Optional[str] = None,
    ):
        self.status = status
        self.photo_id = photo_id
        self.thumbnail_path = thumbnail_path

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary."""
        result: dict[str, str] = {
            "status": self.status,
            "photo_id": self.photo_id,
        }
        if self.thumbnail_path:
            result["thumbnail_path"] = self.thumbnail_path
        return result


class FaceDetectionResult:
    """Result from face detection."""

    def __init__(
        self,
        status: str,
        photo_id: str,
        faces_detected: int = 0,
        faces_saved: int = 0,
        faces_in_vector_store: int = 0,
        face_ids: Optional[list[str]] = None,
    ):
        self.status = status
        self.photo_id = photo_id
        self.faces_detected = faces_detected
        self.faces_saved = faces_saved
        self.faces_in_vector_store = faces_in_vector_store
        self.face_ids = face_ids or []

    def to_dict(self) -> dict[str, str | int | list[str]]:
        """Convert to dictionary."""
        return {
            "status": self.status,
            "photo_id": self.photo_id,
            "faces_detected": self.faces_detected,
            "faces_saved": self.faces_saved,
            "faces_in_vector_store": self.faces_in_vector_store,
            "face_ids": self.face_ids,
        }


class PhotoProcessingService:
    """
    Photo processing service - orchestrates photo and face processing pipelines.

    This service encapsulates the business logic for processing photos and detecting faces.
    It follows the hexagonal architecture pattern by depending only on port interfaces.
    """

    def __init__(
        self,
        photo_repo: PhotoRepository,
        face_repo: FaceRepository,
        ml_services: MLServices,
        vector_store: VectorStore,
        file_storage: FileStorage,
    ) -> None:
        """
        Initialize photo processing service.

        Args:
            photo_repo: Repository for photo persistence
            face_repo: Repository for face persistence
            ml_services: ML services for processing
            vector_store: Vector store for embeddings
            file_storage: File storage for images
        """
        self._photo_repo = photo_repo
        self._face_repo = face_repo
        self._ml_services = ml_services
        self._vector_store = vector_store
        self._file_storage = file_storage

    async def process_photo(self, photo_id: UUID) -> ProcessingResult:
        """
        Process a photo: generate thumbnail, extract metadata, create CLIP embedding.

        This method implements the 4-phase photo processing pipeline:
        1. Update status to processing and commit
        2. Load and process image (generate thumbnail, embedding, analysis)
        3. Store embedding in vector store
        4. Update photo with results and mark as completed

        Args:
            photo_id: UUID of the photo to process

        Returns:
            ProcessingResult with status and thumbnail path

        Raises:
            EntityNotFoundException: If photo not found
        """
        # Phase 1: Mark photo as processing
        photo = await self._mark_processing(photo_id)

        # Phase 2: Process image (thumbnail, embedding, analysis)
        try:
            thumbnail_path, embedding, analysis_dict = await self._process_image(photo)
        except Exception as e:
            # On failure, mark photo as failed
            logger.error(f"Processing failed for photo {photo_id}: {e}")
            photo.set_processing_status("failed")
            await self._photo_repo.save(photo)
            raise

        # Phase 3: Store embedding in vector store
        try:
            await self._store_embedding(photo.id.value, embedding, photo.filename, photo.connector_type)
        except Exception as e:
            # On vector store failure, mark photo as failed
            logger.error(f"Vector store error for {photo_id}: {e}")
            photo.set_processing_status("failed")
            await self._photo_repo.save(photo)
            raise

        # Phase 4: Finalize processing and mark as completed
        updated_photo = await self._finalize_processing(photo_id, thumbnail_path, analysis_dict)

        logger.info(f"Successfully processed photo {photo_id}")
        return ProcessingResult(
            status="completed",
            photo_id=str(photo_id),
            thumbnail_path=updated_photo.thumbnail_path,
        )

    async def detect_faces(self, photo_id: UUID) -> FaceDetectionResult:
        """
        Detect faces in a photo and store their embeddings.

        This method implements the 4-phase face detection pipeline:
        1. Load photo and image data
        2. Detect faces and process crops (outside transaction)
        3. Save faces to DB and commit
        4. Store embeddings in vector store (with compensation on failure)

        Args:
            photo_id: UUID of the photo

        Returns:
            FaceDetectionResult with detection statistics

        Raises:
            EntityNotFoundException: If photo not found
        """
        # Phase 1: Load photo and image data
        photo, image_data = await self._load_photo_and_image(photo_id)

        # Phase 2: Detect and process faces
        detected_faces_count, face_data = await self._detect_and_process_faces(
            photo_id, image_data
        )

        # Phase 3: Save faces to database
        saved_face_ids = await self._save_faces(photo_id, face_data)

        # Phase 4: Store embeddings in vector store
        vector_store_face_ids = await self._store_face_embeddings(
            photo_id, face_data, saved_face_ids
        )

        logger.info(
            f"Successfully detected and processed {len(vector_store_face_ids)} faces "
            f"in photo {photo_id}"
        )
        return FaceDetectionResult(
            status="completed",
            photo_id=str(photo_id),
            faces_detected=detected_faces_count,
            faces_saved=len(saved_face_ids),
            faces_in_vector_store=len(vector_store_face_ids),
            face_ids=vector_store_face_ids,
        )

    # Private helper methods for process_photo

    async def _mark_processing(self, photo_id: UUID) -> Photo:
        """
        Phase 1: Get photo and mark as processing.

        Args:
            photo_id: UUID of the photo to process

        Returns:
            Photo entity marked as processing

        Raises:
            EntityNotFoundException: If photo not found
        """
        photo = await self._photo_repo.find_by_id(photo_id)
        if not photo:
            raise EntityNotFoundException("Photo", str(photo_id))

        photo.set_processing_status("processing")
        await self._photo_repo.save(photo)
        logger.debug(f"Photo {photo_id} marked as processing")
        return photo

    async def _process_image(
        self, photo: Photo
    ) -> tuple[str, Embedding, ImageAnalysisDict]:
        """
        Phase 2: Load and process image (generate thumbnail, embedding, analysis).

        Args:
            photo: Photo entity to process

        Returns:
            Tuple of (thumbnail_path, embedding, analysis_dict)

        Raises:
            ValueError: If image data cannot be loaded
        """
        # Load image data
        image_data = await self._load_image_data(photo)
        if not image_data:
            raise ValueError("Could not load image data")

        # Generate thumbnail
        thumbnail_data = await self._ml_services.generate_thumbnail(image_data)
        thumbnail_path = await self._file_storage.save_thumbnail(
            thumbnail_data, str(photo.id.value)
        )

        # Generate CLIP embedding
        embedding = await self._ml_services.encode_image(image_data)

        # Basic image analysis
        analysis_dict: ImageAnalysisDict = {}
        try:
            analysis = await self._ml_services.analyze_image(image_data)
            # Extract just the labels from DetectedObjectInfo for storage
            object_labels = [obj.label for obj in analysis.detected_objects]
            analysis_dict = {
                "description": analysis.description if analysis.description else None,
                "scene_classification": analysis.scene_classification,
                "detected_objects": object_labels,
            }
        except Exception as e:
            # Image analysis failure is non-critical, log and continue
            logger.warning(f"Image analysis failed for {photo.id.value}: {e}")

        return thumbnail_path, embedding, analysis_dict

    async def _store_embedding(
        self,
        photo_id: UUID,
        embedding: Embedding,
        filename: str,
        connector_type: str,
    ) -> None:
        """
        Phase 3: Store embedding in vector store.

        Args:
            photo_id: UUID of the photo
            embedding: CLIP embedding vector
            filename: Photo filename
            connector_type: Type of connector

        Raises:
            Exception: If vector store operation fails
        """
        payload: VectorStorePhotoPayload = {
            "filename": filename,
            "connector_type": connector_type,
        }
        await self._vector_store.store_photo_embedding(
            photo_id,
            embedding,
            payload=dict(payload),  # Cast TypedDict to dict for interface compatibility
        )
        logger.debug(f"Stored embedding for photo {photo_id}")

    async def _finalize_processing(
        self,
        photo_id: UUID,
        thumbnail_path: str,
        analysis_dict: ImageAnalysisDict,
    ) -> Photo:
        """
        Phase 4: Update photo with results and mark as completed.

        Args:
            photo_id: UUID of the photo
            thumbnail_path: Path to generated thumbnail
            analysis_dict: Image analysis results

        Returns:
            Updated Photo entity

        Raises:
            EntityNotFoundException: If photo not found
        """
        # Re-fetch photo to ensure we have latest version
        updated_photo = await self._photo_repo.find_by_id(photo_id)
        if not updated_photo:
            raise EntityNotFoundException("Photo", str(photo_id))

        # Update with processing results
        updated_photo.thumbnail_path = thumbnail_path
        updated_photo.set_ai_analysis(
            description=analysis_dict.get("description"),
            scene_classification=analysis_dict.get("scene_classification"),
            detected_objects=analysis_dict.get("detected_objects"),
        )
        updated_photo.set_processing_status("completed")
        await self._photo_repo.save(updated_photo)

        return updated_photo

    # Private helper methods for detect_faces

    async def _load_photo_and_image(self, photo_id: UUID) -> tuple[Photo, bytes]:
        """
        Phase 1: Load photo and image data.

        Args:
            photo_id: UUID of the photo

        Returns:
            Tuple of (Photo entity, image data bytes)

        Raises:
            EntityNotFoundException: If photo not found
            ValueError: If image data cannot be loaded
        """
        photo = await self._photo_repo.find_by_id(photo_id)
        if not photo:
            raise EntityNotFoundException("Photo", str(photo_id))

        image_data = await self._load_image_data(photo)
        if not image_data:
            raise ValueError("Could not load image data")

        return photo, image_data

    async def _detect_and_process_faces(
        self, photo_id: UUID, image_data: bytes
    ) -> tuple[int, list[tuple[Face, Embedding, str]]]:
        """
        Phase 2: Detect faces and process crops.

        Args:
            photo_id: UUID of the photo
            image_data: Image data bytes

        Returns:
            Tuple of (total detected count, list of (Face, Embedding, crop_path))
        """
        # Detect faces using ML service
        detected_faces = await self._ml_services.detect_faces(image_data)
        logger.debug(f"Detected {len(detected_faces)} faces in photo {photo_id}")

        # Process each detected face (generate crops)
        face_data: list[tuple[Face, Embedding, str]] = []
        for detected in detected_faces:
            try:
                # Create Face entity
                face = Face.create(
                    photo_id=photo_id,
                    bbox=detected.bbox,
                    quality_score=detected.quality_score,
                    detection_confidence=detected.detection_confidence,
                )

                # Generate and save face crop
                crop_data = await self._ml_services.crop_face(image_data, detected.bbox)
                crop_path = await self._file_storage.save_face_crop(
                    crop_data, str(face.id.value)
                )
                face.set_crop_path(crop_path)

                # Store for batch processing
                face_data.append((face, detected.embedding, crop_path))
                logger.debug(
                    f"Processed face {face.id.value} from photo {photo_id} "
                    f"(confidence: {detected.detection_confidence:.2f})"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to process one detected face in {photo_id}: {e}",
                    extra={"photo_id": str(photo_id), "bbox": detected.bbox},
                )
                # Continue with other faces even if one fails

        return len(detected_faces), face_data

    async def _save_faces(
        self, photo_id: UUID, face_data: list[tuple[Face, Embedding, str]]
    ) -> list[str]:
        """
        Phase 3: Save all faces to database.

        Args:
            photo_id: UUID of the photo
            face_data: List of (Face, Embedding, crop_path) tuples

        Returns:
            List of saved face IDs

        Raises:
            EntityNotFoundException: If photo not found
        """
        saved_face_ids: list[str] = []
        if face_data:
            # Re-fetch photo in case it changed
            photo = await self._photo_repo.find_by_id(photo_id)
            if not photo:
                raise EntityNotFoundException("Photo", str(photo_id))

            # Batch save all faces to database
            faces_to_save = [face for face, _, _ in face_data]
            saved_faces = await self._face_repo.save_faces_batch(faces_to_save)

            # Add all faces to photo
            for saved_face in saved_faces:
                photo.add_face(saved_face.id.value)
                saved_face_ids.append(str(saved_face.id.value))

            logger.debug(f"Batch saved {len(saved_faces)} faces for photo {photo_id}")

            # Update photo with face references
            await self._photo_repo.save(photo)
            logger.info(f"Saved {len(saved_face_ids)} faces to database for photo {photo_id}")

        return saved_face_ids

    async def _store_face_embeddings(
        self,
        photo_id: UUID,
        face_data: list[tuple[Face, Embedding, str]],
        saved_face_ids: list[str],
    ) -> list[str]:
        """
        Phase 4: Store embeddings in vector store (with compensation on failure).

        Args:
            photo_id: UUID of the photo
            face_data: List of (Face, Embedding, crop_path) tuples
            saved_face_ids: List of successfully saved face IDs

        Returns:
            List of face IDs with embeddings in vector store

        Raises:
            Exception: If critical vector store error occurs
        """
        vector_store_face_ids: list[str] = []
        try:
            # Store embeddings for faces that were successfully saved
            for face, embedding, _crop_path in face_data:
                face_id_str = str(face.id.value)
                if face_id_str in saved_face_ids:
                    try:
                        payload: VectorStoreFacePayload = {
                            "photo_id": str(photo_id),
                            "cluster_id": None,
                        }
                        await self._vector_store.store_face_embedding(
                            face.id.value,
                            embedding,
                            payload=dict(payload),  # Cast TypedDict to dict for interface compatibility
                        )
                        vector_store_face_ids.append(face_id_str)
                    except Exception as e:
                        logger.error(f"Failed to store embedding for face {face_id_str}: {e}")
                        # Continue with other faces

            # Check if all embeddings were stored successfully
            if len(vector_store_face_ids) < len(saved_face_ids):
                failed_count = len(saved_face_ids) - len(vector_store_face_ids)
                logger.warning(
                    f"Vector store incomplete: {failed_count}/{len(saved_face_ids)} "
                    f"embeddings failed for {photo_id}"
                )
            else:
                logger.info(
                    f"Stored {len(vector_store_face_ids)} face embeddings for photo {photo_id}"
                )

        except Exception as e:
            logger.error(f"Critical vector store error for {photo_id}: {e}")
            # Compensating action: Delete faces from database
            await self._compensate_face_detection_failure(photo_id, saved_face_ids)
            raise

        return vector_store_face_ids

    async def _load_image_data(self, photo: Photo) -> bytes:
        """
        Load image data from storage or source path.

        Args:
            photo: Photo entity

        Returns:
            Image data as bytes

        Raises:
            ValueError: If no valid image path available
        """
        if photo.storage_path:
            image_data = await self._file_storage.get_file(photo.storage_path)
            if image_data is None:
                raise ValueError(f"Could not load image from storage: {photo.storage_path}")
            return image_data
        elif photo.source_path:
            # For local connector, read from source path with async I/O
            async with aiofiles.open(photo.source_path, "rb") as f:
                return await f.read()
        else:
            raise ValueError("No image path available")

    async def _compensate_face_detection_failure(
        self, photo_id: UUID, face_ids: list[str]
    ) -> None:
        """
        Compensating action: delete faces from database after vector store failure.

        Args:
            photo_id: UUID of the photo
            face_ids: List of face IDs to delete
        """
        try:
            photo = await self._photo_repo.find_by_id(photo_id)
            if photo:
                # Remove face references from photo
                for face_id in face_ids:
                    try:
                        photo.remove_face(UUID(face_id))
                    except (ValueError, AttributeError):
                        pass

                await self._photo_repo.save(photo)

                # Delete face records
                for face_id in face_ids:
                    try:
                        await self._face_repo.delete_face(UUID(face_id))
                        logger.debug(f"Deleted orphaned face {face_id} from database")
                    except Exception as del_error:
                        logger.warning(f"Failed to delete orphaned face {face_id}: {del_error}")

                logger.info(
                    f"Compensating action: Deleted {len(face_ids)} faces from database "
                    f"after vector store failure",
                    extra={"photo_id": str(photo_id), "deleted_faces": face_ids},
                )
        except Exception as comp_error:
            logger.error(
                f"Compensating action failed for {photo_id}: {comp_error}",
                extra={"photo_id": str(photo_id)},
            )
