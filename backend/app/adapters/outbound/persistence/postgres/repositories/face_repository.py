"""PostgreSQL implementation of FaceRepository."""

from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.adapters.outbound.persistence.postgres.mappers import FaceClusterMapper, FaceMapper
from app.adapters.outbound.persistence.postgres.models import FaceClusterModel, FaceModel
from app.application.ports.outbound import FaceRepository
from app.domain.entities import Face, FaceCluster


class FaceRepositoryPostgres(FaceRepository):
    """PostgreSQL implementation of FaceRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # Face operations

    async def save_face(self, face: Face) -> Face:
        """Persist a face entity."""
        # Check if face already exists
        existing = await self._session.get(FaceModel, face.id.value)

        if existing:
            # Update existing face
            existing.photo_id = face.photo_id
            existing.cluster_id = face.cluster_id
            existing.bbox_x = face.bbox.x
            existing.bbox_y = face.bbox.y
            existing.bbox_width = face.bbox.width
            existing.bbox_height = face.bbox.height
            existing.crop_path = face.crop_path
            existing.quality_score = face.quality_score
            existing.detection_confidence = face.detection_confidence

            await self._session.flush()
            return FaceMapper.to_domain(existing)
        else:
            # Create new face
            model = FaceMapper.to_model(face)
            self._session.add(model)
            await self._session.flush()
            return FaceMapper.to_domain(model)

    async def find_face_by_id(self, face_id: UUID) -> Optional[Face]:
        """Find a face by its ID."""
        model = await self._session.get(FaceModel, face_id)
        if model:
            return FaceMapper.to_domain(model)
        return None

    async def find_faces_by_photo(self, photo_id: UUID) -> list[Face]:
        """Find all faces in a photo."""
        stmt = select(FaceModel).where(FaceModel.photo_id == photo_id)
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [FaceMapper.to_domain(model) for model in models]

    async def find_faces_by_cluster(
        self, cluster_id: UUID, limit: int | None = None, offset: int = 0
    ) -> list[Face]:
        """Find all faces in a cluster with optional pagination."""
        stmt = select(FaceModel).where(FaceModel.cluster_id == cluster_id)

        # Add pagination if limit is specified
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [FaceMapper.to_domain(model) for model in models]

    async def delete_face(self, face_id: UUID) -> bool:
        """Delete a face."""
        model = await self._session.get(FaceModel, face_id)
        if model:
            await self._session.delete(model)
            await self._session.flush()
            return True
        return False

    # Cluster operations

    async def save_cluster(self, cluster: FaceCluster) -> FaceCluster:
        """Persist a face cluster."""
        # Check if cluster already exists
        existing = await self._session.get(FaceClusterModel, cluster.id.value)

        if existing:
            # Update existing cluster
            existing.name = cluster.name
            existing.representative_face_id = cluster.representative_face_id
            existing.updated_at = cluster.updated_at

            await self._session.flush()
            await self._session.refresh(existing, ["faces"])
            return FaceClusterMapper.to_domain(existing)
        else:
            # Create new cluster
            model = FaceClusterMapper.to_model(cluster)
            self._session.add(model)
            await self._session.flush()
            await self._session.refresh(model, ["faces"])
            return FaceClusterMapper.to_domain(model)

    async def find_cluster_by_id(self, cluster_id: UUID) -> Optional[FaceCluster]:
        """Find a cluster by its ID."""
        stmt = (
            select(FaceClusterModel)
            .options(selectinload(FaceClusterModel.faces))
            .where(FaceClusterModel.id == cluster_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            return FaceClusterMapper.to_domain(model)
        return None

    async def find_all_clusters(
        self,
        named_only: bool = False,
        unnamed_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[FaceCluster]:
        """Find clusters with optional filtering."""
        stmt = (
            select(FaceClusterModel)
            .options(selectinload(FaceClusterModel.faces))
            .order_by(FaceClusterModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if named_only:
            stmt = stmt.where(
                and_(
                    FaceClusterModel.name.isnot(None),
                    FaceClusterModel.name != "",
                )
            )
        elif unnamed_only:
            stmt = stmt.where(
                or_(
                    FaceClusterModel.name.is_(None),
                    FaceClusterModel.name == "",
                )
            )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [FaceClusterMapper.to_domain(model) for model in models]

    async def delete_cluster(self, cluster_id: UUID) -> bool:
        """Delete a cluster."""
        model = await self._session.get(FaceClusterModel, cluster_id)
        if model:
            # Unassign faces from cluster before deleting
            await self._session.execute(
                update(FaceModel)
                .where(FaceModel.cluster_id == cluster_id)
                .values(cluster_id=None)
            )
            await self._session.delete(model)
            await self._session.flush()
            return True
        return False

    async def count_clusters(self, named_only: bool = False) -> int:
        """Count clusters."""
        stmt = select(func.count(FaceClusterModel.id))

        if named_only:
            stmt = stmt.where(
                and_(
                    FaceClusterModel.name.isnot(None),
                    FaceClusterModel.name != "",
                )
            )

        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def find_photo_ids_by_cluster(
        self,
        cluster_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[UUID]:
        """Find photo IDs containing faces from a cluster."""
        stmt = (
            select(FaceModel.photo_id)
            .distinct()
            .where(FaceModel.cluster_id == cluster_id)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_unclustered_faces(self, limit: int = 100) -> list[Face]:
        """Find faces that haven't been assigned to a cluster yet."""
        stmt = select(FaceModel).where(FaceModel.cluster_id.is_(None)).limit(limit)
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [FaceMapper.to_domain(model) for model in models]

    async def count_faces_in_cluster(self, cluster_id: UUID) -> int:
        """Count faces in a cluster."""
        stmt = select(func.count(FaceModel.id)).where(FaceModel.cluster_id == cluster_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def batch_update_cluster(self, face_ids: list[UUID], cluster_id: UUID | None) -> int:
        """Update cluster assignment for multiple faces at once."""
        if not face_ids:
            return 0

        stmt = (
            update(FaceModel)
            .where(FaceModel.id.in_(face_ids))
            .values(cluster_id=cluster_id)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def save_faces_batch(self, faces: list[Face]) -> list[Face]:
        """
        Persist multiple face entities in a single batch operation.

        This reduces database round-trips from N to 1 for bulk face saves.
        """
        if not faces:
            return []

        # Separate into new and existing faces
        face_ids = [face.id.value for face in faces]
        stmt = select(FaceModel).where(FaceModel.id.in_(face_ids))
        result = await self._session.execute(stmt)
        existing_models = {model.id: model for model in result.scalars().all()}

        saved_faces = []

        for face in faces:
            if face.id.value in existing_models:
                # Update existing face
                existing = existing_models[face.id.value]
                existing.photo_id = face.photo_id
                existing.cluster_id = face.cluster_id
                existing.bbox_x = face.bbox.x
                existing.bbox_y = face.bbox.y
                existing.bbox_width = face.bbox.width
                existing.bbox_height = face.bbox.height
                existing.crop_path = face.crop_path
                existing.quality_score = face.quality_score
                existing.detection_confidence = face.detection_confidence
                saved_faces.append(FaceMapper.to_domain(existing))
            else:
                # Create new face
                model = FaceMapper.to_model(face)
                self._session.add(model)
                saved_faces.append(face)

        # Single flush for all operations
        await self._session.flush()
        return saved_faces

    async def find_faces_by_ids(self, face_ids: list[UUID]) -> list[Face]:
        """Find multiple faces by IDs in a single query."""
        if not face_ids:
            return []

        stmt = select(FaceModel).where(FaceModel.id.in_(face_ids))
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [FaceMapper.to_domain(model) for model in models]

    async def count_photos_by_cluster(self, cluster_id: UUID) -> int:
        """Count unique photos in a cluster without loading all photo IDs."""
        stmt = select(func.count(func.distinct(FaceModel.photo_id))).where(
            FaceModel.cluster_id == cluster_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def count_photos_by_clusters_batch(
        self, cluster_ids: list[UUID]
    ) -> dict[UUID, int]:
        """
        Count unique photos for multiple clusters in a single batch query.

        Uses GROUP BY to aggregate all photo counts in one query,
        eliminating N+1 queries.
        """
        if not cluster_ids:
            return {}

        # Query groups by cluster_id and counts distinct photos
        stmt = (
            select(
                FaceModel.cluster_id,
                func.count(func.distinct(FaceModel.photo_id)).label("photo_count"),
            )
            .where(FaceModel.cluster_id.in_(cluster_ids))
            .group_by(FaceModel.cluster_id)
        )
        result = await self._session.execute(stmt)

        # Build dictionary mapping cluster_id -> photo_count
        photo_counts: dict[UUID, int] = {}
        for row in result.all():
            if row.cluster_id is not None:
                photo_counts[row.cluster_id] = row.photo_count

        # Ensure all requested cluster IDs are in the result (default to 0)
        for cluster_id in cluster_ids:
            if cluster_id not in photo_counts:
                photo_counts[cluster_id] = 0

        return photo_counts

    async def get_co_appearances(
        self,
        cluster_id: UUID | None = None,
    ) -> list[tuple[UUID, UUID, int]]:
        """
        Get all face co-appearances (people appearing together in photos).

        Uses a self-join to find all pairs of faces that appear in the same photo,
        then groups by cluster IDs to count co-appearances.
        """
        f1 = aliased(FaceModel)
        f2 = aliased(FaceModel)

        # Build query: find all pairs of faces in the same photo
        query = (
            select(
                f1.cluster_id.label("cluster_a"),
                f2.cluster_id.label("cluster_b"),
                func.count(func.distinct(f1.photo_id)).label("photo_count"),
            )
            .select_from(f1)
            .join(f2, f1.photo_id == f2.photo_id)
            .where(
                f1.cluster_id.isnot(None),  # Only clustered faces
                f2.cluster_id.isnot(None),
                f1.cluster_id < f2.cluster_id,  # Avoid duplicates (a,b) and (b,a)
            )
            .group_by(f1.cluster_id, f2.cluster_id)
        )

        # Optional filter: only co-appearances for a specific person
        if cluster_id is not None:
            query = query.where(
                or_(f1.cluster_id == cluster_id, f2.cluster_id == cluster_id)
            )

        result = await self._session.execute(query)
        rows = result.all()

        return [(row.cluster_a, row.cluster_b, row.photo_count) for row in rows]

    async def get_shared_photos(
        self,
        person_a_id: UUID,
        person_b_id: UUID,
    ) -> list[UUID]:
        """
        Get IDs of all photos where two people appear together.

        Uses a self-join to find photos containing both cluster IDs.
        """
        f1 = aliased(FaceModel)
        f2 = aliased(FaceModel)

        query = (
            select(f1.photo_id)
            .select_from(f1)
            .join(f2, f1.photo_id == f2.photo_id)
            .where(
                f1.cluster_id == person_a_id,
                f2.cluster_id == person_b_id,
            )
            .distinct()
        )

        result = await self._session.execute(query)
        return [row[0] for row in result.all()]
