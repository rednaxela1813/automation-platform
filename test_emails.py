#!/usr/bin/env python3
"""Simple email test"""
import sys
import os
sys.path.insert(0, 'src')

import imaplib
from automation.config.settings import settings

print('🔍 Checking ALL emails in mailbox...')

try:
    with imaplib.IMAP4_SSL(settings.imap_host) as imap:
        imap.login(settings.imap_user, settings.imap_password)
        imap.select(settings.imap_mailbox)
        
        # Searching ALL emails
        status, data = imap.search(None, 'ALL')
        message_ids = data[0].split() if status == 'OK' else []
        print(f'📧 Total emails: {len(message_ids)}')
        
        # Searching unread
        status2, data2 = imap.search(None, 'UNSEEN')  
        unseen_ids = data2[0].split() if status2 == 'OK' else []
        print(f'📩 Unread: {len(unseen_ids)}')
        
        # Checking last 2 emails for attachments
        for i, msg_id in enumerate(message_ids[-2:]):
            status, msg_data = imap.fetch(msg_id, '(RFC822)')
            if status == 'OK':
                import email
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                
                subject = msg.get('Subject', 'No Subject')
                print(f'\n--- Email {i+1} ---')
                print(f'Subject: {subject[:50]}')
                
                # Looking for attachments
                attachments = []
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get('Content-Disposition') and part.get_filename():
                            attachments.append(part.get_filename())
                
                print(f'Attachments ({len(attachments)}): {attachments}')

except Exception as e:
    print(f'❌ Error: {e}')