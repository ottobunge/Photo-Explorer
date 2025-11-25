"""Unit tests for Connector entity."""

from datetime import datetime

from app.domain.entities.connector import (
    Connector,
    ConnectorStatus,
    ConnectorType,
)
from app.domain.value_objects import SyncStats


class TestSyncStats:
    """Tests for SyncStats value object."""

    def test_create_default_sync_stats(self):
        """When creating default stats, all counts should be 0."""
        stats = SyncStats()

        assert stats.total_items == 0
        assert stats.indexed == 0
        assert stats.skipped == 0
        assert stats.failed == 0
        assert stats.started_at is None
        assert stats.completed_at is None

    def test_is_complete_when_completed_at_set(self):
        """When completed_at is set, is_complete should be True."""
        stats = SyncStats(completed_at=datetime.utcnow())

        assert stats.is_complete is True

    def test_is_complete_when_not_completed(self):
        """When completed_at is None, is_complete should be False."""
        stats = SyncStats()

        assert stats.is_complete is False

    def test_duration_seconds_with_both_timestamps(self):
        """When both timestamps set, duration_seconds should be computed."""
        stats = SyncStats(
            started_at=datetime(2023, 1, 1, 12, 0, 0),
            completed_at=datetime(2023, 1, 1, 12, 5, 30),
        )

        assert stats.duration_seconds == 330.0  # 5 minutes 30 seconds

    def test_duration_seconds_without_timestamps(self):
        """When timestamps not set, duration_seconds should be None."""
        stats = SyncStats()

        assert stats.duration_seconds is None

    def test_duration_seconds_with_only_started_at(self):
        """When only started_at set, duration_seconds should be None."""
        stats = SyncStats(started_at=datetime.utcnow())

        assert stats.duration_seconds is None


class TestConnectorCreation:
    """Tests for Connector factory methods."""

    def test_create_google_photos_connector(self):
        """When creating Google Photos connector, it should have correct defaults."""
        connector = Connector.create_google_photos()

        assert connector.type == ConnectorType.GOOGLE_PHOTOS
        assert connector.name == "Google Photos"
        assert connector.enabled is True
        assert connector.status == ConnectorStatus.DISCONNECTED
        assert connector.config["sync_interval_hours"] == 6
        assert connector.config["include_albums"] == "all"
        assert connector.created_at is not None
        assert connector.is_remote is True

    def test_create_google_photos_with_custom_name(self):
        """When creating Google Photos with custom name, it should be set."""
        connector = Connector.create_google_photos(name="My Google Photos")

        assert connector.name == "My Google Photos"

    def test_create_local_connector(self):
        """When creating local connector, it should have correct defaults."""
        connector = Connector.create_local(path="/home/user/Pictures")

        assert connector.type == ConnectorType.LOCAL
        assert connector.name == "/home/user/Pictures"
        assert connector.enabled is True
        assert connector.status == ConnectorStatus.CONNECTED
        assert connector.config["path"] == "/home/user/Pictures"
        assert connector.config["recursive"] is True
        assert connector.config["watch"] is True
        assert connector.config["auto_album"] is False
        assert connector.is_remote is False

    def test_create_local_connector_with_custom_name(self):
        """When creating local connector with name, it should override path."""
        connector = Connector.create_local(
            path="/home/user/Pictures",
            name="My Photos",
        )

        assert connector.name == "My Photos"
        assert connector.config["path"] == "/home/user/Pictures"

    def test_create_local_connector_with_custom_config(self):
        """When creating local connector with custom config, it should be stored."""
        connector = Connector.create_local(
            path="/photos",
            recursive=False,
            watch=False,
            auto_album=True,
        )

        assert connector.config["recursive"] is False
        assert connector.config["watch"] is False
        assert connector.config["auto_album"] is True

    def test_create_upload_connector(self):
        """When creating upload connector, it should have correct defaults."""
        connector = Connector.create_upload(upload_path="/uploads")

        assert connector.type == ConnectorType.UPLOAD
        assert connector.name == "Uploads"
        assert connector.enabled is True
        assert connector.status == ConnectorStatus.CONNECTED
        assert connector.config["path"] == "/uploads"
        assert connector.config["is_default"] is True
        assert connector.is_remote is False


class TestConnectorStatusManagement:
    """Tests for Connector status operations."""

    def test_set_connected(self):
        """When setting connected, status should update and error should clear."""
        connector = Connector.create_google_photos()
        connector.set_error("Some error")

        connector.set_connected()

        assert connector.status == ConnectorStatus.CONNECTED
        assert connector.error_message is None

    def test_set_disconnected(self):
        """When setting disconnected, status should update."""
        connector = Connector.create_google_photos()
        connector.set_connected()

        connector.set_disconnected()

        assert connector.status == ConnectorStatus.DISCONNECTED

    def test_set_syncing(self):
        """When setting syncing, status should update."""
        connector = Connector.create_google_photos()

        connector.set_syncing()

        assert connector.status == ConnectorStatus.SYNCING

    def test_set_error(self):
        """When setting error, status and message should update."""
        connector = Connector.create_google_photos()

        connector.set_error("Connection timeout")

        assert connector.status == ConnectorStatus.ERROR
        assert connector.error_message == "Connection timeout"

    def test_status_changes_update_timestamp(self):
        """When changing status, updated_at should change."""
        connector = Connector.create_google_photos()
        original_updated_at = connector.updated_at

        import time

        time.sleep(0.01)

        connector.set_connected()

        assert connector.updated_at > original_updated_at


class TestConnectorSyncRecording:
    """Tests for Connector sync recording."""

    def test_record_sync_with_success(self):
        """When recording successful sync, status should be connected."""
        connector = Connector.create_google_photos()
        stats = SyncStats(
            total_items=100,
            indexed=95,
            skipped=5,
            failed=0,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        connector.record_sync(stats)

        assert connector.last_sync is not None
        assert connector.last_sync_stats == stats
        assert connector.status == ConnectorStatus.CONNECTED
        assert connector.error_message is None

    def test_record_sync_with_failures(self):
        """When recording sync with failures, status should be error."""
        connector = Connector.create_google_photos()
        stats = SyncStats(
            total_items=100,
            indexed=90,
            skipped=5,
            failed=5,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        connector.record_sync(stats)

        assert connector.status == ConnectorStatus.ERROR
        assert "5 items failed to sync" in connector.error_message

    def test_record_sync_updates_timestamp(self):
        """When recording sync, last_sync and updated_at should be set."""
        connector = Connector.create_google_photos()
        before = datetime.utcnow()
        stats = SyncStats()

        connector.record_sync(stats)

        assert connector.last_sync >= before
        assert connector.updated_at >= before


class TestConnectorConfiguration:
    """Tests for Connector configuration management."""

    def test_update_config(self):
        """When updating config, values should be merged."""
        connector = Connector.create_google_photos()

        connector.update_config({"sync_interval_hours": 12})

        assert connector.config["sync_interval_hours"] == 12
        assert connector.config["include_albums"] == "all"  # Preserved

    def test_update_config_adds_new_keys(self):
        """When updating config with new keys, they should be added."""
        connector = Connector.create_google_photos()

        connector.update_config({"new_setting": "value"})

        assert connector.config["new_setting"] == "value"

    def test_update_config_updates_timestamp(self):
        """When updating config, updated_at should change."""
        connector = Connector.create_google_photos()
        original_updated_at = connector.updated_at

        import time

        time.sleep(0.01)

        connector.update_config({"key": "value"})

        assert connector.updated_at > original_updated_at


class TestConnectorEnableDisable:
    """Tests for Connector enable/disable operations."""

    def test_enable_connector(self):
        """When enabling connector, enabled should be True."""
        connector = Connector.create_google_photos()
        connector.disable()

        connector.enable()

        assert connector.enabled is True

    def test_disable_connector(self):
        """When disabling connector, enabled should be False."""
        connector = Connector.create_google_photos()

        connector.disable()

        assert connector.enabled is False

    def test_enable_disable_updates_timestamp(self):
        """When enabling/disabling, updated_at should change."""
        connector = Connector.create_google_photos()
        original_updated_at = connector.updated_at

        import time

        time.sleep(0.01)

        connector.disable()

        assert connector.updated_at > original_updated_at


class TestConnectorProperties:
    """Tests for Connector computed properties."""

    def test_is_remote_for_google_photos(self):
        """When connector is Google Photos, is_remote should be True."""
        connector = Connector.create_google_photos()

        assert connector.is_remote is True

    def test_is_remote_for_local(self):
        """When connector is local, is_remote should be False."""
        connector = Connector.create_local(path="/photos")

        assert connector.is_remote is False

    def test_is_remote_for_upload(self):
        """When connector is upload, is_remote should be False."""
        connector = Connector.create_upload(upload_path="/uploads")

        assert connector.is_remote is False

    def test_path_for_local_connector(self):
        """When connector is local, path should return config path."""
        connector = Connector.create_local(path="/home/user/Pictures")

        assert connector.path == "/home/user/Pictures"

    def test_path_for_upload_connector(self):
        """When connector is upload, path should return config path."""
        connector = Connector.create_upload(upload_path="/uploads")

        assert connector.path == "/uploads"

    def test_path_for_remote_connector(self):
        """When connector is remote, path should be None."""
        connector = Connector.create_google_photos()

        assert connector.path is None
