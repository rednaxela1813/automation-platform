"""
Адаптер для локального файлового хранилища
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from automation.ports.email import EmailAttachment
from automation.ports.file_storage import FileStorageService, FileStorageResult
from automation.config.settings import settings


class LocalFileStorage:
    """Реализация файлового хранилища на локальной файловой системе"""
    
    def __init__(self):
        self.safe_storage_dir = Path(settings.safe_storage_dir)
        self.quarantine_dir = Path(settings.quarantine_dir)
        
        # Создаем директории если их нет
        self.safe_storage_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        
        # Разрешенные расширения файлов
        self.allowed_extensions = {'.pdf', '.xlsx', '.xls', '.docx', '.xml'}
        
        # Максимальный размер файла в байтах
        self.max_file_size = settings.max_file_size_mb * 1024 * 1024
    
    def store_attachment(self, attachment: EmailAttachment) -> tuple[FileStorageResult, str]:
        """Сохранить вложение в соответствующее хранилище"""
        
        # Проверки безопасности
        if not self.is_file_safe(attachment):
            reason = self._get_rejection_reason(attachment)
            quarantine_path = self._save_to_quarantine(attachment)
            return FileStorageResult.QUARANTINE, str(quarantine_path)
        
        # Сохраняем в безопасное хранилище
        safe_path = self._save_to_safe_storage(attachment)
        return FileStorageResult.SAFE_STORAGE, str(safe_path)
    
    def is_file_safe(self, attachment: EmailAttachment) -> bool:
        """Проверить безопасность файла"""
        
        # Проверка расширения
        if not self._has_allowed_extension(attachment.filename):
            return False
        
        # Проверка размера
        if attachment.size > self.max_file_size:
            return False
        
        # Проверка MIME типа
        if not self._has_valid_mime_type(attachment):
            return False
        
        # Проверка на вредоносное содержимое (базовая)
        if self._contains_suspicious_content(attachment):
            return False
        
        return True
    
    def get_safe_files(self) -> List[Path]:
        """Получить список файлов в безопасном хранилище"""
        return list(self.safe_storage_dir.glob('**/*'))
    
    def get_quarantine_files(self) -> List[Path]:
        """Получить список файлов в карантине"""
        return list(self.quarantine_dir.glob('**/*'))
    
    def delete_quarantine_file(self, filename: str) -> bool:
        """Удалить файл из карантина"""
        file_path = self.quarantine_dir / filename
        
        try:
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                return True
            return False
        except (OSError, PermissionError):
            return False
    
    def get_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Получить информацию о файле"""
        if not file_path.exists():
            return None
        
        stat = file_path.stat()
        return {
            'name': file_path.name,
            'size': stat.st_size,
            'created': datetime.fromtimestamp(stat.st_ctime),
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'extension': file_path.suffix.lower(),
            'hash': self._calculate_file_hash(file_path)
        }
    
    def _save_to_safe_storage(self, attachment: EmailAttachment) -> Path:
        """Сохранить файл в безопасное хранилище"""
        safe_filename = self._generate_safe_filename(attachment)
        file_path = self.safe_storage_dir / safe_filename
        
        # Записываем файл
        with open(file_path, 'wb') as f:
            f.write(attachment.content)
        
        # Создаем метаданные
        self._save_metadata(file_path, attachment)
        
        return file_path
    
    def _save_to_quarantine(self, attachment: EmailAttachment) -> Path:
        """Сохранить файл в карантин"""
        quarantine_filename = f"quarantine_{self._generate_safe_filename(attachment)}"
        file_path = self.quarantine_dir / quarantine_filename
        
        with open(file_path, 'wb') as f:
            f.write(attachment.content)
        
        # Сохраняем причину помещения в карантин
        self._save_quarantine_info(file_path, attachment)
        
        return file_path
    
    def _generate_safe_filename(self, attachment: EmailAttachment) -> str:
        """Генерировать безопасное имя файла"""
        # Создаем хеш содержимого для уникальности
        content_hash = hashlib.md5(attachment.content).hexdigest()[:8]
        
        # Очищаем оригинальное имя файла
        safe_name = self._sanitize_filename(attachment.filename)
        
        # Добавляем timestamp и хеш
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        name_part = Path(safe_name).stem
        extension = Path(safe_name).suffix
        
        return f"{timestamp}_{content_hash}_{name_part}{extension}"
    
    def _sanitize_filename(self, filename: str) -> str:
        """Очистить имя файла от опасных символов"""
        import re
        
        # Удаляем опасные символы
        safe_chars = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        
        # Ограничиваем длину
        if len(safe_chars) > 100:
            name_part = safe_chars[:90]
            extension = Path(filename).suffix[:10]
            safe_chars = name_part + extension
        
        return safe_chars
    
    def _has_allowed_extension(self, filename: str) -> bool:
        """Проверить разрешенное расширение файла"""
        extension = Path(filename).suffix.lower()
        return extension in self.allowed_extensions
    
    def _has_valid_mime_type(self, attachment: EmailAttachment) -> bool:
        """Проверить MIME тип файла"""
        allowed_mime_types = {
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
            'application/vnd.ms-excel',  # .xls
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
            'application/xml',
            'text/xml'
        }
        
        return attachment.content_type in allowed_mime_types
    
    def _contains_suspicious_content(self, attachment: EmailAttachment) -> bool:
        """Базовая проверка на вредоносное содержимое"""
        
        # Проверяем первые байты файла на подозрительные паттерны
        content_start = attachment.content[:1024].decode('utf-8', errors='ignore')
        
        suspicious_patterns = [
            'javascript:',
            '<script',
            'eval(',
            'document.write',
            'shell_exec',
            'system(',
        ]
        
        content_lower = content_start.lower()
        for pattern in suspicious_patterns:
            if pattern in content_lower:
                return True
        
        return False
    
    def _get_rejection_reason(self, attachment: EmailAttachment) -> str:
        """Получить причину отклонения файла"""
        reasons = []
        
        if not self._has_allowed_extension(attachment.filename):
            reasons.append(f"Недопустимое расширение: {Path(attachment.filename).suffix}")
        
        if attachment.size > self.max_file_size:
            reasons.append(f"Превышен размер файла: {attachment.size / (1024*1024):.1f}MB")
        
        if not self._has_valid_mime_type(attachment):
            reasons.append(f"Недопустимый MIME тип: {attachment.content_type}")
        
        if self._contains_suspicious_content(attachment):
            reasons.append("Обнаружено подозрительное содержимое")
        
        return "; ".join(reasons) if reasons else "Неизвестная причина"
    
    def _save_metadata(self, file_path: Path, attachment: EmailAttachment) -> None:
        """Сохранить метаданные файла"""
        metadata = {
            'original_filename': attachment.filename,
            'content_type': attachment.content_type,
            'size': attachment.size,
            'stored_at': datetime.now().isoformat(),
            'file_hash': hashlib.sha256(attachment.content).hexdigest()
        }
        
        metadata_path = file_path.with_suffix('.metadata.json')
        
        import json
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def _save_quarantine_info(self, file_path: Path, attachment: EmailAttachment) -> None:
        """Сохранить информацию о файле в карантине"""
        quarantine_info = {
            'original_filename': attachment.filename,
            'content_type': attachment.content_type,
            'size': attachment.size,
            'quarantined_at': datetime.now().isoformat(),
            'quarantine_reason': self._get_rejection_reason(attachment),
            'file_hash': hashlib.sha256(attachment.content).hexdigest()
        }
        
        info_path = file_path.with_suffix('.quarantine_info.json')
        
        import json
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(quarantine_info, f, indent=2, ensure_ascii=False)
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Вычислить хеш файла"""
        hash_sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()