"""Face API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.adapters.inbound.api.schemas.face_schemas import (
    ClusterData,
    ClusterListData,
    ClusterListResponse,
    ClusterMergeRequest,
    ClusterNameRequest,
    ClusterResponse,
    FaceMoveRequest,
    GraphEdge,
    GraphNode,
    PaginationMeta,
    RelationshipPhotosData,
    RelationshipPhotosResponse,
    RepresentativeFace,
    SocialGraphData,
    SocialGraphResponse,
)
from app.dependencies import FaceRepoDep, FaceServiceDep, FileStorageDep, SearchServiceDep
from app.domain.entities import FaceCluster
from app.domain.exceptions import (
    DomainException,
    EntityNotFoundException,
    FaceClusterNotFoundError,
    FaceNotFoundError,
    InvalidOperationException,
)

router = APIRouter()


def _build_cluster_data(
    cluster: FaceCluster,
    photo_count: int,
) -> ClusterData:
    """Build ClusterData response from a FaceCluster entity."""
    representative_face = None
    if cluster.representative_face_id:
        representative_face = RepresentativeFace(
            id=str(cluster.representative_face_id),
            crop_url=f"/api/v1/faces/{cluster.representative_face_id}/crop",
        )

    return ClusterData(
        id=str(cluster.id.value),
        name=cluster.name,
        face_count=cluster.face_count,
        photo_count=photo_count,
        representative_face=representative_face,
    )


@router.get(
    "/clusters",
    response_model=ClusterListResponse,
    summary="List face clusters",
    description="""
    List all face clusters with pagination and filtering.

    Face clusters are groups of detected faces that appear to be the same person,
    created automatically using facial recognition ML models. Clusters can be
    named to identify people.

    **Filtering options:**
    - **named_only**: Only show clusters that have been assigned a name (identified people)
    - **unnamed_only**: Only show clusters without names (unidentified people)
    - Neither flag: Show all clusters

    **Response includes:**
    - Cluster ID and name (if assigned)
    - Number of face detections in the cluster
    - Number of unique photos containing faces from this cluster
    - Representative face thumbnail for preview

    **Use cases:**
    - Build a "People" gallery in your UI
    - Show unidentified faces for naming
    - Search photos by person
    """,
    responses={
        200: {
            "description": "List of face clusters",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "clusters": [
                                {
                                    "id": "123e4567-e89b-12d3-a456-426614174000",
                                    "name": "John Doe",
                                    "face_count": 45,
                                    "photo_count": 32,
                                    "representative_face": {
                                        "id": "550e8400-e29b-41d4-a716-446655440000",
                                        "crop_url": "/api/v1/faces/550e8400-e29b-41d4-a716-446655440000/crop",
                                    },
                                },
                                {
                                    "id": "223e4567-e89b-12d3-a456-426614174001",
                                    "name": None,
                                    "face_count": 12,
                                    "photo_count": 10,
                                    "representative_face": {
                                        "id": "650e8400-e29b-41d4-a716-446655440001",
                                        "crop_url": "/api/v1/faces/650e8400-e29b-41d4-a716-446655440001/crop",
                                    },
                                },
                            ]
                        },
                        "meta": {"page": 1, "per_page": 50, "total": 23},
                    }
                }
            },
        }
    },
    tags=["Faces"],
)
async def list_clusters(
    face_repo: FaceRepoDep,
    named_only: bool = False,
    unnamed_only: bool = False,
    page: Annotated[int, Query(ge=1, le=1000, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
) -> ClusterListResponse:
    """List face clusters with optional filtering."""
    # Calculate offset
    offset = (page - 1) * per_page

    # Get clusters with filters
    clusters = await face_repo.find_all_clusters(
        named_only=named_only,
        unnamed_only=unnamed_only,
        limit=per_page,
        offset=offset,
    )

    # Get total count for pagination
    # Note: count_clusters only supports named_only filter
    if unnamed_only:
        # For unnamed_only, we need to compute total differently
        # Get total clusters and subtract named ones
        total_all = await face_repo.count_clusters(named_only=False)
        total_named = await face_repo.count_clusters(named_only=True)
        total = total_all - total_named
    else:
        total = await face_repo.count_clusters(named_only=named_only)

    # Build cluster data with photo counts
    # Get all cluster IDs for batch query (eliminates N+1 queries)
    cluster_ids = [cluster.id.value for cluster in clusters]
    photo_counts = await face_repo.count_photos_by_clusters_batch(cluster_ids)

    # Build cluster data using batched photo counts
    cluster_data_list = [
        _build_cluster_data(cluster, photo_counts[cluster.id.value])
        for cluster in clusters
    ]

    return ClusterListResponse(
        success=True,
        data=ClusterListData(clusters=cluster_data_list),
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get(
    "/clusters/{cluster_id}",
    response_model=ClusterResponse,
    summary="Get face cluster details",
    description="""
    Get detailed information about a specific face cluster.

    Returns cluster metadata including:
    - Cluster ID and name (if assigned)
    - Number of face detections
    - Number of unique photos
    - Representative face for the cluster

    Use the cluster faces endpoint to get all individual face detections
    within this cluster.
    """,
    responses={
        200: {
            "description": "Cluster details",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "name": "John Doe",
                            "face_count": 45,
                            "photo_count": 32,
                            "representative_face": {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "crop_url": "/api/v1/faces/550e8400-e29b-41d4-a716-446655440000/crop",
                            },
                        },
                    }
                }
            },
        },
        404: {
            "description": "Cluster not found",
            "content": {"application/json": {"example": {"detail": "Cluster not found"}}},
        },
    },
    tags=["Faces"],
)
async def get_cluster(cluster_id: UUID, face_repo: FaceRepoDep) -> ClusterResponse:
    """Get a face cluster by ID."""
    cluster = await face_repo.find_cluster_by_id(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # Get unique photo count
    photo_count = await face_repo.count_photos_by_cluster(cluster_id)

    cluster_data = _build_cluster_data(cluster, photo_count)

    return ClusterResponse(
        success=True,
        data=cluster_data,
    )


@router.get("/clusters/{cluster_id}/faces")
async def get_cluster_faces(
    cluster_id: UUID,
    face_repo: FaceRepoDep,
    page: Annotated[int, Query(ge=1, le=1000, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 100,
) -> dict:
    """Get all faces in a cluster."""
    cluster = await face_repo.find_cluster_by_id(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # Get faces in this cluster
    faces = await face_repo.find_faces_by_cluster(cluster_id, limit=per_page)

    face_data = [
        {
            "id": str(face.id.value),
            "photo_id": str(face.photo_id),
            "crop_url": f"/api/v1/faces/{face.id.value}/crop",
        }
        for face in faces
    ]

    return {
        "success": True,
        "data": {"faces": face_data},
        "meta": {"page": page, "per_page": per_page, "total": len(face_data)},
    }


@router.patch(
    "/clusters/{cluster_id}",
    response_model=ClusterResponse,
    summary="Name a face cluster",
    description="""
    Assign or update the name of a face cluster to identify a person.

    This is the primary way to identify people in your photo library.
    Once named, you can:
    - Search for photos containing this person
    - Filter photos by person
    - Build a "People" view in your UI

    **Example use case:**
    1. List all unnamed clusters
    2. Show representative face thumbnails to the user
    3. User identifies a person and provides a name
    4. Call this endpoint to assign the name
    5. Cluster now appears in "named" filters

    **Notes:**
    - Names are stored as plain text
    - Duplicate names are allowed (multiple clusters can have the same name)
    - To clear a name, set it to null or empty string
    """,
    responses={
        200: {
            "description": "Cluster named successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "name": "John Doe",
                            "face_count": 45,
                            "photo_count": 32,
                            "representative_face": {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "crop_url": "/api/v1/faces/550e8400-e29b-41d4-a716-446655440000/crop",
                            },
                        },
                    }
                }
            },
        },
        404: {
            "description": "Cluster not found",
            "content": {"application/json": {"example": {"detail": "Cluster not found"}}},
        },
    },
    tags=["Faces"],
)
async def name_cluster(
    cluster_id: UUID,
    request: ClusterNameRequest,
    face_repo: FaceRepoDep,
) -> ClusterResponse:
    """Assign a name to a face cluster."""
    cluster = await face_repo.find_cluster_by_id(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # Update the cluster name
    cluster.set_name(request.name)

    # Save the updated cluster
    cluster = await face_repo.save_cluster(cluster)

    # Get photo count for response
    photo_count = await face_repo.count_photos_by_cluster(cluster_id)

    cluster_data = _build_cluster_data(cluster, photo_count)

    return ClusterResponse(
        success=True,
        data=cluster_data,
    )


@router.post("/clusters/merge", response_model=ClusterResponse)
async def merge_clusters(
    request: ClusterMergeRequest,
    face_service: FaceServiceDep,
    face_repo: FaceRepoDep,
) -> ClusterResponse:
    """Merge multiple clusters into one."""
    try:
        merged_cluster = await face_service.merge_clusters(
            source_cluster_ids=request.source_cluster_ids,
            target_cluster_id=request.target_cluster_id,
        )
    except (EntityNotFoundException, FaceClusterNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (DomainException, InvalidOperationException) as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Get photo count for response
    photo_count = await face_repo.count_photos_by_cluster(merged_cluster.id.value)

    cluster_data = _build_cluster_data(merged_cluster, photo_count)

    return ClusterResponse(
        success=True,
        data=cluster_data,
    )


@router.post("/{face_id}/split", response_model=ClusterResponse)
async def split_face(
    face_id: UUID,
    face_service: FaceServiceDep,
    face_repo: FaceRepoDep,
) -> ClusterResponse:
    """Split a face from its cluster into a new cluster."""
    try:
        new_cluster = await face_service.split_face(face_id)
    except (EntityNotFoundException, FaceNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (DomainException, InvalidOperationException) as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Get photo count for response (will be 1 for new single-face cluster)
    photo_count = await face_repo.count_photos_by_cluster(new_cluster.id.value)

    cluster_data = _build_cluster_data(new_cluster, photo_count)

    return ClusterResponse(
        success=True,
        data=cluster_data,
    )


@router.post("/{face_id}/move")
async def move_face(
    face_id: UUID,
    request: FaceMoveRequest,
    face_service: FaceServiceDep,
) -> dict:
    """Move a face to a different cluster."""
    try:
        await face_service.move_face(face_id, request.target_cluster_id)
    except (EntityNotFoundException, FaceNotFoundError, FaceClusterNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (DomainException, InvalidOperationException) as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"success": True, "data": {"moved": True}}


@router.get(
    "/{face_id}/crop",
    summary="Get face crop image",
    description="""
    Get the cropped thumbnail image of a detected face.

    Face crops are small thumbnail images containing just the detected face,
    extracted from the original photo. They are automatically generated during
    face detection processing.

    **Use cases:**
    - Display face thumbnails in cluster previews
    - Show representative faces for people
    - Build face galleries
    - Face comparison UI

    **Technical details:**
    - Images are typically 112x112 pixels (aligned face)
    - Served as JPEG with caching headers
    - Generated from the original photo during ML processing
    - Stored separately from the original photo

    If a face crop is not available, it may indicate:
    - Face detection is still in progress
    - Face detection failed for this photo
    - Storage error during processing
    """,
    responses={
        200: {
            "description": "Face crop image (JPEG)",
            "content": {"image/jpeg": {"schema": {"type": "string", "format": "binary"}}},
            "headers": {
                "Cache-Control": {
                    "description": "Caching directive for 24 hours",
                    "schema": {"type": "string", "example": "public, max-age=86400"},
                }
            },
        },
        404: {
            "description": "Face or crop not found",
            "content": {
                "application/json": {
                    "examples": {
                        "face_not_found": {
                            "summary": "Face doesn't exist",
                            "value": {"detail": "Face not found"},
                        },
                        "crop_not_available": {
                            "summary": "Crop not generated",
                            "value": {"detail": "Face crop not available"},
                        },
                        "file_missing": {
                            "summary": "File missing from storage",
                            "value": {"detail": "Face crop file not found"},
                        },
                    }
                }
            },
        },
    },
    tags=["Faces"],
)
async def get_face_crop(
    face_id: UUID,
    face_repo: FaceRepoDep,
    file_storage: FileStorageDep,
) -> Response:
    """Get the cropped face image."""
    # Find the face by ID
    face = await face_repo.find_face_by_id(face_id)
    if not face:
        raise HTTPException(status_code=404, detail="Face not found")

    if not face.crop_path:
        raise HTTPException(status_code=404, detail="Face crop not available")

    # Read the crop file from storage
    try:
        image_data = await file_storage.get_file(face.crop_path)
        if not image_data:
            raise HTTPException(status_code=404, detail="Face crop file not found")

        return Response(
            content=image_data,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Face crop file not found")


@router.post("/search")
async def search_by_face(
    search_service: SearchServiceDep,
    image: UploadFile = File(...),
) -> dict:
    """Search for photos containing a similar face."""
    # Read the uploaded image
    image_bytes = await image.read()

    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image file")

    # Perform face search
    try:
        results = await search_service.search_by_face(
            face_image=image_bytes,
            limit=20,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Face search failed: {e!s}")

    # Convert to response format
    photo_results = [
        {
            "photo": {
                "id": str(result.photo.id.value),
                "filename": result.photo.filename,
                "thumbnail_url": f"/api/v1/photos/{result.photo.id.value}/thumbnail"
                if result.photo.thumbnail_path or result.photo.is_remote
                else None,
                "taken_at": result.photo.taken_at.isoformat() if result.photo.taken_at else None,
            },
            "score": result.score,
            "highlights": result.highlights,
        }
        for result in results
    ]

    return {"success": True, "data": {"results": photo_results}}


@router.get(
    "/graph",
    response_model=SocialGraphResponse,
    summary="Get social graph of face relationships",
    description="""
    Get the social graph showing relationships between people based on photo co-appearances.

    The social graph represents people as nodes and relationships as edges. Each edge
    indicates that two people appear together in one or more photos.

    **Query Parameters:**
    - **person_id** (optional): Filter the graph to show only direct connections
      to this specific person. If not provided, returns the complete graph.

    **Response includes:**
    - **Nodes**: All people (face clusters) in the graph
      - ID, name, face count, representative face ID
    - **Edges**: Relationships between people
      - Person A ID, Person B ID, shared photo count
      - Sample photo IDs (up to 5) showing them together
    - **Metadata**: Node count, edge count, is_empty, has_connections

    **Use cases:**
    - Visualize social connections in photo collection
    - Find photos of people who appear together frequently
    - Build interactive network graph UI
    - Discover relationships between people
    """,
    responses={
        200: {
            "description": "Social graph with nodes and edges",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "nodes": [
                                {
                                    "id": "123e4567-e89b-12d3-a456-426614174000",
                                    "name": "John Doe",
                                    "face_count": 45,
                                    "representative_face_id": "550e8400-e29b-41d4-a716-446655440000",
                                },
                                {
                                    "id": "223e4567-e89b-12d3-a456-426614174001",
                                    "name": "Jane Smith",
                                    "face_count": 32,
                                    "representative_face_id": "650e8400-e29b-41d4-a716-446655440001",
                                },
                            ],
                            "edges": [
                                {
                                    "person_a_id": "123e4567-e89b-12d3-a456-426614174000",
                                    "person_b_id": "223e4567-e89b-12d3-a456-426614174001",
                                    "shared_photo_count": 15,
                                    "sample_photo_ids": [
                                        "aaa11111-e89b-12d3-a456-426614174000",
                                        "bbb22222-e89b-12d3-a456-426614174001",
                                    ],
                                }
                            ],
                            "node_count": 2,
                            "edge_count": 1,
                            "is_empty": False,
                            "has_connections": True,
                        },
                        "error": None,
                    }
                }
            },
        }
    },
)
async def get_social_graph(
    face_service: FaceServiceDep,
    person_id: Annotated[UUID | None, Query(description="Filter by person ID")] = None,
) -> SocialGraphResponse:
    """Get the social graph of face relationships."""
    try:
        # Get social graph from service
        graph = await face_service.get_social_graph(filtered_by_person_id=person_id)

        # Convert to response format
        nodes = []
        for node in graph.nodes:
            graph_node = GraphNode(
                id=str(node.id),
                name=node.name,
                face_count=node.face_count,
                representative_face_id=str(node.representative_face_id)
                if node.representative_face_id
                else None,
            )
            nodes.append(graph_node)

        edges = []
        for relationship in graph.edges:
            edge = GraphEdge(
                person_a_id=str(relationship.person_a_id),
                person_b_id=str(relationship.person_b_id),
                shared_photo_count=relationship.shared_photo_count,
                sample_photo_ids=[str(photo_id) for photo_id in relationship.sample_photo_ids],
            )
            edges.append(edge)

        data = SocialGraphData(
            nodes=nodes,
            edges=edges,
            node_count=graph.node_count,
            edge_count=graph.edge_count,
            is_empty=graph.is_empty,
            has_connections=graph.has_connections,
        )

        return SocialGraphResponse(success=True, data=data, error=None)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build social graph: {e!s}")


@router.get(
    "/relationships/{person_a_id}/{person_b_id}/photos",
    response_model=RelationshipPhotosResponse,
    summary="Get photos showing two people together",
    description="""
    Get all photos where two specific people appear together.

    This endpoint returns the complete list of photos containing both people,
    along with information about each person (cluster data).

    **Path Parameters:**
    - **person_a_id**: UUID of first person's cluster
    - **person_b_id**: UUID of second person's cluster

    **Response includes:**
    - **photo_ids**: List of all photo IDs containing both people
    - **person_a**: Cluster data for first person (name, face count, etc.)
    - **person_b**: Cluster data for second person
    - **total**: Total count of shared photos

    **Use cases:**
    - Show all photos of two people together
    - Build relationship detail view in UI
    - Find photos by relationship/co-appearance
    """,
    responses={
        200: {
            "description": "List of photo IDs and person data",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "photo_ids": [
                                "aaa11111-e89b-12d3-a456-426614174000",
                                "bbb22222-e89b-12d3-a456-426614174001",
                            ],
                            "person_a": {
                                "id": "123e4567-e89b-12d3-a456-426614174000",
                                "name": "John Doe",
                                "face_count": 45,
                                "photo_count": 32,
                                "representative_face": {
                                    "id": "550e8400-e29b-41d4-a716-446655440000",
                                    "crop_url": "/api/v1/faces/550e8400-e29b-41d4-a716-446655440000/crop",
                                },
                            },
                            "person_b": {
                                "id": "223e4567-e89b-12d3-a456-426614174001",
                                "name": "Jane Smith",
                                "face_count": 32,
                                "photo_count": 28,
                                "representative_face": {
                                    "id": "650e8400-e29b-41d4-a716-446655440001",
                                    "crop_url": "/api/v1/faces/650e8400-e29b-41d4-a716-446655440001/crop",
                                },
                            },
                            "total": 15,
                        },
                        "error": None,
                    }
                }
            },
        },
        404: {"description": "One or both clusters not found"},
    },
)
async def get_relationship_photos(
    person_a_id: UUID,
    person_b_id: UUID,
    face_service: FaceServiceDep,
    face_repo: FaceRepoDep,
) -> RelationshipPhotosResponse:
    """Get photos where two people appear together."""
    try:
        # Verify both clusters exist
        cluster_a = await face_repo.find_cluster_by_id(person_a_id)
        if not cluster_a:
            raise HTTPException(status_code=404, detail=f"Cluster {person_a_id} not found")

        cluster_b = await face_repo.find_cluster_by_id(person_b_id)
        if not cluster_b:
            raise HTTPException(status_code=404, detail=f"Cluster {person_b_id} not found")

        # Get shared photos
        photo_ids = await face_service.get_relationship_photos(person_a_id, person_b_id)

        # Build cluster data for both people using batch query (eliminates N+1 queries)
        photo_counts = await face_repo.count_photos_by_clusters_batch([person_a_id, person_b_id])
        cluster_data_a = _build_cluster_data(cluster_a, photo_counts[person_a_id])
        cluster_data_b = _build_cluster_data(cluster_b, photo_counts[person_b_id])

        data = RelationshipPhotosData(
            photo_ids=[str(photo_id) for photo_id in photo_ids],
            person_a=cluster_data_a,
            person_b=cluster_data_b,
            total=len(photo_ids),
        )

        return RelationshipPhotosResponse(success=True, data=data, error=None)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get relationship photos: {e!s}"
        )
