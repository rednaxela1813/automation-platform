"""
Background tasks for Email Automation Platform
"""

from .email_processing import (
    process_new_emails_task,
    process_single_email_task,
    send_processing_report_task,
)
from .file_cleanup import (
    archive_processed_files_task,
    cleanup_old_files_task,
    cleanup_quarantine_task,
)
from .monitoring import alert_on_errors_task, generate_daily_metrics_task, system_health_check_task

__all__ = [
    # Email processing tasks
    "process_new_emails_task",
    "process_single_email_task",
    "send_processing_report_task",
    # File cleanup tasks
    "cleanup_old_files_task",
    "cleanup_quarantine_task",
    "archive_processed_files_task",
    # Monitoring tasks
    "system_health_check_task",
    "generate_daily_metrics_task",
    "alert_on_errors_task",
]
