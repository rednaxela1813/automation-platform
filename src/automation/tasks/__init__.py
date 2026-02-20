"""
Фоновые задачи для Email Automation Platform
"""

from .email_processing import (
    process_new_emails_task,
    process_single_email_task,
    send_processing_report_task
)

from .file_cleanup import (
    cleanup_old_files_task,
    cleanup_quarantine_task,
    archive_processed_files_task
)

from .monitoring import (
    system_health_check_task,
    generate_daily_metrics_task,
    alert_on_errors_task
)

__all__ = [
    # Email processing tasks
    'process_new_emails_task',
    'process_single_email_task', 
    'send_processing_report_task',
    
    # File cleanup tasks
    'cleanup_old_files_task',
    'cleanup_quarantine_task',
    'archive_processed_files_task',
    
    # Monitoring tasks
    'system_health_check_task',
    'generate_daily_metrics_task',
    'alert_on_errors_task',
]