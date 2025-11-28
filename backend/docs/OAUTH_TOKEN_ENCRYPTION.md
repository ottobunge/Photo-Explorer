# OAuth Token Encryption Implementation

## Overview

This document describes the OAuth token encryption implementation for the Photo Explorer application, addressing **CRIT-1** from the code review action plan.

## Security Issue

Previously, OAuth tokens could potentially be stored in plain text, creating a security vulnerability where tokens could be compromised if the database or storage was accessed by unauthorized parties.

## Solution

OAuth tokens are now encrypted at rest using the **Fernet** symmetric encryption scheme from the `cryptography` library. This provides strong encryption with the following characteristics:

- AES-128 encryption in CBC mode
- HMAC for authentication
- Timestamp for token expiration
- URL-safe base64 encoding

## Implementation Details

### 1. Token Storage Implementations

Two token storage implementations are provided:

#### File-Based Storage (`SecureTokenStorage`)
- Stores encrypted tokens in JSON files
- Useful for single-server deployments
- Files are created with secure permissions (0600)
- Directory is created with secure permissions (0700)

#### Database Storage (`DatabaseTokenStorage`)
- Stores encrypted tokens in PostgreSQL database
- Uses the `oauth_tokens` table
- Recommended for distributed deployments
- Requires migration 0002 to be applied

### 2. Encryption Key Management

The encryption key is managed through the `TOKEN_ENCRYPTION_KEY` environment variable:

```bash
# Generate a new key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add to .env file
TOKEN_ENCRYPTION_KEY=your_generated_key_here
```

**Important Security Notes:**
- The encryption key is required and must be set in production
- Never commit the encryption key to version control
- Use a secure key management service in production (e.g., AWS Secrets Manager, HashiCorp Vault)
- If the key is lost, all encrypted tokens will be unrecoverable
- Rotate keys periodically following security best practices

### 3. Configuration

The encryption key is configured in the application settings:

```python
# backend/app/config.py
class Settings(BaseSettings):
    # Security
    token_encryption_key: str  # Required, loaded from TOKEN_ENCRYPTION_KEY env var
```

### 4. Database Schema

The `oauth_tokens` table stores encrypted token data:

```sql
CREATE TABLE oauth_tokens (
    connector_type VARCHAR(50) PRIMARY KEY,
    encrypted_data VARCHAR(4096) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### 5. Token Data Structure

Tokens are stored as encrypted JSON containing:

```json
{
    "access_token": "string",
    "refresh_token": "string",
    "token_type": "Bearer",
    "expires_at": "ISO-8601 datetime",
    "scopes": ["array", "of", "scopes"]
}
```

## Usage Examples

### Using SecureTokenStorage (File-based)

```python
from app.adapters.outbound.storage import SecureTokenStorage
from app.application.ports.outbound.token_storage import OAuthTokens
from datetime import datetime, timezone, timedelta

# Initialize storage
storage = SecureTokenStorage(
    storage_dir="./data/tokens",
    encryption_key=os.environ.get("TOKEN_ENCRYPTION_KEY")
)

# Save tokens
tokens = OAuthTokens(
    access_token="ya29.a0...",
    refresh_token="1//0g...",
    token_type="Bearer",
    expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    scopes=["https://www.googleapis.com/auth/photoslibrary.readonly"]
)
await storage.save_tokens("google_photos", tokens)

# Load tokens
loaded_tokens = await storage.load_tokens("google_photos")
if loaded_tokens and not loaded_tokens.is_expired:
    # Use the access token
    pass

# Delete tokens
await storage.delete_tokens("google_photos")
```

### Using DatabaseTokenStorage

```python
from app.adapters.outbound.storage import DatabaseTokenStorage
from app.adapters.outbound.persistence.postgres.database import get_session

# Initialize storage with session factory
storage = DatabaseTokenStorage(
    session_factory=get_session,
    encryption_key=os.environ.get("TOKEN_ENCRYPTION_KEY")
)

# Same API as SecureTokenStorage
await storage.save_tokens("google_photos", tokens)
loaded_tokens = await storage.load_tokens("google_photos")
```

## Migration Guide

### For Existing Deployments

If you have existing deployments with unencrypted tokens:

1. **Apply the migration:**
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **Generate an encryption key:**
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

3. **Update your .env file:**
   ```bash
   TOKEN_ENCRYPTION_KEY=your_generated_key_here
   ```

4. **Re-authenticate connectors:**
   - Existing tokens in the old format will need to be replaced
   - Users should disconnect and reconnect their Google Photos accounts
   - This ensures all tokens are properly encrypted

### For New Deployments

1. Set `TOKEN_ENCRYPTION_KEY` in your environment before starting the application
2. All tokens will be encrypted from the start

## Testing

Comprehensive unit tests are provided in:
```
backend/tests/unit/adapters/outbound/storage/test_secure_token_storage.py
```

Run tests with:
```bash
cd backend
poetry run pytest tests/unit/adapters/outbound/storage/test_secure_token_storage.py -v
```

### Test Coverage

The test suite covers:
- ✅ Encryption and decryption of tokens
- ✅ Verification that tokens are encrypted at rest (not plain text)
- ✅ Loading non-existent tokens returns None
- ✅ Deleting tokens
- ✅ Updating existing tokens
- ✅ Secure file permissions (0600 for files, 0700 for directories)
- ✅ Auto-generation of encryption key if not provided
- ✅ Connector type sanitization for safe filenames
- ✅ Database storage implementation
- ✅ Token expiration checking

## Security Considerations

### Encryption at Rest
- ✅ Tokens are encrypted using Fernet (AES-128-CBC + HMAC)
- ✅ Encryption key is required and must be provided
- ✅ Files are created with restrictive permissions

### Key Management
- ⚠️ Key must be stored securely (use secrets management in production)
- ⚠️ Key rotation requires re-encryption of all tokens
- ⚠️ Backup keys securely - lost keys mean lost access to tokens

### Additional Recommendations
1. Use environment-specific keys (different for dev/staging/prod)
2. Implement key rotation policy (e.g., annually)
3. Monitor access to encrypted token storage
4. Use database storage for distributed deployments
5. Consider using a dedicated secrets management service

## Architecture Integration

### Port-Adapter Pattern

The implementation follows the hexagonal architecture:

```
Domain/Application Layer:
└── app/application/ports/outbound/token_storage.py
    └── TokenStorage (interface)
    └── OAuthTokens (data class)

Adapter Layer:
└── app/adapters/outbound/storage/secure_token_storage.py
    ├── SecureTokenStorage (file-based implementation)
    └── DatabaseTokenStorage (database implementation)
```

### Dependency Injection

Token storage should be injected into use cases and services:

```python
class GooglePhotosConnector:
    def __init__(self, token_storage: TokenStorage):
        self._token_storage = token_storage
```

## Related Files

- Configuration: `backend/app/config.py`
- Models: `backend/app/adapters/outbound/persistence/postgres/models.py`
- Migration: `backend/alembic/versions/20250101_000001_0002_add_oauth_tokens.py`
- Tests: `backend/tests/unit/adapters/outbound/storage/test_secure_token_storage.py`
- Example env: `.env.example`

## Status

✅ **Completed** - OAuth token encryption is fully implemented and tested.

**Implementation Date:** 2025-11-24
**Issue:** CRIT-1 from Code Review Action Plan
**Security Level:** High - Protects sensitive OAuth credentials
