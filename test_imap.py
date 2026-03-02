#!/usr/bin/env python3
"""
Simple IMAP connection diagnostics
"""
import sys
import os
sys.path.insert(0, 'src')

from automation.config.settings import settings
import imaplib

def test_imap_connection():
    print('🔧 Checking IMAP settings:')
    print(f'IMAP Host: {settings.imap_host}')
    print(f'IMAP User: {settings.imap_user}')
    print(f'IMAP Password: {"*" * len(settings.imap_password)}')
    print(f'IMAP Mailbox: {settings.imap_mailbox}')
    
    try:
        print(f'\n🔌 Trying to connect to {settings.imap_host}...')
        
        with imaplib.IMAP4_SSL(settings.imap_host) as imap:
            print('✅ SSL connection established')
            
            result = imap.login(settings.imap_user, settings.imap_password)
            print(f'✅ Authentication successful: {result}')
            
            # Selecting mailbox
            status, count = imap.select(settings.imap_mailbox)
            print(f'📬 Mailbox "{settings.imap_mailbox}": {status}, messages: {count[0].decode()}')
            
            # Checking latest messages
            status, messages = imap.search(None, 'ALL')
            message_ids = messages[0].split()
            print(f'📧 Total messages in mailbox: {len(message_ids)}')
            
            if message_ids:
                print(f'🔢 IDs of latest messages: {message_ids[-5:]}')
            
            imap.logout()
            return True
            
    except Exception as e:
        print(f'❌ IMAP connection error: {str(e)}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_imap_connection()