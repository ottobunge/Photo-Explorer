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
    PaginationMeta,
    RepresentativeFace,
)
from app.dependencies import FaceRepoDep, FileStorageDep
from app.domain.entities import FaceCluster

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


@router.get("/clusters", response_model=ClusterListResponse)
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
    cluster_data_list = []
    for cluster in clusters:
        # Get unique photo count for this cluster
        photo_ids = await face_repo.find_photo_ids_by_cluster(
            cluster.id.value,
            limit=10000,  # Get all to count
        )
        photo_count = len(photo_ids)

        cluster_data_list.append(_build_cluster_data(cluster, photo_count))

    return ClusterListResponse(
        success=True,
        data=ClusterListData(clusters=cluster_data_list),
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/clusters/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(cluster_id: UUID, face_repo: FaceRepoDep) -> ClusterResponse:
    """Get a face cluster by ID."""
    cluster = await face_repo.find_cluster_by_id(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # Get unique photo count
    photo_ids = await face_repo.find_photo_ids_by_cluster(cluster_id, limit=10000)
    photo_count = len(photo_ids)

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


@router.patch("/clusters/{cluster_id}", response_model=ClusterResponse)
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
    photo_ids = await face_repo.find_photo_ids_by_cluster(cluster_id, limit=10000)
    photo_count = len(photo_ids)

    cluster_data = _build_cluster_data(cluster, photo_count)

    return ClusterResponse(
        success=True,
        data=cluster_data,
    )


@router.post("/clusters/merge", response_model=ClusterResponse)
async def merge_clusters(request: ClusterMergeRequest) -> ClusterResponse:
    """Merge multiple clusters into one."""
    # TODO: Inject FaceUseCases and call merge_clusters()
    raise HTTPException(status_code=404, detail="Target cluster not found")


@router.post("/{face_id}/split", response_model=ClusterResponse)
async def split_face(face_id: UUID) -> ClusterResponse:
    """Split a face from its cluster into a new cluster."""
    # TODO: Inject FaceUseCases and call split_face()
    raise HTTPException(status_code=404, detail="Face not found")


@router.post("/{face_id}/move")
async def move_face(face_id: UUID, request: FaceMoveRequest) -> dict:
    """Move a face to a different cluster."""
    # TODO: Inject FaceUseCases and call move_face()
    return {"success": True, "data": {"moved": True}}


@router.get("/{face_id}/crop")
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
async def search_by_face(image: UploadFile = File(...)) -> dict:
    """Search for photos containing a similar face."""
    # TODO: Inject SearchUseCases and call search_by_face()
    return {"success": True, "data": {"results": []}}
