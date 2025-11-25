"""Integration tests for ConnectorRepository performance and index usage.

This module tests that the database index on config->>'path' is properly
used for find_by_path() queries, improving query performance.

NOTE: These tests require PostgreSQL and will be skipped on SQLite since
JSON path indexing and EXPLAIN ANALYZE are PostgreSQL-specific features.
"""

import time
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.adapters.outbound.persistence.postgres.models import ConnectorModel
from app.adapters.outbound.persistence.postgres.repositories.connector_repository import (
    ConnectorRepositoryPostgres,
)
from app.domain.entities.connector import ConnectorStatus, ConnectorType


async def is_postgresql(session):
    """Check if we're using PostgreSQL or SQLite."""
    result = await session.execute(text("SELECT 1"))
    # PostgreSQL uses asyncpg, SQLite uses aiosqlite
    return "postgresql" in str(session.bind.url)


@pytest.mark.asyncio
async def test_find_by_path_uses_index(test_session):
    """Test that find_by_path() uses the database index on config->>'path'.

    This test verifies that the query plan includes an Index Scan on
    ix_connectors_config_path rather than a Sequential Scan.
    """
    # Skip if not PostgreSQL
    if not await is_postgresql(test_session):
        pytest.skip("This test requires PostgreSQL for EXPLAIN ANALYZE")

    # Create test connector with path
    connector = ConnectorModel(
        id=uuid4(),
        type=ConnectorType.LOCAL,
        name="Test Local",
        enabled=True,
        status=ConnectorStatus.ACTIVE,
        config={"path": "/test/path/to/photos"},
    )
    test_session.add(connector)
    await test_session.commit()

    # Execute EXPLAIN ANALYZE on the find_by_path query
    # Note: We need to construct the same query that find_by_path() uses
    query = text(
        """
        EXPLAIN (ANALYZE, FORMAT JSON)
        SELECT * FROM connectors
        WHERE type = 'local'
        AND config->>'path' = '/test/path/to/photos'
    """
    )

    result = await test_session.execute(query)
    explain_output = result.scalar()

    # Parse the EXPLAIN output
    plan = explain_output[0]["Plan"]

    # Check that the query uses Index Scan, not Sequential Scan
    # Note: The actual plan might have nested nodes, so we need to check recursively
    def find_scan_type(node):
        """Recursively find the scan type in the query plan."""
        node_type = node.get("Node Type", "")
        if "Scan" in node_type:
            return node_type

        # Check child plans
        if "Plans" in node:
            for child in node["Plans"]:
                scan_type = find_scan_type(child)
                if scan_type:
                    return scan_type
        return None

    scan_type = find_scan_type(plan)

    # Assert that we're using an index scan, not a sequential scan
    # This will fail before the migration is applied (RED phase)
    assert scan_type is not None, "No scan found in query plan"
    assert "Index" in scan_type, (
        f"Expected Index Scan but got {scan_type}. "
        "The database index on config->>'path' may not exist or is not being used."
    )


@pytest.mark.asyncio
async def test_find_by_path_with_1000_connectors_fast(test_session):
    """Test that find_by_path() remains fast even with 1000+ connectors.

    This test creates 1000 connectors and measures the query time.
    With the index, the query should complete in under 100ms.
    Without the index, it would require a full table scan.
    """
    # Skip if not PostgreSQL
    if not await is_postgresql(test_session):
        pytest.skip("This test requires PostgreSQL for JSON path indexing")

    # Create 1000 test connectors with different paths
    connectors = []
    for i in range(1000):
        connector = ConnectorModel(
            id=uuid4(),
            type=ConnectorType.LOCAL,
            name=f"Test Local {i}",
            enabled=True,
            status=ConnectorStatus.ACTIVE,
            config={"path": f"/test/path/to/photos/{i}"},
        )
        connectors.append(connector)

    test_session.add_all(connectors)
    await test_session.commit()

    # Add one more connector with a known path to search for
    target_path = "/test/path/to/photos/target"
    target_connector = ConnectorModel(
        id=uuid4(),
        type=ConnectorType.LOCAL,
        name="Target Connector",
        enabled=True,
        status=ConnectorStatus.ACTIVE,
        config={"path": target_path},
    )
    test_session.add(target_connector)
    await test_session.commit()

    # Create repository and measure query time
    repo = ConnectorRepositoryPostgres(test_session)

    start_time = time.perf_counter()
    result = await repo.find_by_path(target_path)
    end_time = time.perf_counter()

    query_time_ms = (end_time - start_time) * 1000

    # Verify we found the correct connector
    assert result is not None
    assert result.id.value == target_connector.id

    # With the index, the query should be very fast (< 100ms)
    # Without the index, it would require scanning all 1001 rows
    assert query_time_ms < 100, (
        f"Query took {query_time_ms:.2f}ms, expected < 100ms. "
        "The database index may not be present or not being used."
    )


@pytest.mark.asyncio
async def test_index_only_on_non_null_paths(test_session):
    """Test that the index is partial and only includes non-null paths.

    This test verifies that the index is a partial index (WHERE config->>'path' IS NOT NULL)
    by checking the index definition in pg_indexes.
    """
    # Skip if not PostgreSQL
    if not await is_postgresql(test_session):
        pytest.skip("This test requires PostgreSQL for partial indexes")

    # Query the pg_indexes system catalog to check index definition
    query = text(
        """
        SELECT indexdef
        FROM pg_indexes
        WHERE tablename = 'connectors'
        AND indexname = 'ix_connectors_config_path'
    """
    )

    result = await test_session.execute(query)
    index_def = result.scalar()

    # This will fail if the index doesn't exist (RED phase)
    assert index_def is not None, (
        "Index ix_connectors_config_path does not exist. " "Run the migration to create the index."
    )

    # Verify it's a partial index with WHERE clause
    assert "WHERE" in index_def.upper(), "Index should be partial with WHERE clause"
    assert "IS NOT NULL" in index_def.upper(), "Index should only include non-null paths"


@pytest.mark.asyncio
async def test_find_by_path_with_null_config_paths(test_session):
    """Test that connectors with null paths don't affect find_by_path() queries.

    This ensures that the partial index works correctly and non-path connectors
    don't bloat the index.
    """
    # Skip if not PostgreSQL
    if not await is_postgresql(test_session):
        pytest.skip("This test requires PostgreSQL for partial indexes")

    # Create connectors with null paths (Google Photos, Upload, etc.)
    for i in range(100):
        connector = ConnectorModel(
            id=uuid4(),
            type=ConnectorType.GOOGLE_PHOTOS,
            name=f"Google Photos {i}",
            enabled=True,
            status=ConnectorStatus.ACTIVE,
            config={"credentials": "some_creds"},  # No 'path' key
        )
        test_session.add(connector)

    # Create one local connector with path
    target_path = "/test/path/to/photos/local"
    local_connector = ConnectorModel(
        id=uuid4(),
        type=ConnectorType.LOCAL,
        name="Local Connector",
        enabled=True,
        status=ConnectorStatus.ACTIVE,
        config={"path": target_path},
    )
    test_session.add(local_connector)
    await test_session.commit()

    # Query should still be fast and find the correct connector
    repo = ConnectorRepositoryPostgres(test_session)

    start_time = time.perf_counter()
    result = await repo.find_by_path(target_path)
    end_time = time.perf_counter()

    query_time_ms = (end_time - start_time) * 1000

    assert result is not None
    assert result.id.value == local_connector.id
    assert query_time_ms < 50, (
        f"Query took {query_time_ms:.2f}ms with 100 non-path connectors. "
        "The partial index should exclude these from the index."
    )
