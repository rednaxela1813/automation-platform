#!/usr/bin/env python3
"""Simple email test"""
import sys
import os
sys.path.insert(0, 'src')

import imaplib
from automation.config.settings import settings

print('🔍 Проверяем ВСЕ письма в ящике...')

try:
    with imaplib.IMAP4_SSL(settings.imap_host) as imap:
        imap.login(settings.imap_user, settings.imap_password)
        imap.select(settings.imap_mailbox)
        
        # Ищем ВСЕ письма
        status, data = imap.search(None, 'ALL')
        message_ids = data[0].split() if status == 'OK' else []
        print(f'📧 Всего писем: {len(message_ids)}')
        
        # Ищем непрочитанные
        status2, data2 = imap.search(None, 'UNSEEN')  
        unseen_ids = data2[0].split() if status2 == 'OK' else []
        print(f'📩 Непрочитанных: {len(unseen_ids)}')
        
        # Проверяем последние 2 письма на вложения
        for i, msg_id in enumerate(message_ids[-2:]):
            status, msg_data = imap.fetch(msg_id, '(RFC822)')
            if status == 'OK':
                import email
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                
                subject = msg.get('Subject', 'No Subject')
                print(f'\n--- Письмо {i+1} ---')
                print(f'Тема: {subject[:50]}')
                
                # Ищем вложения
                attachments = []
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get('Content-Disposition') and part.get_filename():
                            attachments.append(part.get_filename())
                
                print(f'Вложения ({len(attachments)}): {attachments}')

except Exception as e:
    print(f'❌ Ошибка: {e}')