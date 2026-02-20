"""
Конфигурация Celery для фоновых задач
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from automation.config.settings import settings


# Создаем экземпляр Celery
celery_app = Celery(
    "automation",
    broker=f"redis://localhost:6379/0",
    backend=f"redis://localhost:6379/0",
    include=[
        "automation.tasks.email_processing",
        "automation.tasks.file_cleanup",
        "automation.tasks.monitoring"
    ]
)

# Конфигурация Celery
celery_app.conf.update(
    # Часовой пояс
    timezone="UTC",
    
    # Настройки задач по умолчанию
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Результаты задач
    result_expires=3600,  # 1 час
    result_backend_transport_options={
        "master_name": "mymaster",
    },
    
    # Настройки worker'а
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Маршrutирование задач
    task_routes={
        "automation.tasks.email_processing.*": {"queue": "email_processing"},
        "automation.tasks.file_cleanup.*": {"queue": "file_cleanup"},
        "automation.tasks.monitoring.*": {"queue": "monitoring"},
    },
    
    # Периодические задачи (Celery Beat)
    beat_schedule={
        # Проверка новых email каждые 5 минут
        "process-new-emails": {
            "task": "automation.tasks.email_processing.process_new_emails_task",
            "schedule": crontab(minute="*/5"),
            "options": {"queue": "email_processing"}
        },
        
        # Очистка старых файлов каждый день в 2:00
        "cleanup-old-files": {
            "task": "automation.tasks.file_cleanup.cleanup_old_files_task",
            "schedule": crontab(hour=2, minute=0),
            "options": {"queue": "file_cleanup"}
        },
        
        # Мониторинг состояния системы каждые 10 минут
        "system-health-check": {
            "task": "automation.tasks.monitoring.system_health_check_task",
            "schedule": crontab(minute="*/10"),
            "options": {"queue": "monitoring"}
        },
    },
)


@celery_app.task(bind=True)
def debug_task(self):
    """Отладочная задача для проверки работы Celery"""
    print(f'Request: {self.request!r}')
    return {"status": "success", "message": "Debug task completed"}


# Настройка логирования для Celery
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Настроить периодические задачи после конфигурации Celery"""
    
    # Дополнительные периодические задачи можно добавлять здесь
    # sender.add_periodic_task(
    #     crontab(minute=0, hour="*/4"),  # каждые 4 часа
    #     custom_task.s(),
    # )
    pass


if __name__ == "__main__":
    celery_app.start()