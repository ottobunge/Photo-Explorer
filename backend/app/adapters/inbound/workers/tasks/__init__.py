# Celery tasks
from app.adapters.inbound.workers.tasks.photo_processing import (
    detect_faces_task,
    process_photo_task,
    reprocess_photo_task,
)
from app.adapters.inbound.workers.tasks.face_clustering import (
    cluster_faces_task,
    update_clusters_task,
    merge_clusters_task,
)
from app.adapters.inbound.workers.tasks.connector_sync import (
    sync_local_folder_task,
    index_single_file_task,
    handle_file_deleted_task,
    handle_file_moved_task,
)
from app.adapters.inbound.workers.tasks.google_photos_sync import (
    sync_google_photos_task,
    refresh_photo_url_task,
    fetch_google_photo_bytes_task,
    schedule_google_photos_sync,
)
from app.adapters.inbound.workers.tasks.photo_analysis import (
    analyze_photo_task,
    generate_description_task,
    answer_question_task,
    batch_analyze_task,
    analyze_pending_photos,
)

__all__ = [
    # Photo processing
    "process_photo_task",
    "detect_faces_task",
    "reprocess_photo_task",
    # Photo analysis (vision LLM)
    "analyze_photo_task",
    "generate_description_task",
    "answer_question_task",
    "batch_analyze_task",
    "analyze_pending_photos",
    # Face clustering
    "cluster_faces_task",
    "update_clusters_task",
    "merge_clusters_task",
    # Local folder sync
    "sync_local_folder_task",
    "index_single_file_task",
    "handle_file_deleted_task",
    "handle_file_moved_task",
    # Google Photos sync
    "sync_google_photos_task",
    "refresh_photo_url_task",
    "fetch_google_photo_bytes_task",
    "schedule_google_photos_sync",
]
