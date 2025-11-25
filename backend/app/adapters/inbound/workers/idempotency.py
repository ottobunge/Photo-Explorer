"""Task idempotency helpers for Celery workers."""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbound.persistence.postgres.models import TaskExecutionModel
from app.domain.entities.task_execution import TaskExecutionStatus

logger = logging.getLogger(__name__)


async def check_task_completed(
    session: AsyncSession,
    task_id: str,
) -> bool:
    """
    Check if a task has already completed successfully.

    Args:
        session: Database session
        task_id: Celery task ID

    Returns:
        True if task already completed, False otherwise
    """
    stmt = select(TaskExecutionModel).where(
        TaskExecutionModel.task_id == task_id,
        TaskExecutionModel.status == TaskExecutionStatus.COMPLETED.value,
    )
    result = await session.execute(stmt)
    execution = result.scalar_one_or_none()

    if execution is not None:
        logger.info(
            f"Task {task_id} already completed at {execution.completed_at}",
            extra={
                "task_id": task_id,
                "task_name": execution.task_name,
                "completed_at": execution.completed_at,
            },
        )
        return True

    return False


async def mark_task_running(
    session: AsyncSession,
    task_id: str,
    task_name: str,
    context: Optional[dict] = None,
) -> TaskExecutionModel:
    """
    Mark a task as running (or create if doesn't exist).

    Args:
        session: Database session
        task_id: Celery task ID
        task_name: Task function name
        context: Optional context dict

    Returns:
        TaskExecutionModel instance
    """
    # Check if execution record exists
    stmt = select(TaskExecutionModel).where(TaskExecutionModel.task_id == task_id)
    result = await session.execute(stmt)
    execution = result.scalar_one_or_none()

    if execution is None:
        # Create new execution record
        execution = TaskExecutionModel(
            task_id=task_id,
            task_name=task_name,
            status=TaskExecutionStatus.RUNNING.value,
            created_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            context=context,
        )
        session.add(execution)
    else:
        # Update existing record
        execution.status = TaskExecutionStatus.RUNNING.value
        execution.started_at = datetime.utcnow()
        if context:
            execution.context = context

    await session.flush()
    logger.debug(f"Marked task {task_id} as running")
    return execution


async def mark_task_completed(
    session: AsyncSession,
    task_id: str,
    result: Optional[Any] = None,
) -> None:
    """
    Mark a task as completed successfully.

    Args:
        session: Database session
        task_id: Celery task ID
        result: Optional result to store (will be JSON serialized)
    """
    stmt = select(TaskExecutionModel).where(TaskExecutionModel.task_id == task_id)
    result_obj = await session.execute(stmt)
    execution = result_obj.scalar_one_or_none()

    if execution is None:
        logger.warning(f"Task {task_id} not found when marking completed")
        return

    execution.status = TaskExecutionStatus.COMPLETED.value
    execution.completed_at = datetime.utcnow()
    if result is not None:
        try:
            execution.result = json.dumps(result)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize task result: {e}")
            execution.result = str(result)

    await session.flush()
    logger.info(f"Marked task {task_id} as completed")


async def mark_task_failed(
    session: AsyncSession,
    task_id: str,
    error_message: str,
) -> None:
    """
    Mark a task as failed.

    Args:
        session: Database session
        task_id: Celery task ID
        error_message: Error message
    """
    stmt = select(TaskExecutionModel).where(TaskExecutionModel.task_id == task_id)
    result = await session.execute(stmt)
    execution = result.scalar_one_or_none()

    if execution is None:
        logger.warning(f"Task {task_id} not found when marking failed")
        return

    execution.status = TaskExecutionStatus.FAILED.value
    execution.completed_at = datetime.utcnow()
    execution.error_message = error_message[:1000]  # Limit error message length

    await session.flush()
    logger.info(f"Marked task {task_id} as failed: {error_message}")


async def mark_task_retrying(
    session: AsyncSession,
    task_id: str,
) -> None:
    """
    Mark a task as retrying (increment retry count).

    Args:
        session: Database session
        task_id: Celery task ID
    """
    stmt = select(TaskExecutionModel).where(TaskExecutionModel.task_id == task_id)
    result = await session.execute(stmt)
    execution = result.scalar_one_or_none()

    if execution is None:
        logger.warning(f"Task {task_id} not found when marking retrying")
        return

    execution.status = TaskExecutionStatus.RETRYING.value
    execution.retries += 1

    await session.flush()
    logger.info(f"Marked task {task_id} as retrying (attempt {execution.retries})")


async def get_task_context(
    session: AsyncSession,
    task_id: str,
) -> Optional[dict]:
    """
    Get the context for a task execution.

    Args:
        session: Database session
        task_id: Celery task ID

    Returns:
        Context dict or None
    """
    stmt = select(TaskExecutionModel.context).where(TaskExecutionModel.task_id == task_id)
    result = await session.execute(stmt)
    context = result.scalar_one_or_none()
    return context
