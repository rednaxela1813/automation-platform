#!/usr/bin/env python3
"""Детальная диагностика всех вложений в письмах"""
import sys
import os
import email
import imaplib
from pathlib import Path
sys.path.insert(0, 'src')

from automation.config.settings import settings

print('🔍 ДЕТАЛЬНАЯ ДИАГНОСТИКА ВСЕХ ВЛОЖЕНИЙ')
print('=' * 50)

try:
    with imaplib.IMAP4_SSL(settings.imap_host) as imap:
        imap.login(settings.imap_user, settings.imap_password)
        imap.select(settings.imap_mailbox)
        
        # Получаем ВСЕ письма
        status, data = imap.search(None, 'ALL')
        message_ids = data[0].split() if status == 'OK' else []
        print(f'📧 Всего писем в ящике: {len(message_ids)}')
        
        total_attachments = 0
        
        # Анализируем каждое письмо
        for i, msg_id in enumerate(message_ids):
            print(f'\n--- ПИСЬМО {i+1} (ID: {msg_id.decode()}) ---')
            
            status, msg_data = imap.fetch(msg_id, '(RFC822)')
            if status != 'OK':
                print('❌ Не удалось получить письмо')
                continue
                
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            
            subject = msg.get('Subject', 'No Subject')
            sender = msg.get('From', 'Unknown')
            print(f'Тема: {subject[:60]}')
            print(f'От: {sender}')
            print(f'Multipart: {msg.is_multipart()}')
            
            # Детальный анализ структуры письма
            if not msg.is_multipart():
                print('📄 Простое письмо (не multipart)')
                content_type = msg.get_content_type()
                print(f'Content-Type: {content_type}')
                continue
                
            # Анализ каждой части multipart письма
            attachments_count = 0
            print('📎 Анализируем части письма:')
            
            for part_num, part in enumerate(msg.walk()):
                content_type = part.get_content_type()
                content_disposition = part.get('Content-Disposition')
                filename = part.get_filename()
                
                print(f'  Часть {part_num}:')
                print(f'    Content-Type: {content_type}')
                print(f'    Content-Disposition: {content_disposition}')
                print(f'    Filename: {filename}')
                
                # Это вложение?
                if content_disposition and ('attachment' in content_disposition.lower() or 'inline' in content_disposition.lower()):
                    attachments_count += 1
                    total_attachments += 1
                    
                    if filename:
                        file_ext = Path(filename).suffix.lower()
                        payload_size = len(part.get_payload(decode=True) or b'')
                        
                        print(f'    ⭐ ВЛОЖЕНИЕ #{attachments_count}:')
                        print(f'       Имя: {filename}')
                        print(f'       Расширение: {file_ext}')
                        print(f'       Размер: {payload_size} байт')
                        print(f'       MIME: {content_type}')
                        
                        # Особое внимание к PDF
                        if file_ext == '.pdf' or 'pdf' in content_type.lower():
                            print(f'       🎯 НАЙДЕН PDF!')
                        
                        # Проверяем разрешенные типы
                        allowed_extensions = {'.pdf', '.xlsx', '.xls', '.docx', '.xml', '.png'}
                        if file_ext in allowed_extensions:
                            print(f'       ✅ Тип разрешен')
                        else:
                            print(f'       ❌ Тип запрещен')
                            
            print(f'📊 Вложений в письме: {attachments_count}')
            
        print(f'\n📈 ИТОГО ВЛОЖЕНИЙ ВО ВСЕХ ПИСЬМАХ: {total_attachments}')

except Exception as e:
    print(f'❌ Ошибка: {e}')
    import traceback
    traceback.print_exc()