"""
Порты для работы с файловым хранилищем
Определяют интерфейсы для безопасного хранения и карантина файлов
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol
from pathlib import Path
from enum import Enum

from automation.ports.email import EmailAttachment


class FileStorageResult(Enum):
    """Результат сохранения файла"""
    SAFE_STORAGE = "safe_storage"
    QUARANTINE = "quarantine" 
    REJECTED = "rejected"


class FileStorageService(Protocol):
    """Интерфейс для файлового хранилища"""
    
    def store_attachment(self, attachment: EmailAttachment) -> tuple[FileStorageResult, str]:
        """
        Сохранить вложение в соответствующее хранилище
        
        Returns:
            tuple: (результат, путь к файлу или причина отклонения)
        """
        ...
    
    def is_file_safe(self, attachment: EmailAttachment) -> bool:
        """Проверить безопасность файла"""
        ...
    
    def get_safe_files(self) -> list[Path]:
        """Получить список файлов в безопасном хранилище"""
        ...
    
    def get_quarantine_files(self) -> list[Path]:
        """Получить список файлов в карантине"""
        ...
    
    def delete_quarantine_file(self, filename: str) -> bool:
        """Удалить файл из карантина"""
        ...