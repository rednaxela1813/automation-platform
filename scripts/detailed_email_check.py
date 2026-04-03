#!/usr/bin/env python3
"""Detailed diagnostics of all email attachments"""
import sys
import os
import email
import imaplib
from pathlib import Path
sys.path.insert(0, 'src')

from automation.config.settings import settings

print('🔍 DETAILED DIAGNOSTICS OF ALL ATTACHMENTS')
print('=' * 50)

try:
    with imaplib.IMAP4_SSL(settings.imap_host) as imap:
        imap.login(settings.imap_user, settings.imap_password)
        imap.select(settings.imap_mailbox)
        
        # Fetching ALL emails
        status, data = imap.search(None, 'ALL')
        message_ids = data[0].split() if status == 'OK' else []
        print(f'📧 Total messages in mailbox: {len(message_ids)}')
        
        total_attachments = 0
        
        # Analyzing each email
        for i, msg_id in enumerate(message_ids):
            print(f'\n--- EMAIL {i+1} (ID: {msg_id.decode()}) ---')
            
            status, msg_data = imap.fetch(msg_id, '(RFC822)')
            if status != 'OK':
                print('❌ Failed to fetch email')
                continue
                
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            
            subject = msg.get('Subject', 'No Subject')
            sender = msg.get('From', 'Unknown')
            print(f'Subject: {subject[:60]}')
            print(f'From: {sender}')
            print(f'Multipart: {msg.is_multipart()}')
            
            # Detailed analysis of email structure
            if not msg.is_multipart():
                print('📄 Simple email (not multipart)')
                content_type = msg.get_content_type()
                print(f'Content-Type: {content_type}')
                continue
                
            # Analyze each part of multipart email
            attachments_count = 0
            print('📎 Analyzing email parts:')
            
            for part_num, part in enumerate(msg.walk()):
                content_type = part.get_content_type()
                content_disposition = part.get('Content-Disposition')
                filename = part.get_filename()
                
                print(f'  Part {part_num}:')
                print(f'    Content-Type: {content_type}')
                print(f'    Content-Disposition: {content_disposition}')
                print(f'    Filename: {filename}')
                
                # Is this an attachment?
                if content_disposition and ('attachment' in content_disposition.lower() or 'inline' in content_disposition.lower()):
                    attachments_count += 1
                    total_attachments += 1
                    
                    if filename:
                        file_ext = Path(filename).suffix.lower()
                        payload_size = len(part.get_payload(decode=True) or b'')
                        
                        print(f'    ⭐ ATTACHMENT #{attachments_count}:')
                        print(f'       Name: {filename}')
                        print(f'       Extension: {file_ext}')
                        print(f'       Size: {payload_size} bytes')
                        print(f'       MIME: {content_type}')
                        
                        # Special attention to PDF
                        if file_ext == '.pdf' or 'pdf' in content_type.lower():
                            print(f'       🎯 PDF FOUND!')
                        
                        # Checking allowed types
                        allowed_extensions = {'.pdf', '.xlsx', '.xls', '.docx', '.xml', '.png'}
                        if file_ext in allowed_extensions:
                            print(f'       ✅ Type allowed')
                        else:
                            print(f'       ❌ Type blocked')
                            
            print(f'📊 Attachments in email: {attachments_count}')
            
        print(f'\n📈 TOTAL ATTACHMENTS IN ALL EMAILS: {total_attachments}')

except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()