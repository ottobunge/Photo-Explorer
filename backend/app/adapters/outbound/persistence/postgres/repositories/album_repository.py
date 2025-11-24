"""PostgreSQL implementation of AlbumRepository."""

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.outbound.persistence.postgres.mappers import AlbumMapper
from app.adapters.outbound.persistence.postgres.models import AlbumModel
from app.application.ports.outbound import AlbumRepository
from app.domain.entities import Album


class AlbumRepositoryPostgres(AlbumRepository):
    """PostgreSQL implementation of AlbumRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, album: Album) -> Album:
        """Persist an album entity."""
        # Check if album already exists
        existing = await self._session.get(AlbumModel, album.id.value)

        if existing:
            # Update existing album
            existing.name = album.name
            existing.description = album.description
            existing.cover_photo_id = album.cover_photo_id
            existing.updated_at = album.updated_at

            await self._session.flush()
            await self._session.refresh(existing, ["photos"])
            return AlbumMapper.to_domain(existing)
        else:
            # Create new album
            model = AlbumMapper.to_model(album)
            self._session.add(model)
            await self._session.flush()
            await self._session.refresh(model, ["photos"])
            return AlbumMapper.to_domain(model)

    async def find_by_id(self, album_id: UUID) -> Optional[Album]:
        """Find an album by its ID."""
        stmt = (
            select(AlbumModel)
            .options(selectinload(AlbumModel.photos))
            .where(AlbumModel.id == album_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            return AlbumMapper.to_domain(model)
        return None

    async def find_all(self, limit: int = 20, offset: int = 0) -> list[Album]:
        """Find all albums with pagination."""
        stmt = (
            select(AlbumModel)
            .options(selectinload(AlbumModel.photos))
            .order_by(AlbumModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [AlbumMapper.to_domain(model) for model in models]

    async def delete(self, album_id: UUID) -> bool:
        """Delete an album."""
        model = await self._session.get(AlbumModel, album_id)
        if model:
            await self._session.delete(model)
            await self._session.flush()
            return True
        return False

    async def count(self) -> int:
        """Count all albums."""
        stmt = select(func.count(AlbumModel.id))
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def find_by_name(self, name: str) -> Optional[Album]:
        """Find an album by its name."""
        stmt = (
            select(AlbumModel)
            .options(selectinload(AlbumModel.photos))
            .where(AlbumModel.name == name)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            return AlbumMapper.to_domain(model)
        return None
