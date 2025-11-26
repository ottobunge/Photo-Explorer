"""Metrics endpoint for Prometheus scraping."""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import REGISTRY, generate_latest

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> str:
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text exposition format for scraping.
    Includes Celery task metrics:
    - celery_task_duration_seconds: Task execution time histogram
    - celery_task_failures_total: Task failure counter
    - celery_task_success_total: Task success counter
    - celery_task_retries_total: Task retry counter
    - celery_active_tasks: Currently executing tasks gauge
    """
    return generate_latest(REGISTRY).decode("utf-8")
