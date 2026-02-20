"""
Порты для работы с электронной почтой
Определяют интерфейсы для обработки email сообщений и вложений
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Protocol
from dataclasses import dataclass
from email.message import Message


@dataclass(frozen=True)
class EmailAttachment:
    """Модель вложения электронного письма"""
    filename: str
    content_type: str
    content: bytes
    size: int


@dataclass(frozen=True) 
class EmailMessage:
    """Модель электронного сообщения"""
    message_id: str
    subject: str
    sender: str
    received_date: str
    body: str
    attachments: List[EmailAttachment]


class EmailProcessor(Protocol):
    """Интерфейс для обработки электронной почты"""
    
    def fetch_new_messages(self) -> List[EmailMessage]:
        """Получить новые сообщения из почтового ящика"""
        ...
    
    def extract_attachments(self, message: Message) -> List[EmailAttachment]:
        """Извлечь вложения из сообщения"""
        ...
    
    def mark_as_processed(self, message_id: str) -> bool:
        """Отметить сообщение как обработанное"""
        ...