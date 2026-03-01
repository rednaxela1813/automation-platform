#!/usr/bin/env python3
"""
Простая диагностика IMAP подключения
"""
import sys
import os
sys.path.insert(0, 'src')

from automation.config.settings import settings
import imaplib

def test_imap_connection():
    print('🔧 Проверка настроек IMAP:')
    print(f'IMAP Host: {settings.imap_host}')
    print(f'IMAP User: {settings.imap_user}')
    print(f'IMAP Password: {"*" * len(settings.imap_password)}')
    print(f'IMAP Mailbox: {settings.imap_mailbox}')
    
    try:
        print(f'\n🔌 Пробуем подключиться к {settings.imap_host}...')
        
        with imaplib.IMAP4_SSL(settings.imap_host) as imap:
            print('✅ SSL подключение установлено')
            
            result = imap.login(settings.imap_user, settings.imap_password)
            print(f'✅ Авторизация успешна: {result}')
            
            # Выбираем почтовый ящик
            status, count = imap.select(settings.imap_mailbox)
            print(f'📬 Почтовый ящик "{settings.imap_mailbox}": {status}, писем: {count[0].decode()}')
            
            # Проверяем последние письма
            status, messages = imap.search(None, 'ALL')
            message_ids = messages[0].split()
            print(f'📧 Всего писем в ящике: {len(message_ids)}')
            
            if message_ids:
                print(f'🔢 ID последних писем: {message_ids[-5:]}')
            
            imap.logout()
            return True
            
    except Exception as e:
        print(f'❌ Ошибка подключения IMAP: {str(e)}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_imap_connection()