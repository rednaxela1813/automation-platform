#!/usr/bin/env python3
"""Тестирование извлечения вложений"""
import sys
import os
sys.path.insert(0, 'src')

from automation.adapters.email_imap import ImapEmailClient

print('🧪 ТЕСТИРОВАНИЕ ИЗВЛЕЧЕНИЯ ВЛОЖЕНИЙ')
print('=' * 50)

try:
    client = ImapEmailClient()
    messages = client.fetch_unseen_messages()  # Теперь ищет ALL
    
    print(f'📧 Найдено сообщений: {len(messages)}')
    
    for i, msg in enumerate(messages):
        print(f'\n--- СООБЩЕНИЕ {i+1} ---')
        print(f'Тема: {msg.subject[:50]}...')
        print(f'Вложений найдено системой: {len(msg.attachments)}')
        
        for j, att in enumerate(msg.attachments):
            print(f'  Вложение {j+1}:')
            print(f'    Имя: {att.filename}')
            print(f'    Тип: {att.content_type}')
            print(f'    Размер: {att.size} байт')
            
            # Особое внимание к PDF
            if att.filename.lower().endswith('.pdf'):
                print(f'    🎯 ЭТО PDF ФАЙЛ!')

except Exception as e:
    print(f'❌ Ошибка: {e}')
    import traceback
    traceback.print_exc()