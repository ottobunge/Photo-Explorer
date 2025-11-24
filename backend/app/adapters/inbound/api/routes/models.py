"""Model management API routes."""

from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.adapters.inbound.api.schemas.model_schemas import (
    ActiveModelsResponse,
    DownloadedModelsResponse,
    DownloadProgressData,
    DownloadRequest,
    DownloadResponse,
    HFModelData,
    ModelInfoResponse,
    ModelSearchResponse,
    RecommendedModelsResponse,
    SetActiveModelRequest,
)
from app.infrastructure.models import (
    HFModelInfo,
    ModelTask,
    get_model_browser,
    get_model_config,
    RECOMMENDED_MODELS,
)

router = APIRouter()


def _model_to_schema(info: HFModelInfo, is_downloaded: bool = False) -> HFModelData:
    """Convert HFModelInfo to schema."""
    return HFModelData(
        model_id=info.model_id,
        author=info.author,
        model_name=info.model_name,
        pipeline_tag=info.pipeline_tag,
        tags=info.tags,
        downloads=info.downloads,
        likes=info.likes,
        last_modified=info.last_modified.isoformat() if info.last_modified else None,
        library_name=info.library_name,
        size_mb=info.size_mb,
        private=info.private,
        gated=info.gated,
        files=info.files,
        is_downloaded=is_downloaded,
    )


@router.get("/search", response_model=ModelSearchResponse)
async def search_models(
    query: Annotated[str, Query(min_length=1, max_length=200, description="Search query")],
    task: Annotated[Optional[str], Query(max_length=50, description="Filter by task type")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum results (1-100)")] = 20,
) -> ModelSearchResponse:
    """Search for models on Hugging Face."""
    browser = get_model_browser()

    try:
        model_task = ModelTask(task) if task else None
    except ValueError:
        model_task = None

    results = await browser.search_models(
        query=query,
        task=model_task,
        limit=limit,
    )

    # Check which are downloaded
    downloaded_ids = set(browser.list_downloaded_models())

    models = [
        _model_to_schema(m, is_downloaded=m.model_id in downloaded_ids)
        for m in results
    ]

    return ModelSearchResponse(
        success=True,
        data={"models": models},
    )


@router.get("/info/{author}/{model_name}", response_model=ModelInfoResponse)
async def get_model_info(author: str, model_name: str) -> ModelInfoResponse:
    """Get detailed information about a model."""
    model_id = f"{author}/{model_name}"
    browser = get_model_browser()

    info = await browser.get_model_info(model_id)

    if not info:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")

    is_downloaded = browser.is_model_downloaded(model_id)

    return ModelInfoResponse(
        success=True,
        data=_model_to_schema(info, is_downloaded=is_downloaded),
    )


@router.post("/download", response_model=DownloadResponse)
async def download_model(
    request: DownloadRequest,
    background_tasks: BackgroundTasks,
) -> DownloadResponse:
    """Start downloading a model."""
    browser = get_model_browser()

    # Check if already downloaded
    if browser.is_model_downloaded(request.model_id):
        return DownloadResponse(
            success=True,
            data=DownloadProgressData(
                model_id=request.model_id,
                status="completed",
                progress=1.0,
            ),
        )

    # Start download in background
    async def download_task():
        await browser.download_model(request.model_id, revision=request.revision)

    background_tasks.add_task(download_task)

    return DownloadResponse(
        success=True,
        data=DownloadProgressData(
            model_id=request.model_id,
            status="downloading",
            progress=0.0,
        ),
    )


@router.get("/download/{author}/{model_name}/progress", response_model=DownloadResponse)
async def get_download_progress(author: str, model_name: str) -> DownloadResponse:
    """Get download progress for a model."""
    model_id = f"{author}/{model_name}"
    browser = get_model_browser()

    progress = browser.get_download_progress(model_id)

    if progress:
        return DownloadResponse(
            success=True,
            data=DownloadProgressData(
                model_id=progress.model_id,
                status=progress.status,
                progress=progress.progress,
                downloaded_bytes=progress.downloaded_bytes,
                total_bytes=progress.total_bytes,
                current_file=progress.current_file,
                error=progress.error,
            ),
        )

    # Check if already downloaded
    if browser.is_model_downloaded(model_id):
        return DownloadResponse(
            success=True,
            data=DownloadProgressData(
                model_id=model_id,
                status="completed",
                progress=1.0,
            ),
        )

    return DownloadResponse(
        success=True,
        data=DownloadProgressData(
            model_id=model_id,
            status="not_started",
            progress=0.0,
        ),
    )


@router.delete("/download/{author}/{model_name}")
async def delete_model(author: str, model_name: str) -> dict:
    """Delete a downloaded model."""
    model_id = f"{author}/{model_name}"
    browser = get_model_browser()

    success = await browser.delete_model(model_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")

    return {"success": True, "data": {"deleted": True}}


@router.get("/downloaded", response_model=DownloadedModelsResponse)
async def list_downloaded_models() -> DownloadedModelsResponse:
    """List all downloaded models."""
    browser = get_model_browser()

    models = browser.list_downloaded_models()

    return DownloadedModelsResponse(
        success=True,
        data={"models": models},
    )


@router.get("/recommended", response_model=RecommendedModelsResponse)
async def get_recommended_models(
    task: Annotated[Optional[str], Query(max_length=50, description="Filter by task")] = None,
) -> RecommendedModelsResponse:
    """Get recommended models for each task."""
    browser = get_model_browser()

    try:
        model_task = ModelTask(task) if task else None
    except ValueError:
        model_task = None

    recommended = browser.get_recommended_models(model_task)
    downloaded_ids = set(browser.list_downloaded_models())

    # Fetch info for each recommended model
    result: dict[str, list[HFModelData]] = {}

    for task_name, model_ids in recommended.items():
        result[task_name] = []
        for model_id in model_ids:
            # Create minimal info for now (full info would be too slow)
            parts = model_id.split("/", 1)
            result[task_name].append(HFModelData(
                model_id=model_id,
                author=parts[0] if len(parts) > 1 else "",
                model_name=parts[1] if len(parts) > 1 else parts[0],
                is_downloaded=model_id in downloaded_ids,
            ))

    return RecommendedModelsResponse(
        success=True,
        data={"recommendations": result},
    )


@router.get("/active", response_model=ActiveModelsResponse)
async def get_active_models() -> ActiveModelsResponse:
    """Get currently configured active models."""
    from app.infrastructure.models.downloader import ModelDownloader, CLIP_MODELS

    config = get_model_config()

    # CLIP uses open_clip which auto-downloads from OpenAI CDN
    # The model name format is like "ViT-B/32" in config, "ViT-B-32" in files
    clip_model_name = config.clip.model_name
    clip_file_name = clip_model_name.replace("/", "-")

    # Check if the model file exists in the cache directory
    clip_downloaded = False
    if clip_file_name in CLIP_MODELS:
        model_info = CLIP_MODELS[clip_file_name]
        model_path = config.clip_dir / model_info.filename
        clip_downloaded = model_path.exists()

    # Also check open_clip's default cache location
    if not clip_downloaded:
        import os
        open_clip_cache = os.path.expanduser("~/.cache/clip")
        if os.path.exists(open_clip_cache):
            # open_clip may cache models here
            clip_downloaded = any(
                clip_model_name.replace("/", "-") in f
                for f in os.listdir(open_clip_cache)
            ) if os.path.isdir(open_clip_cache) else False

    # InsightFace models are auto-downloaded by the insightface library
    # Check if the model directory exists
    face_model_name = config.face.detection_model
    face_model_dir = config.face_dir / "models" / face_model_name
    face_downloaded = face_model_dir.exists() and any(face_model_dir.iterdir()) if face_model_dir.exists() else False

    return ActiveModelsResponse(
        success=True,
        data={
            # Return open_clip model name (auto-downloads when used)
            "clip_model": clip_model_name,
            "clip_status": "downloaded" if clip_downloaded else "auto_download",
            # Return InsightFace model name (auto-downloaded when used)
            "face_model": f"insightface/{face_model_name}",
            "face_status": "downloaded" if face_downloaded else "auto_download",
        },
    )


@router.post("/active")
async def set_active_model(request: SetActiveModelRequest) -> dict:
    """Set the active model for a task."""
    # TODO: Implement model switching
    # This would update the config and potentially reload the model
    return {
        "success": True,
        "data": {
            "task": request.task,
            "model_id": request.model_id,
            "message": "Model configuration updated. Restart required to take effect.",
        },
    }


@router.get("/tasks")
async def list_model_tasks() -> dict:
    """List available model tasks."""
    return {
        "success": True,
        "data": {
            "tasks": [
                {"id": task.value, "name": task.name.replace("_", " ").title()}
                for task in ModelTask
            ]
        },
    }
