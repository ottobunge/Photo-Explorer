"""Model management API schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class HFModelData(BaseModel):
    """Hugging Face model information."""

    model_id: str
    author: str
    model_name: str
    pipeline_tag: Optional[str] = None
    tags: list[str] = []
    downloads: int = 0
    likes: int = 0
    last_modified: Optional[str] = None
    library_name: Optional[str] = None
    size_mb: Optional[float] = None
    private: bool = False
    gated: bool = False
    files: list[str] = []
    is_downloaded: bool = False


class ModelSearchResponse(BaseModel):
    """Response for model search."""

    success: bool
    data: dict[str, list[HFModelData]]
    error: Optional[dict[str, Any]] = None


class ModelInfoResponse(BaseModel):
    """Response for model info."""

    success: bool
    data: HFModelData
    error: Optional[dict[str, Any]] = None


class DownloadProgressData(BaseModel):
    """Download progress information."""

    model_id: str
    status: str  # pending, downloading, completed, failed
    progress: float
    downloaded_bytes: int = 0
    total_bytes: int = 0
    current_file: Optional[str] = None
    error: Optional[str] = None


class DownloadResponse(BaseModel):
    """Response for download operations."""

    success: bool
    data: DownloadProgressData
    error: Optional[dict[str, Any]] = None


class DownloadRequest(BaseModel):
    """Request to download a model."""

    model_id: str = Field(..., min_length=1, max_length=256, description="Hugging Face model ID")
    revision: str = Field("main", min_length=1, max_length=128, description="Model revision/branch")

    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, v: str) -> str:
        """Validate model ID format."""
        v = v.strip()
        if not v:
            raise ValueError("Model ID cannot be empty")
        # Model ID should be in format: author/model-name
        if "/" not in v:
            raise ValueError("Model ID must be in format: author/model-name")
        parts = v.split("/")
        if len(parts) != 2:
            raise ValueError("Model ID must contain exactly one '/' character")
        author, model_name = parts
        if not author or not model_name:
            raise ValueError("Both author and model name must be non-empty")
        if len(v) > 256:
            raise ValueError("Model ID must be at most 256 characters")
        return v

    @field_validator("revision")
    @classmethod
    def validate_revision(cls, v: str) -> str:
        """Validate revision name."""
        v = v.strip()
        if not v:
            return "main"
        if len(v) > 128:
            raise ValueError("Revision must be at most 128 characters")
        # Check for suspicious characters
        if any(c in v for c in ["<", ">", "|", "&", ";", "`", "$", "(", ")", "{", "}"]):
            raise ValueError("Revision contains invalid characters")
        return v


class DownloadedModelsData(BaseModel):
    """List of downloaded models."""

    models: list[str]


class DownloadedModelsResponse(BaseModel):
    """Response for listing downloaded models."""

    success: bool
    data: DownloadedModelsData
    error: Optional[dict[str, Any]] = None


class RecommendedModelsData(BaseModel):
    """Recommended models by task."""

    recommendations: dict[str, list[HFModelData]]


class RecommendedModelsResponse(BaseModel):
    """Response for recommended models."""

    success: bool
    data: RecommendedModelsData
    error: Optional[dict[str, Any]] = None


class ActiveModelData(BaseModel):
    """Currently active model configuration."""

    clip_model: str
    clip_status: str  # downloaded, downloading, not_downloaded
    face_model: str
    face_status: str


class ActiveModelsResponse(BaseModel):
    """Response for active model configuration."""

    success: bool
    data: ActiveModelData
    error: Optional[dict[str, Any]] = None


class SetActiveModelRequest(BaseModel):
    """Request to set the active model."""

    task: str = Field(..., min_length=1, max_length=50, description="Model task type")
    model_id: str = Field(..., min_length=1, max_length=256, description="Model ID")

    @field_validator("task")
    @classmethod
    def validate_task(cls, v: str) -> str:
        """Validate task type."""
        v = v.strip().lower()
        allowed_tasks = {"clip", "face", "text", "image"}
        if v not in allowed_tasks:
            raise ValueError(f"Invalid task type. Allowed: {', '.join(sorted(allowed_tasks))}")
        return v

    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, v: str) -> str:
        """Validate model ID."""
        v = v.strip()
        if not v:
            raise ValueError("Model ID cannot be empty")
        if len(v) > 256:
            raise ValueError("Model ID must be at most 256 characters")
        return v
