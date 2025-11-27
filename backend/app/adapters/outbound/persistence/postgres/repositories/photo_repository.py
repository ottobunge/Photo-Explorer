"""PostgreSQL implementation of PhotoRepository."""

from typing import Optional
from uuid import UUID

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.outbound.persistence.postgres.mappers import PhotoMapper
from app.adapters.outbound.persistence.postgres.models import (
    AlbumModel,
    PhotoModel,
    photo_album_association,
)
from app.application.ports.outbound import PhotoRepository
from app.domain.entities import Photo


class PhotoRepositoryPostgres(PhotoRepository):
    """PostgreSQL implementation of PhotoRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, photo: Photo) -> Photo:
        """Persist a photo entity."""
        # Check if photo already exists
        existing = await self._session.get(PhotoModel, photo.id.value)

        if existing:
            # Update existing photo
            model = PhotoMapper.to_model(photo)
            for key, value in model.__dict__.items():
                if not key.startswith("_") and key != "id":
                    setattr(existing, key, value)

            # Handle album associations
            await self._sync_album_associations(existing, photo.album_ids)

            await self._session.flush()
            await self._session.refresh(existing, ["albums", "faces"])
            return PhotoMapper.to_domain(existing)
        else:
            # Create new photo
            model = PhotoMapper.to_model(photo)
            self._session.add(model)
            await self._session.flush()

            # Handle album associations
            await self._sync_album_associations(model, photo.album_ids)

            await self._session.refresh(model, ["albums", "faces"])
            return PhotoMapper.to_domain(model)

    async def _sync_album_associations(self, model: PhotoModel, album_ids: list[UUID]) -> None:
        """Synchronize photo-album associations."""
        # Clear existing associations
        await self._session.execute(
            delete(photo_album_association).where(photo_album_association.c.photo_id == model.id)
        )

        # Add new associations using batch query to avoid N+1
        if album_ids:
            # First verify that the albums exist with a single query
            stmt = select(AlbumModel.id).where(AlbumModel.id.in_(album_ids))
            result = await self._session.execute(stmt)
            existing_album_ids = [row[0] for row in result.all()]

            # Insert associations directly into the association table (batch operation)
            if existing_album_ids:
                values = [
                    {"photo_id": model.id, "album_id": album_id} for album_id in existing_album_ids
                ]
                await self._session.execute(insert(photo_album_association).values(values))

    async def find_by_id(self, photo_id: UUID) -> Optional[Photo]:
        """Find a photo by its ID."""
        stmt = (
            select(PhotoModel)
            .options(
                selectinload(PhotoModel.albums),
                selectinload(PhotoModel.faces),
                selectinload(PhotoModel.connector),
            )
            .where(PhotoModel.id == photo_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            return PhotoMapper.to_domain(model)
        return None

    async def find_all(
        self,
        limit: int = 20,
        offset: int = 0,
        album_id: Optional[UUID] = None,
        connector_id: Optional[UUID] = None,
    ) -> list[Photo]:
        """Find all photos with optional filtering."""
        stmt = (
            select(PhotoModel)
            .options(
                selectinload(PhotoModel.albums),
                selectinload(PhotoModel.faces),
                selectinload(PhotoModel.connector),
            )
            .order_by(PhotoModel.created_at.desc())
        )

        if album_id:
            # Join with albums table and use distinct to avoid duplicates
            stmt = stmt.join(PhotoModel.albums).where(AlbumModel.id == album_id).distinct()

        if connector_id:
            stmt = stmt.where(PhotoModel.connector_id == connector_id)

        # Apply limit and offset after filtering
        stmt = stmt.limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [PhotoMapper.to_domain(model) for model in models]

    async def delete(self, photo_id: UUID) -> bool:
        """Delete a photo."""
        model = await self._session.get(PhotoModel, photo_id)
        if model:
            await self._session.delete(model)
            await self._session.flush()
            return True
        return False

    async def count(
        self, album_id: Optional[UUID] = None, connector_id: Optional[UUID] = None
    ) -> int:
        """Count photos with optional filtering."""
        if album_id:
            # Use count(distinct) when joining to avoid counting duplicates
            stmt = (
                select(func.count(func.distinct(PhotoModel.id)))
                .join(PhotoModel.albums)
                .where(AlbumModel.id == album_id)
            )
        else:
            stmt = select(func.count(PhotoModel.id))

        if connector_id:
            stmt = stmt.where(PhotoModel.connector_id == connector_id)

        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def find_by_original_path(self, path: str) -> Optional[Photo]:
        """Find a photo by its original filesystem path."""
        stmt = (
            select(PhotoModel)
            .options(
                selectinload(PhotoModel.albums),
                selectinload(PhotoModel.faces),
                selectinload(PhotoModel.connector),
            )
            .where(PhotoModel.source_path == path)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            return PhotoMapper.to_domain(model)
        return None

    async def find_by_external_id(self, external_id: str, connector_id: UUID) -> Optional[Photo]:
        """Find a photo by its external ID and connector."""
        stmt = (
            select(PhotoModel)
            .options(
                selectinload(PhotoModel.albums),
                selectinload(PhotoModel.faces),
                selectinload(PhotoModel.connector),
            )
            .where(
                PhotoModel.external_id == external_id,
                PhotoModel.connector_id == connector_id,
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            return PhotoMapper.to_domain(model)
        return None

    async def find_pending_processing(self, limit: int = 100) -> list[Photo]:
        """Find photos pending processing."""
        stmt = (
            select(PhotoModel)
            .options(
                selectinload(PhotoModel.albums),
                selectinload(PhotoModel.faces),
                selectinload(PhotoModel.connector),
            )
            .where(PhotoModel.processing_status == "pending")
            .order_by(PhotoModel.created_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [PhotoMapper.to_domain(model) for model in models]

    async def find_by_connector(
        self,
        connector_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Photo]:
        """Find photos by connector."""
        stmt = (
            select(PhotoModel)
            .options(
                selectinload(PhotoModel.albums),
                selectinload(PhotoModel.faces),
                selectinload(PhotoModel.connector),
            )
            .where(PhotoModel.connector_id == connector_id)
            .order_by(PhotoModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [PhotoMapper.to_domain(model) for model in models]

    async def count_by_connector(self, connector_id: UUID) -> int:
        """Count photos for a specific connector."""
        stmt = select(func.count(PhotoModel.id)).where(PhotoModel.connector_id == connector_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def delete_many(self, photo_ids: list[UUID]) -> int:
        """Delete multiple photos in a single query."""
        if not photo_ids:
            return 0

        stmt = delete(PhotoModel).where(PhotoModel.id.in_(photo_ids))
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def delete_bulk_by_connector(self, connector_id: UUID) -> int:
        """Delete all photos for a connector in a single bulk operation."""
        stmt = delete(PhotoModel).where(PhotoModel.connector_id == connector_id)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def exists_by_external_id(self, connector_id: UUID, external_id: str) -> bool:
        """
        Check if a photo with given external_id exists for a connector.

        Uses an optimized EXISTS query instead of loading the full photo entity.
        This is significantly faster than fetching all photos and checking in memory.
        """
        stmt = select(
            select(PhotoModel.id)
            .where(PhotoModel.connector_id == connector_id)
            .where(PhotoModel.external_id == external_id)
            .exists()
        )
        result = await self._session.execute(stmt)
        exists = result.scalar()
        return bool(exists) if exists is not None else False
