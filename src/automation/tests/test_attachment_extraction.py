#!/usr/bin/env python3
"""Attachment extraction test"""
import sys
import os
sys.path.insert(0, 'src')

from automation.adapters.email_imap import ImapEmailClient

print('🧪 ATTACHMENT EXTRACTION TEST')
print('=' * 50)

try:
    client = ImapEmailClient()
    messages = client.fetch_unseen_messages()  # Now searching ALL
    
    print(f'📧 Messages found: {len(messages)}')
    
    for i, msg in enumerate(messages):
        print(f'\n--- MESSAGE {i+1} ---')
        print(f'Subject: {msg.subject[:50]}...')
        print(f'Attachments detected by system: {len(msg.attachments)}')
        
        for j, att in enumerate(msg.attachments):
            print(f'  Attachment {j+1}:')
            print(f'    Name: {att.filename}')
            print(f'    Type: {att.content_type}')
            print(f'    Size: {att.size} bytes')
            
            # Special attention to PDF
            if att.filename.lower().endswith('.pdf'):
                print(f'    🎯 THIS IS A PDF FILE!')

except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()