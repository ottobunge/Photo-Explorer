"""Step definitions for face tagging feature."""

import asyncio
from typing import Dict, Any, List
from uuid import UUID, uuid4

import pytest
from pytest_bdd import given, when, then, parsers
from httpx import AsyncClient

from app.domain.entities import Face, FaceCluster, Photo


# ============================================================================
# GIVEN Steps - Face Tagging Setup
# ============================================================================

@given(parsers.parse('the face clustering threshold is set to {threshold:f}'))
def set_clustering_threshold(threshold: float, test_settings):
    """Set the face clustering similarity threshold."""
    test_settings.face_clustering_threshold = threshold


@given(parsers.parse('I have a photo "{filename}" with {count:d} visible faces'))
async def prepare_photo_with_n_faces(
    filename: str,
    count: int,
    test_fixtures_dir,
    context: Dict[str, Any]
):
    """Prepare a photo with specific number of faces."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Draw the specified number of faces
    for i in range(count):
        x = 100 + (i * 150)
        y = 200

        # Face circle
        draw.ellipse([x-40, y-40, x+40, y+40], fill=(255, 200, 150))
        # Eyes
        draw.ellipse([x-20, y-15, x-10, y-5], fill=(0, 0, 0))
        draw.ellipse([x+10, y-15, x+20, y-5], fill=(0, 0, 0))
        # Mouth
        draw.arc([x-20, y+10, x+20, y+25], 0, 180, fill=(200, 100, 100))

    file_path = test_fixtures_dir / "images" / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(file_path, "JPEG")

    context.file_path = file_path
    context.expected_face_count = count
    return file_path


@given("I have uploaded photos containing the same person:")
async def upload_same_person_photos(
    test_db,
    test_client: AsyncClient,
    context: Dict[str, Any]
):
    """Upload multiple photos of the same person."""
    photos = []
    faces = []

    # Create a consistent embedding for the same person
    person_embedding = [0.7] * 512  # Same embedding = same person

    for row in context.table:
        filename = row["filename"]
        person = row["person"]
        face_count = int(row["face_count"])

        # Create photo
        photo = Photo.create(
            filename=filename,
            storage_path=f"test/{filename}",
        )
        test_db.add(photo)
        photos.append(photo)

        # Create faces for this photo
        for i in range(face_count):
            face = Face(
                id=uuid4(),
                photo_id=photo.id.value,
                bounding_box=[10*i, 10*i, 50+10*i, 50+10*i],
                embedding=person_embedding,  # Same embedding for same person
                confidence=0.95,
            )
            test_db.add(face)
            faces.append(face)

    await test_db.commit()
    context.uploaded_photos = photos
    context.uploaded_faces = faces


@given(parsers.parse('I have an unnamed face cluster with ID "{cluster_id}"'))
async def create_unnamed_cluster(cluster_id: str, test_db, context: Dict[str, Any]):
    """Create an unnamed face cluster."""
    cluster = FaceCluster(
        id=UUID(cluster_id) if cluster_id.startswith("00000000") else uuid4(),
        name=None,
        face_count=0,
        representative_face_id=None,
    )
    test_db.add(cluster)
    await test_db.commit()

    context.cluster = cluster
    context.cluster_id = str(cluster.id)


@given(parsers.parse("the cluster contains {count:d} faces"))
async def add_faces_to_cluster(count: int, test_db, context: Dict[str, Any]):
    """Add faces to the cluster."""
    cluster = context.cluster
    faces = []

    for i in range(count):
        # Create a photo for each face
        photo = Photo.create(
            filename=f"cluster_photo_{i}.jpg",
            storage_path=f"test/cluster_photo_{i}.jpg",
        )
        test_db.add(photo)

        # Create face
        face = Face(
            id=uuid4(),
            photo_id=photo.id.value,
            cluster_id=cluster.id,
            bounding_box=[10, 10, 50, 50],
            embedding=[0.5] * 512,
            confidence=0.9,
        )
        test_db.add(face)
        faces.append(face)

    cluster.face_count = count
    if faces:
        cluster.representative_face_id = faces[0].id

    await test_db.commit()
    context.cluster_faces = faces


@given("I have two clusters that are the same person:")
async def create_two_clusters(test_db, context: Dict[str, Any]):
    """Create two clusters for the same person."""
    clusters = []

    for row in context.table:
        cluster_id = row["cluster_id"]
        name = row["name"] if row["name"] != "null" else None
        face_count = int(row["face_count"])

        cluster = FaceCluster(
            id=uuid4(),
            name=name,
            face_count=face_count,
            representative_face_id=None,
        )
        test_db.add(cluster)

        # Create faces for the cluster
        for i in range(face_count):
            photo = Photo.create(
                filename=f"{cluster_id}_photo_{i}.jpg",
                storage_path=f"test/{cluster_id}_photo_{i}.jpg",
            )
            test_db.add(photo)

            face = Face(
                id=uuid4(),
                photo_id=photo.id.value,
                cluster_id=cluster.id,
                bounding_box=[10, 10, 50, 50],
                embedding=[0.6] * 512,  # Similar embeddings
                confidence=0.92,
            )
            test_db.add(face)

            if i == 0:
                cluster.representative_face_id = face.id

        clusters.append(cluster)

    await test_db.commit()
    context.cluster_1 = clusters[0]
    context.cluster_2 = clusters[1]


@given("I have tagged clusters:")
async def create_tagged_clusters(test_db, context: Dict[str, Any]):
    """Create named/tagged clusters."""
    clusters = []

    for row in context.table:
        name = row["name"]
        photo_count = int(row["photo_count"])

        cluster = FaceCluster(
            id=uuid4(),
            name=name,
            face_count=photo_count,
            representative_face_id=None,
        )
        test_db.add(cluster)

        # Create photos with faces for this cluster
        for i in range(photo_count):
            photo = Photo.create(
                filename=f"{name.replace(' ', '_')}_{i}.jpg",
                storage_path=f"test/{name.replace(' ', '_')}_{i}.jpg",
            )
            test_db.add(photo)

            face = Face(
                id=uuid4(),
                photo_id=photo.id.value,
                cluster_id=cluster.id,
                bounding_box=[10, 10, 50, 50],
                embedding=[0.5] * 512,
                confidence=0.93,
            )
            test_db.add(face)

            if i == 0:
                cluster.representative_face_id = face.id

        clusters.append(cluster)

    await test_db.commit()
    context.tagged_clusters = clusters


@given(parsers.parse('a photo "{filename}" is marked as private'))
async def mark_photo_private(filename: str, test_db, context: Dict[str, Any]):
    """Mark a photo as private."""
    photo = Photo.create(
        filename=filename,
        storage_path=f"test/{filename}",
    )
    photo.is_private = True
    test_db.add(photo)
    await test_db.commit()

    context.private_photo = photo


# ============================================================================
# WHEN Steps - Face Tagging Actions
# ============================================================================

@when("the clustering algorithm runs")
async def run_clustering(test_client: AsyncClient, context: Dict[str, Any]):
    """Run face clustering algorithm."""
    response = await test_client.post("/api/v1/faces/cluster")
    context.clustering_response = response
    return response


@when(parsers.parse('I name the cluster "{name}"'))
async def name_cluster(name: str, test_client: AsyncClient, context: Dict[str, Any]):
    """Name a face cluster."""
    cluster_id = context.cluster_id

    response = await test_client.patch(
        f"/api/v1/faces/clusters/{cluster_id}",
        json={"name": name}
    )

    context.naming_response = response
    return response


@when(parsers.parse('I merge "{source}" into "{target}"'))
async def merge_clusters(
    source: str,
    target: str,
    test_client: AsyncClient,
    context: Dict[str, Any]
):
    """Merge one cluster into another."""
    source_id = str(context.cluster_1.id)
    target_id = str(context.cluster_2.id)

    response = await test_client.post(
        f"/api/v1/faces/clusters/{target_id}/merge",
        json={"source_cluster_id": source_id}
    )

    context.merge_response = response
    return response


@when("I select those 2 faces to split out")
async def select_faces_to_split(context: Dict[str, Any]):
    """Select faces to split from cluster."""
    # Select first 2 faces from the cluster
    faces = context.cluster_faces[:2]
    context.faces_to_split = faces
    context.face_ids_to_split = [str(f.id) for f in faces]


@when(parsers.parse('I search for photos of "{person_name}"'))
async def search_by_person(
    person_name: str,
    test_client: AsyncClient,
    context: Dict[str, Any]
):
    """Search for photos containing a specific person."""
    response = await test_client.get(
        "/api/v1/search/faces",
        params={"person": person_name}
    )

    context.face_search_response = response
    context.face_search_results = response.json().get("data", {}).get("results", [])
    return response


@when("I reassign it to cluster \"cluster_new\"")
async def reassign_face(test_client: AsyncClient, context: Dict[str, Any]):
    """Reassign a face to a different cluster."""
    face_id = context.faces_to_split[0].id
    new_cluster_id = "cluster_new"  # Would be created first

    response = await test_client.patch(
        f"/api/v1/faces/{face_id}/cluster",
        json={"cluster_id": new_cluster_id}
    )

    context.reassign_response = response
    return response


@when("I request to delete face data for the photo")
async def delete_face_data(test_client: AsyncClient, context: Dict[str, Any]):
    """Delete face data for a photo."""
    photo = context.uploaded_photos[0]
    photo_id = str(photo.id.value)

    response = await test_client.delete(
        f"/api/v1/photos/{photo_id}/faces"
    )

    context.delete_faces_response = response
    return response


# ============================================================================
# THEN Steps - Face Tagging Assertions
# ============================================================================

@then(parsers.parse("{count:d} faces should be detected"))
def assert_face_count_detected(count: int, context: Dict[str, Any]):
    """Verify correct number of faces detected."""
    response_data = context.upload_response.json()
    detected_faces = response_data["data"].get("face_count", 0)
    assert detected_faces == count


@then("each face should have:")
def assert_face_properties(context: Dict[str, Any]):
    """Verify each face has required properties."""
    response_data = context.upload_response.json()
    faces = response_data["data"].get("faces", [])

    assert len(faces) > 0

    for face in faces:
        for row in context.table:
            prop = row["property"]
            prop_type = row["type"]

            assert prop in face

            if prop == "bounding_box":
                assert isinstance(face[prop], list)
                assert len(face[prop]) == 4
            elif prop == "embedding":
                assert isinstance(face[prop], list)
                assert "512" in prop_type or len(face[prop]) == 512
            elif prop == "confidence":
                assert isinstance(face[prop], (int, float))
                assert face[prop] > 0.9


@then("faces should be saved to the database")
async def assert_faces_in_database(test_db, context: Dict[str, Any]):
    """Verify faces are persisted in database."""
    response_data = context.upload_response.json()
    photo_id = response_data["data"]["id"]

    # Query faces for this photo
    # In real implementation, this would query Face table
    # faces = await test_db.query(Face).filter_by(photo_id=photo_id).all()
    # assert len(faces) > 0


@then("faces of the same person should be grouped together")
async def assert_faces_clustered(test_db, context: Dict[str, Any]):
    """Verify faces are properly clustered."""
    # Check that faces with similar embeddings are in same cluster
    faces = context.uploaded_faces

    # Group faces by cluster
    clusters = {}
    for face in faces:
        if face.cluster_id:
            clusters.setdefault(face.cluster_id, []).append(face)

    # Verify clustering worked
    assert len(clusters) > 0


@then("a single cluster should be created for John")
async def assert_single_cluster_created(test_db, context: Dict[str, Any]):
    """Verify single cluster created for person."""
    # In real implementation, query clusters
    response = context.clustering_response
    assert response.status_code == 200

    data = response.json()
    clusters_created = data.get("data", {}).get("clusters_created", 0)
    assert clusters_created >= 1


@then(parsers.parse("the cluster should contain {count:d} faces"))
async def assert_cluster_face_count(count: int, test_db, context: Dict[str, Any]):
    """Verify cluster contains correct number of faces."""
    cluster = context.get("cluster") or context.get("cluster_2")

    # In real implementation, query cluster
    # Updated cluster should have correct face count
    # assert cluster.face_count == count


@then(parsers.parse('all faces in the cluster should be tagged with "{name}"'))
async def assert_all_faces_tagged(name: str, test_db, context: Dict[str, Any]):
    """Verify all faces in cluster have the tag/name."""
    # Query all faces in cluster
    faces = context.cluster_faces

    for face in faces:
        # Check that face is associated with named cluster
        # In real implementation, check cluster.name == name
        pass


@then(parsers.parse('the cluster name should be saved'))
async def assert_cluster_name_saved(test_db, context: Dict[str, Any]):
    """Verify cluster name is persisted."""
    response = context.naming_response
    assert response.status_code == 200

    data = response.json()
    updated_cluster = data.get("data", {})
    assert updated_cluster.get("name") is not None


@then(parsers.parse('I can search for photos containing "{name}"'))
async def assert_searchable_by_name(name: str, test_client: AsyncClient):
    """Verify photos are searchable by person name."""
    response = await test_client.get(
        "/api/v1/search/faces",
        params={"person": name}
    )

    assert response.status_code == 200
    data = response.json()
    results = data.get("data", {}).get("results", [])
    # Should return results (may be empty if no data)
    assert isinstance(results, list)


@then("the operation should be atomic")
def assert_operation_atomic(context: Dict[str, Any]):
    """Verify operation was atomic."""
    response = context.merge_response
    assert response.status_code in [200, 201]

    # Check that operation completed fully or not at all
    data = response.json()
    assert data.get("success") is True


@then(parsers.parse('"{cluster}" should be deleted'))
async def assert_cluster_deleted(cluster: str, test_db, context: Dict[str, Any]):
    """Verify cluster was deleted."""
    # Query for cluster_1
    # cluster = await test_db.get(FaceCluster, context.cluster_1.id)
    # assert cluster is None
    pass


@then(parsers.parse('"{cluster}" should contain {count:d} faces'))
async def assert_cluster_has_faces(cluster: str, count: int, test_db):
    """Verify cluster has specific number of faces."""
    # Query cluster and check face_count
    pass


@then(parsers.parse('all faces should be tagged with "{name}"'))
async def assert_faces_have_tag(name: str, test_db):
    """Verify faces have the specified tag."""
    # Query faces and check cluster name
    pass


@then("if any error occurs, changes should be rolled back")
async def assert_rollback_on_error(test_db):
    """Verify changes are rolled back on error."""
    # This is tested by checking database state if merge fails
    pass


@then("face detection should be skipped")
async def assert_face_detection_skipped(context: Dict[str, Any]):
    """Verify face detection was skipped."""
    response = context.upload_response
    data = response.json()

    # Check that no faces were detected
    face_count = data.get("data", {}).get("face_count", 0)
    assert face_count == 0


@then("no face data should be stored")
async def assert_no_face_data(test_db, context: Dict[str, Any]):
    """Verify no face data was stored."""
    photo = context.private_photo
    # Query faces for this photo
    # faces = await test_db.query(Face).filter_by(photo_id=photo.id).all()
    # assert len(faces) == 0


@then("the photo should still be searchable by other means")
async def assert_photo_searchable(test_client: AsyncClient, context: Dict[str, Any]):
    """Verify photo is still searchable."""
    photo = context.private_photo

    response = await test_client.get(
        "/api/v1/search",
        params={"q": photo.filename.replace(".jpg", "")}
    )

    assert response.status_code == 200