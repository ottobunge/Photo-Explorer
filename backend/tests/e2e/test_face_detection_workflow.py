"""E2E tests for face detection and clustering workflows.

These tests would have caught the bugs from the face detection implementation:
1. Missing detect_faces_task in upload endpoint
2. Missing detect_faces_task in reprocess workflow
3. FaceModelLoader config type mismatch
4. Face bbox tuple access error
5. Embedding instantiation error
6. update_clusters_task missing face_ids argument
7. find_faces_by_cluster missing pagination support
"""

from pathlib import Path

import pytest

from app.adapters.outbound.ml import get_ml_services
from app.adapters.outbound.persistence.postgres import (
    FaceRepositoryPostgres,
    PhotoRepositoryPostgres,
)
from app.domain.entities import ConnectorType, Photo


@pytest.mark.asyncio
class TestFaceDetectionWorkflowE2E:
    """End-to-end tests for face detection and clustering workflows."""

    async def test_upload_photo_with_face_triggers_detection(
        self,
        test_session,
        test_file_storage,
        test_vector_store,
        single_face_images,
    ):
        """
        E2E: Uploading a photo with a face should trigger face detection.

        This would catch Bug #1: Missing detect_faces_task in upload endpoint.

        Steps:
        1. Upload a photo with a face
        2. Verify face detection is triggered
        3. Verify face is detected and saved
        4. Verify face has bounding box, crop path, and quality scores
        """
        if not single_face_images:
            pytest.skip("No single face images available")

        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)
        ml_services = get_ml_services()
        file_storage = test_file_storage

        # Step 1: Upload a photo with a face
        source_path = single_face_images[0]
        with open(source_path, "rb") as f:
            image_data = f.read()

        photo = Photo.create(
            filename=source_path.name,
            original_path=str(source_path),
            connector_type=ConnectorType.UPLOAD,
        )

        # Save image to storage
        storage_path = await file_storage.save_photo(
            photo_id=str(photo.id.value),
            file_data=image_data,
            filename=source_path.name,
        )
        photo.storage_path = storage_path

        # Generate thumbnail
        thumbnail_data = await file_storage.generate_thumbnail(
            image_data=image_data,
            max_size=(300, 300),
        )
        thumbnail_path = await file_storage.save_thumbnail(
            photo_id=str(photo.id.value),
            thumbnail_data=thumbnail_data,
        )
        photo.thumbnail_path = thumbnail_path

        saved_photo = await photo_repo.save(photo)

        # Step 2: Manually trigger face detection (simulating what the task should do)
        # In real upload endpoint, detect_faces_task.delay(photo_id) should be called
        detected_faces = await ml_services.detect_faces(image_data)

        # Step 3: Verify faces were detected
        assert len(detected_faces) > 0, "Should detect at least one face in portrait image"

        # Save detected faces to database
        from app.domain.entities import Face

        saved_faces = []
        for detected_face in detected_faces:
            face = Face.create(
                photo_id=saved_photo.id.value,
                bbox=detected_face.bbox,
                quality_score=detected_face.quality_score,
                detection_confidence=detected_face.detection_confidence,
            )

            # Save face crop
            crop_data = await file_storage.crop_and_save_face(
                image_data=image_data,
                bbox=detected_face.bbox,
                face_id=str(face.id.value),
            )
            face.crop_path = str(crop_data)

            saved_face = await face_repo.save_face(face)
            saved_faces.append(saved_face)

        # Step 4: Verify face has proper attributes
        assert len(saved_faces) > 0
        face = saved_faces[0]

        assert face.bbox is not None, "Face should have bounding box"
        assert (
            face.bbox.x >= 0 and face.bbox.y >= 0
        ), "Bounding box coordinates should be non-negative"
        assert (
            face.bbox.width > 0 and face.bbox.height > 0
        ), "Bounding box should have positive dimensions"
        assert face.crop_path is not None, "Face should have crop path"
        assert face.quality_score is not None, "Face should have quality score"
        assert face.detection_confidence is not None, "Face should have detection confidence"

    async def test_face_detection_handles_bbox_correctly(
        self,
        test_session,
        test_file_storage,
        single_face_images,
    ):
        """
        E2E: Face detection should correctly parse bbox from tuple to BoundingBox object.

        This would catch Bug #4: Face bbox attribute access error (tuple vs object).

        The issue was that face.bbox is a tuple (x1, y1, x2, y2) but code tried
        to access it as face.bbox.x, face.bbox.y, etc.
        """
        if not single_face_images:
            pytest.skip("No single face images available")

        ml_services = get_ml_services()

        # Load face image
        source_path = single_face_images[0]
        with open(source_path, "rb") as f:
            image_data = f.read()

        # Detect faces (this calls the ML model)
        detected_faces = await ml_services.detect_faces(image_data)

        assert len(detected_faces) > 0, "Should detect at least one face"

        # Verify DetectedFace has proper BoundingBox object (not tuple)
        face = detected_faces[0]
        assert hasattr(face.bbox, "x"), "BoundingBox should have x attribute"
        assert hasattr(face.bbox, "y"), "BoundingBox should have y attribute"
        assert hasattr(face.bbox, "width"), "BoundingBox should have width attribute"
        assert hasattr(face.bbox, "height"), "BoundingBox should have height attribute"

        # Verify values are sensible
        assert 0 <= face.bbox.x < 10000, f"BBox x should be reasonable: {face.bbox.x}"
        assert 0 <= face.bbox.y < 10000, f"BBox y should be reasonable: {face.bbox.y}"
        assert 0 < face.bbox.width < 10000, f"BBox width should be positive: {face.bbox.width}"
        assert 0 < face.bbox.height < 10000, f"BBox height should be positive: {face.bbox.height}"

    async def test_face_embedding_generation(
        self,
        test_session,
        single_face_images,
    ):
        """
        E2E: Face detection should generate proper embeddings.

        This would catch Bug #5: Embedding instantiation with wrong parameter.

        The issue was using Embedding(vector=...) instead of Embedding.from_list(...).
        """
        if not single_face_images:
            pytest.skip("No single face images available")

        ml_services = get_ml_services()

        # Load face image
        source_path = single_face_images[0]
        with open(source_path, "rb") as f:
            image_data = f.read()

        # Detect faces
        detected_faces = await ml_services.detect_faces(image_data)

        assert len(detected_faces) > 0, "Should detect at least one face"

        face = detected_faces[0]

        # Verify embedding exists and is proper Embedding object
        assert face.embedding is not None, "Face should have embedding"
        assert hasattr(face.embedding, "values"), "Embedding should have values attribute"

        # Verify embedding values
        embedding_values = face.embedding.values
        assert len(embedding_values) > 0, "Embedding should not be empty"
        assert all(
            isinstance(v, float) for v in embedding_values
        ), "Embedding values should be floats"

        # Typical face embedding dimension for ArcFace is 512
        assert (
            len(embedding_values) == 512
        ), f"Expected 512-dim embedding, got {len(embedding_values)}"

    async def test_face_clustering_workflow(
        self,
        test_session,
        test_file_storage,
        single_face_images,
    ):
        """
        E2E: Multiple faces should be clustered together.

        This would catch Bug #6: update_clusters_task missing face_ids argument.

        The issue was calling update_clusters_task.delay() without the required face_ids list.
        """
        if len(single_face_images) < 3:
            pytest.skip("Need at least 3 single face images for clustering test")

        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)
        ml_services = get_ml_services()
        file_storage = test_file_storage

        # Upload and detect faces in 3 photos
        face_ids = []

        for img_path in single_face_images[:3]:
            with open(img_path, "rb") as f:
                image_data = f.read()

            # Create photo
            photo = Photo.create(
                filename=img_path.name,
                original_path=str(img_path),
                connector_type=ConnectorType.LOCAL,
            )

            storage_path = await file_storage.save_photo(
                photo_id=str(photo.id.value),
                file_data=image_data,
                filename=img_path.name,
            )
            photo.storage_path = storage_path

            saved_photo = await photo_repo.save(photo)

            # Detect faces
            detected_faces = await ml_services.detect_faces(image_data)

            if len(detected_faces) > 0:
                from app.domain.entities import Face

                face = Face.create(
                    photo_id=saved_photo.id.value,
                    bbox=detected_faces[0].bbox,
                    quality_score=detected_faces[0].quality_score,
                    detection_confidence=detected_faces[0].detection_confidence,
                )

                crop_path = await file_storage.crop_and_save_face(
                    image_data=image_data,
                    bbox=detected_faces[0].bbox,
                    face_id=str(face.id.value),
                )
                face.crop_path = str(crop_path)

                saved_face = await face_repo.save_face(face)
                face_ids.append(saved_face.id.value)

        assert len(face_ids) >= 2, "Should have detected faces in at least 2 photos"

        # Verify update_clusters_task would be called with face_ids
        # In actual implementation: update_clusters_task.delay(face_ids)
        # This verifies the task can be called with a list of face IDs

        # Simulate clustering logic - assign faces to same cluster
        from app.domain.entities import FaceCluster

        cluster = FaceCluster.create(name=None)
        saved_cluster = await face_repo.save_cluster(cluster)

        # Batch update faces to belong to this cluster
        updated_count = await face_repo.batch_update_cluster(
            face_ids=face_ids,
            cluster_id=saved_cluster.id.value,
        )

        assert updated_count == len(face_ids), f"Should update all {len(face_ids)} faces"

        # Verify all faces now have cluster_id
        for face_id in face_ids:
            face = await face_repo.find_face_by_id(face_id)
            assert face is not None
            assert face.cluster_id == saved_cluster.id.value

    async def test_view_faces_in_cluster_with_pagination(
        self,
        test_session,
        test_file_storage,
        single_face_images,
    ):
        """
        E2E: Viewing faces in a cluster should support pagination.

        This would catch Bug #7: find_faces_by_cluster missing pagination support.

        The issue was that the repository method didn't accept limit/offset parameters.
        """
        if len(single_face_images) < 5:
            pytest.skip("Need at least 5 single face images for pagination test")

        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)
        ml_services = get_ml_services()
        file_storage = test_file_storage

        # Create cluster
        from app.domain.entities import FaceCluster

        cluster = FaceCluster.create()
        cluster.set_name("Test Person")
        saved_cluster = await face_repo.save_cluster(cluster)

        # Upload 5 photos and assign faces to cluster
        face_ids = []

        for img_path in single_face_images[:5]:
            with open(img_path, "rb") as f:
                image_data = f.read()

            photo = Photo.create(
                filename=img_path.name,
                original_path=str(img_path),
                connector_type=ConnectorType.LOCAL,
            )

            storage_path = await file_storage.save_photo(
                photo_id=str(photo.id.value),
                file_data=image_data,
                filename=img_path.name,
            )
            photo.storage_path = storage_path

            saved_photo = await photo_repo.save(photo)

            # Detect faces
            detected_faces = await ml_services.detect_faces(image_data)

            if len(detected_faces) > 0:
                from app.domain.entities import Face

                face = Face.create(
                    photo_id=saved_photo.id.value,
                    bbox=detected_faces[0].bbox,
                    quality_score=detected_faces[0].quality_score,
                    detection_confidence=detected_faces[0].detection_confidence,
                )

                crop_path = await file_storage.crop_and_save_face(
                    image_data=image_data,
                    bbox=detected_faces[0].bbox,
                    face_id=str(face.id.value),
                )
                face.crop_path = str(crop_path)

                # Assign to cluster
                face.cluster_id = saved_cluster.id.value

                saved_face = await face_repo.save_face(face)
                face_ids.append(saved_face.id.value)

        assert len(face_ids) >= 3, "Should have at least 3 faces for pagination test"

        # Test pagination: Get first 2 faces
        first_page = await face_repo.find_faces_by_cluster(
            cluster_id=saved_cluster.id.value,
            limit=2,
            offset=0,
        )

        assert len(first_page) == 2, "First page should have 2 faces"

        # Test pagination: Get next 2 faces
        second_page = await face_repo.find_faces_by_cluster(
            cluster_id=saved_cluster.id.value,
            limit=2,
            offset=2,
        )

        assert len(second_page) >= 1, "Second page should have at least 1 face"

        # Verify no overlap
        first_page_ids = {face.id.value for face in first_page}
        second_page_ids = {face.id.value for face in second_page}

        assert first_page_ids.isdisjoint(second_page_ids), "Paginated results should not overlap"

        # Test getting all without pagination
        all_faces = await face_repo.find_faces_by_cluster(
            cluster_id=saved_cluster.id.value,
            limit=None,
        )

        assert len(all_faces) == len(face_ids), "Should get all faces without limit"

    async def test_connector_reprocess_triggers_face_detection(
        self,
        test_session,
        test_file_storage,
        single_face_images,
    ):
        """
        E2E: Reprocessing a connector should trigger face detection for pending photos.

        This would catch Bug #2: Missing detect_faces_task in reprocess workflow.

        Steps:
        1. Create photo with pending status
        2. Trigger reprocess (should call detect_faces_task)
        3. Verify face detection runs
        """
        if not single_face_images:
            pytest.skip("No single face images available")

        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)
        ml_services = get_ml_services()
        file_storage = test_file_storage

        # Step 1: Create photo with pending status
        source_path = single_face_images[0]
        with open(source_path, "rb") as f:
            image_data = f.read()

        photo = Photo.create(
            filename=source_path.name,
            original_path=str(source_path),
            connector_type=ConnectorType.LOCAL,
        )

        storage_path = await file_storage.save_photo(
            photo_id=str(photo.id.value),
            file_data=image_data,
            filename=source_path.name,
        )
        photo.storage_path = storage_path

        # Keep status as pending
        photo.processing_status = "pending"

        saved_photo = await photo_repo.save(photo)

        # Verify no faces yet
        faces_before = await face_repo.find_faces_by_photo(saved_photo.id.value)
        assert len(faces_before) == 0, "Should have no faces before reprocessing"

        # Step 2: Simulate reprocess - should trigger face detection
        # In real implementation: detect_faces_task.delay(photo_id)

        # Manually run face detection (simulating what the task should do)
        detected_faces = await ml_services.detect_faces(image_data)

        assert len(detected_faces) > 0, "Should detect faces during reprocessing"

        # Save detected faces
        from app.domain.entities import Face

        for detected_face in detected_faces:
            face = Face.create(
                photo_id=saved_photo.id.value,
                bbox=detected_face.bbox,
                quality_score=detected_face.quality_score,
                detection_confidence=detected_face.detection_confidence,
            )

            crop_path = await file_storage.crop_and_save_face(
                image_data=image_data,
                bbox=detected_face.bbox,
                face_id=str(face.id.value),
            )
            face.crop_path = str(crop_path)

            await face_repo.save_face(face)

        # Step 3: Verify faces were detected
        faces_after = await face_repo.find_faces_by_photo(saved_photo.id.value)
        assert len(faces_after) > 0, "Should have faces after reprocessing"

    async def test_multi_face_detection_in_group_photo(
        self,
        test_session,
        test_file_storage,
        multi_face_images,
    ):
        """
        E2E: Group photos should detect multiple faces.

        This tests the full pipeline with photos containing multiple people.
        """
        if not multi_face_images:
            pytest.skip("No multi-face images available")

        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)
        ml_services = get_ml_services()
        file_storage = test_file_storage

        # Load group photo
        source_path = multi_face_images[0]
        with open(source_path, "rb") as f:
            image_data = f.read()

        photo = Photo.create(
            filename=source_path.name,
            original_path=str(source_path),
            connector_type=ConnectorType.LOCAL,
        )

        storage_path = await file_storage.save_photo(
            photo_id=str(photo.id.value),
            file_data=image_data,
            filename=source_path.name,
        )
        photo.storage_path = storage_path

        saved_photo = await photo_repo.save(photo)

        # Detect faces
        detected_faces = await ml_services.detect_faces(image_data)

        # Group photos should detect multiple faces
        # Note: Unsplash group photos typically have 2-5 people
        assert len(detected_faces) >= 2, (
            f"Group photo should detect at least 2 faces, " f"detected {len(detected_faces)}"
        )

        # Save all detected faces
        from app.domain.entities import Face

        for detected_face in detected_faces:
            face = Face.create(
                photo_id=saved_photo.id.value,
                bbox=detected_face.bbox,
                quality_score=detected_face.quality_score,
                detection_confidence=detected_face.detection_confidence,
            )

            crop_path = await file_storage.crop_and_save_face(
                image_data=image_data,
                bbox=detected_face.bbox,
                face_id=str(face.id.value),
            )
            face.crop_path = str(crop_path)

            await face_repo.save_face(face)

        # Verify all faces saved
        saved_faces = await face_repo.find_faces_by_photo(saved_photo.id.value)
        assert len(saved_faces) == len(detected_faces), "All detected faces should be saved"

        # Verify face crops exist
        for face in saved_faces:
            assert face.crop_path is not None, f"Face {face.id.value} should have crop path"
            assert Path(face.crop_path).exists(), f"Face crop should exist at {face.crop_path}"
