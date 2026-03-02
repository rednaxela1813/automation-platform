# Email Automation Platform Setup

## IMAP Configuration

1. Copy and edit the environment file:
```bash
cp .env.example .env
nano .env
```

2. Configure IMAP values:
```env
IMAP_HOST=imap.gmail.com
IMAP_USER=your-email@gmail.com
IMAP_PASSWORD=your-app-specific-password
IMAP_MAILBOX=INBOX
```

## Provider Notes

### Gmail
1. Enable 2FA for your Google account.
2. Create an App Password: https://support.google.com/accounts/answer/185833
3. Use the App Password instead of your main password.

### Custom servers
Set the host, port, and mailbox according to your provider documentation.

## Quick Connection Test
```bash
python run.py
# In another terminal:
python test_imap.py
```

## Security Recommendations
- Never commit `.env` to git.
- Use app passwords whenever possible.
- Rotate credentials regularly.
- Restrict IMAP access by IP if your provider supports it.

## Additional Settings
You can also configure API host/port, database path, storage paths, and debug mode in `.env`.
