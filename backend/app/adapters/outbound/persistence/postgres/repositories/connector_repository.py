"""PostgreSQL implementation of ConnectorRepository."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbound.persistence.postgres.mappers import ConnectorMapper
from app.adapters.outbound.persistence.postgres.models import ConnectorModel
from app.application.ports.outbound import ConnectorRepository
from app.domain.entities import Connector
from app.domain.entities.connector import ConnectorType


class ConnectorRepositoryPostgres(ConnectorRepository):
    """PostgreSQL implementation of ConnectorRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, connector: Connector) -> Connector:
        """Persist a connector entity."""
        # Check if connector already exists
        existing = await self._session.get(ConnectorModel, connector.id.value)

        if existing:
            # Update existing connector
            existing.type = connector.type
            existing.name = connector.name
            existing.enabled = connector.enabled
            existing.status = connector.status
            existing.config = connector.config
            existing.last_sync = connector.last_sync
            existing.error_message = connector.error_message
            existing.updated_at = connector.updated_at

            # Handle sync stats serialization
            if connector.last_sync_stats:
                existing.last_sync_stats = {
                    "total_items": connector.last_sync_stats.total_items,
                    "indexed": connector.last_sync_stats.indexed,
                    "skipped": connector.last_sync_stats.skipped,
                    "failed": connector.last_sync_stats.failed,
                    "started_at": (
                        connector.last_sync_stats.started_at.isoformat()
                        if connector.last_sync_stats.started_at
                        else None
                    ),
                    "completed_at": (
                        connector.last_sync_stats.completed_at.isoformat()
                        if connector.last_sync_stats.completed_at
                        else None
                    ),
                }
            else:
                existing.last_sync_stats = None

            await self._session.flush()
            return ConnectorMapper.to_domain(existing)
        else:
            # Create new connector
            model = ConnectorMapper.to_model(connector)
            self._session.add(model)
            await self._session.flush()
            return ConnectorMapper.to_domain(model)

    async def find_by_id(self, connector_id: UUID) -> Optional[Connector]:
        """Find a connector by its ID."""
        model = await self._session.get(ConnectorModel, connector_id)
        if model:
            return ConnectorMapper.to_domain(model)
        return None

    async def find_by_type(self, connector_type: str) -> Optional[Connector]:
        """Find a connector by its type."""
        # Convert string to enum if needed
        if isinstance(connector_type, str):
            try:
                type_enum = ConnectorType(connector_type)
            except ValueError:
                return None
        else:
            type_enum = connector_type

        stmt = select(ConnectorModel).where(ConnectorModel.type == type_enum)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            return ConnectorMapper.to_domain(model)
        return None

    async def find_all(self) -> list[Connector]:
        """Find all connectors."""
        stmt = select(ConnectorModel).order_by(ConnectorModel.created_at.desc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [ConnectorMapper.to_domain(model) for model in models]

    async def find_enabled(self) -> list[Connector]:
        """Find all enabled connectors."""
        stmt = (
            select(ConnectorModel)
            .where(ConnectorModel.enabled.is_(True))
            .order_by(ConnectorModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [ConnectorMapper.to_domain(model) for model in models]

    async def delete(self, connector_id: UUID) -> bool:
        """Delete a connector."""
        model = await self._session.get(ConnectorModel, connector_id)
        if model:
            await self._session.delete(model)
            await self._session.flush()
            return True
        return False

    async def find_by_path(self, path: str) -> Optional[Connector]:
        """Find a local connector by its path."""
        stmt = select(ConnectorModel).where(
            ConnectorModel.type == ConnectorType.LOCAL,
            ConnectorModel.config["path"].as_string() == path,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            return ConnectorMapper.to_domain(model)
        return None
