"""
Celery configuration for background tasks
"""

from __future__ import annotations

import logging

from celery import Celery
from celery.schedules import crontab

from automation.config.logging import configure_logging
from automation.config.settings import settings

configure_logging()
logger = logging.getLogger(__name__)

# Create Celery instance
celery_app = Celery(
    "automation",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "automation.tasks.email_processing",
        "automation.tasks.file_cleanup",
        "automation.tasks.monitoring",
        "automation.tasks.retry_processing",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Timezone
    timezone="UTC",
    # Default task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Task results
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
    },
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    # Task routing
    task_routes={
        "automation.tasks.email_processing.*": {"queue": "email_processing"},
        "automation.tasks.file_cleanup.*": {"queue": "file_cleanup"},
        "automation.tasks.monitoring.*": {"queue": "monitoring"},
        "automation.tasks.retry_processing.*": {"queue": "retry_processing"},
    },
    # Periodic tasks (Celery Beat)
    beat_schedule={
        # Check new email with configured scan interval
        "process-new-emails": {
            "task": "automation.tasks.email_processing.process_new_emails_task",
            "schedule": crontab(minute=f"*/{settings.scan_interval_minutes}"),
            "options": {"queue": "email_processing"},
        },
        # Clean old files daily at 2:00
        "cleanup-old-files": {
            "task": "automation.tasks.file_cleanup.cleanup_old_files_task",
            "schedule": crontab(hour=2, minute=0),
            "options": {"queue": "file_cleanup"},
        },
        # Monitor system state every 10 minutes
        "system-health-check": {
            "task": "automation.tasks.monitoring.system_health_check_task",
            "schedule": crontab(minute="*/10"),
            "options": {"queue": "monitoring"},
        },
        # Retry failed invoices every 30 minutes
        "retry-failed-invoices": {
            "task": "automation.tasks.retry_processing.retry_failed_invoices_task",
            "schedule": crontab(minute="*/30"),
            "options": {"queue": "retry_processing"},
        },
        # Cleanup old database records weekly
        "cleanup-old-records": {
            "task": "automation.tasks.retry_processing.cleanup_old_records_task",
            "schedule": crontab(hour=3, minute=0, day_of_week=1),  # Monday 3:00 AM
            "options": {"queue": "retry_processing"},
        },
    },
)


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for Celery verification"""
    logger.info("Celery debug task request: %r", self.request)
    return {"status": "success", "message": "Debug task completed"}


# Configure Celery logging
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Configure periodic tasks after Celery setup"""

    # Additional periodic tasks can be added here
    # sender.add_periodic_task(
    #     crontab(minute=0, hour="*/4"),  # every 4 hours
    #     custom_task.s(),
    # )
    pass


if __name__ == "__main__":
    celery_app.start()
