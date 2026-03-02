# Critical Security Warning

Real credentials were previously detected in `.env`.

## Immediate Actions

1. Remove all real secrets from `.env`.
2. Ensure `.env` is ignored by git.
3. Use `.env.example` as the template for new setups.

## Security Recommendations
- Never commit credentials.
- Store secrets in environment variables or a secret manager.
- Rotate passwords regularly.
- Use app-specific passwords for email accounts.

This must be fixed before any deployment.
