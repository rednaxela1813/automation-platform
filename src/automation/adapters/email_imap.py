from __future__ import annotations

import email
import imaplib
from email.message import Message
from typing import List
from datetime import datetime

from automation.config.settings import settings
from automation.ports.email import EmailMessage, EmailAttachment


class ImapEmailClient:
    def __init__(self) -> None:
        self.host = settings.imap_host
        self.username = settings.imap_user
        self.password = settings.imap_password
        self.mailbox = settings.imap_mailbox

    def fetch_new_messages(self) -> List[EmailMessage]:
        """Получить непрочитанные сообщения и конвертировать в EmailMessage"""
        with imaplib.IMAP4_SSL(self.host) as imap:
            imap.login(self.username, self.password)
            imap.select(self.mailbox)

            status, data = imap.search(None, "UNSEEN")
            if status != "OK":
                return []

            messages = []
            for msg_id in data[0].split():
                status, msg_data = imap.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                
                # Конвертируем email.Message в EmailMessage
                email_message = self._convert_to_email_message(msg, msg_id.decode())
                messages.append(email_message)

            return messages

    def mark_as_processed(self, message_id: str) -> bool:
        """Отметить сообщение как обработанное (SEEN)"""
        try:
            with imaplib.IMAP4_SSL(self.host) as imap:
                imap.login(self.username, self.password)
                imap.select(self.mailbox)
                status, _ = imap.store(message_id, "+FLAGS", "\\Seen")
                return status == "OK"
        except Exception:
            return False

    # Backward-compatible alias (can be removed after full codebase update)
    def fetch_unseen_messages(self) -> List[EmailMessage]:
        return self.fetch_new_messages()
    
    def _convert_to_email_message(self, msg: Message, msg_id: str) -> EmailMessage:
        """Конвертировать email.Message в EmailMessage"""
        
        # Извлекаем основные поля
        subject = msg.get('Subject', 'No Subject')
        sender = msg.get('From', 'Unknown Sender')
        date = msg.get('Date', str(datetime.now()))
        
        # Извлекаем текст письма
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
        else:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        
        # Извлекаем вложения
        attachments = self._extract_attachments(msg)
        
        return EmailMessage(
            message_id=msg_id,
            subject=subject,
            sender=sender,
            received_date=date,
            body=body,
            attachments=attachments
        )
    
    def _extract_attachments(self, msg: Message) -> List[EmailAttachment]:
        """Извлечь вложения из сообщения"""
        attachments = []
        
        if not msg.is_multipart():
            return attachments
            
        for part in msg.walk():
            # Пропускаем основное тело письма
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
                
            filename = part.get_filename()
            if filename:
                content = part.get_payload(decode=True)
                if content:
                    attachment = EmailAttachment(
                        filename=filename,
                        content_type=part.get_content_type(),
                        content=content,
                        size=len(content)
                    )
                    attachments.append(attachment)
        
        return attachments
