# Photo Explorer - Connectors Specification

## Overview

Connectors allow Photo Explorer to index photos from various sources without necessarily downloading and storing the original files. The system supports both:

1. **Remote Connectors**: Index from cloud services (Google Photos, etc.)
2. **Local Connectors**: Index from local filesystem directories

## Design Principles

### Index, Don't Import

For remote sources like Google Photos:
- We **index** photos: extract metadata and generate embeddings
- We **don't store** original files (saving TB of storage)
- We **fetch on-demand** when users want to view a photo
- We **cache** thumbnails temporarily for UI performance

### Reference-Based Storage

Instead of storing photos, we store references:
```python
class PhotoReference:
    connector_type: str       # "google_photos", "local", etc.
    external_id: str          # ID in the source system
    source_path: str          # Original path/URL
    cached_thumbnail: str     # Local cached thumbnail (optional)
    last_synced: datetime
```

## Configuration Storage

All settings are stored in `~/.config/photo-explorer/`:

```
~/.config/photo-explorer/
├── config.yaml              # Main configuration
├── connectors/
│   ├── google-photos.yaml   # Google Photos connector config
│   └── local-folders.yaml   # Local folder configs
├── tokens/
│   └── google-photos.json   # OAuth tokens (encrypted)
└── cache/
    └── thumbnails/          # Cached thumbnails
```

### config.yaml

```yaml
storage:
  data_dir: ~/.local/share/photo-explorer
  cache_dir: ~/.cache/photo-explorer
  thumbnail_cache_hours: 24

indexing:
  batch_size: 100
  parallel_workers: 4

connectors:
  enabled:
    - google-photos
    - local-folders
```

---

## Google Photos Connector

### Authentication Flow

1. User clicks "Connect Google Photos" in Settings
2. Frontend opens OAuth consent screen
3. User grants `photoslibrary.readonly` scope
4. Backend receives authorization code
5. Backend exchanges for access + refresh tokens
6. Tokens stored encrypted in `~/.config/photo-explorer/tokens/`

### OAuth 2.0 Configuration

```yaml
# connectors/google-photos.yaml
google_photos:
  client_id: ${GOOGLE_CLIENT_ID}       # From env or config
  client_secret: ${GOOGLE_CLIENT_SECRET}
  scopes:
    - https://www.googleapis.com/auth/photoslibrary.readonly
  redirect_uri: http://localhost:8000/api/v1/connectors/google-photos/callback

sync:
  enabled: true
  interval_hours: 6
  albums:
    - all                              # or specific album IDs
  date_range:
    from: null                         # null = no limit
    to: null
```

### Indexing Process

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Google Photos Indexing Flow                       │
└─────────────────────────────────────────────────────────────────────┘

1. List Photos from Google Photos API
   └── GET /v1/mediaItems (paginated, max 100 per page)

2. For each media item:
   ├── Check if already indexed (by external_id)
   ├── If new or updated:
   │   ├── Extract metadata (camera, date, dimensions)
   │   ├── Fetch image bytes (temporary, for embedding)
   │   ├── Generate CLIP embedding
   │   ├── Detect faces, generate face embeddings
   │   ├── Run vision model for description
   │   ├── Store in database with connector reference
   │   └── Discard image bytes (not stored)
   └── Update sync timestamp

3. Handle deletions:
   └── Mark photos as "source_deleted" if no longer in Google Photos
```

### On-Demand Image Loading

When a user requests to view a photo:

```python
async def get_photo_url(photo_id: UUID) -> str:
    """Get a fresh URL for viewing a photo."""
    photo = await photo_repo.find_by_id(photo_id)

    if photo.connector_type == "google_photos":
        # Get fresh baseUrl from Google Photos API
        # (baseUrls expire after 60 minutes)
        access_token = await token_manager.get_valid_token("google_photos")
        media_item = await google_photos_api.get_media_item(
            photo.external_id,
            access_token
        )
        # Return URL with size parameters
        return f"{media_item.baseUrl}=w2048-h2048"

    elif photo.connector_type == "local":
        # Return local file path or serve directly
        return f"/api/v1/photos/{photo_id}/file"
```

### Photo Picker API Integration

The Google Photos Picker API allows users to selectively import specific photos from their Google Photos library through an interactive UI.

#### Picker Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Google Photos Picker Flow                         │
└─────────────────────────────────────────────────────────────────────┘

1. User clicks "Import Photos" on connector detail page
   └── Frontend: POST /api/v1/connectors/{id}/picker/session

2. Backend creates picker session with Google
   ├── Calls Google Picker API: POST /v1/sessions
   ├── Configures session: { pickingConfig: { maxItemCount: "1000" } }
   └── Returns: { sessionId, pickerUri, expireTime, pollInterval }

3. Frontend opens picker in popup window
   └── Opens pickerUri in centered popup (900x700px)

4. User interacts with Google Photos picker
   ├── Browses their Google Photos library
   ├── Selects photos/videos to import
   └── Clicks "ADD" button in picker

5. Frontend polls backend for session status (every 2 seconds)
   └── GET /api/v1/connectors/{id}/picker/session/{sessionId}

6. Backend polls Google Picker API for status
   ├── GET /v1/sessions/{sessionId}
   └── Returns: { mediaItemsSet: true/false, expireTime }

7. When mediaItemsSet becomes true:
   ├── Frontend: POST /api/v1/connectors/{id}/picker/session/{sessionId}/import
   ├── Backend fetches selected media items from Google
   ├── Creates Celery task to process photos
   └── Photos are indexed asynchronously

8. Session cleanup:
   ├── Sessions expire after ~60 minutes (set by Google)
   ├── Frontend detects expiration via expireTime field
   └── Shows appropriate message if session expires
```

#### Implementation Details

**Session Configuration:**
- Only `pickingConfig.maxItemCount` can be configured
- Default limit is 2000 items, we set 1000 for reasonable batch sizes
- No other configuration options exist (like file type filtering)

**State Management:**
- Backend maintains session state via Google's Picker API
- Frontend trusts backend state, not browser window state
- Polling is backend-driven (Google provides `pollInterval`)
- Session expiration handled via `expireTime` from Google API

**Why This Approach Works:**
- ✅ **Reliable**: Uses official Google Picker API session state
- ✅ **No false positives**: Doesn't check unreliable `window.closed` property
- ✅ **Handles expiration**: Google provides expiration timestamp
- ✅ **Scalable**: Backend handles session lifecycle
- ✅ **User-friendly**: Clear feedback at each stage

**Common Issues Avoided:**
- ❌ Don't check `pickerWindow.closed` - unreliable during loading
- ❌ Don't poll immediately - wait 3 seconds for window to load
- ❌ Don't use invalid config fields (`allowedMediaTypes`, `selectionMode` don't exist)
- ❌ Don't ignore session expiration - always check `expireTime`

### API Limitations

| Limit | Value |
|-------|-------|
| Max items per page | 100 |
| Picker session max items | 2000 (configurable, we use 1000) |
| Picker session duration | ~60 minutes (set by Google) |
| baseUrl validity | 60 minutes |
| Daily quota | 10,000 requests |
| Rate limit | ~50 requests/second |

### Handling Token Refresh

```python
class TokenManager:
    async def get_valid_token(self, connector: str) -> str:
        token_data = await self.load_token(connector)

        if token_data.is_expired:
            new_tokens = await self.refresh_token(
                connector,
                token_data.refresh_token
            )
            await self.save_token(connector, new_tokens)
            return new_tokens.access_token

        return token_data.access_token
```

---

## Local Folders Connector

### Configuration

```yaml
# connectors/local-folders.yaml
folders:
  - path: /home/user/Pictures
    name: My Pictures
    recursive: true
    watch: true              # Watch for filesystem changes
    auto_album: true         # Create albums from subfolders

  - path: /mnt/photos/archive
    name: Archive
    recursive: true
    watch: false             # Manual sync only
    auto_album: false
```

### Indexing Process

For local folders, we can either:
1. **Index in place**: Don't copy files, just create references
2. **Index with thumbnails**: Generate and cache thumbnails locally

```
Local Folder Indexing Flow
─────────────────────────

1. Scan directory (recursive if enabled)
   └── Find all image files (jpg, png, heic, etc.)

2. For each file:
   ├── Check if already indexed (by path + mtime)
   ├── If new or modified:
   │   ├── Extract EXIF metadata
   │   ├── Generate CLIP embedding (read from disk)
   │   ├── Detect faces
   │   ├── Generate thumbnail (cache locally)
   │   ├── Store reference in database
   │   └── source_path = absolute file path

3. Handle deletions:
   └── Mark as "source_deleted" if file no longer exists

4. Optional: Set up filesystem watcher
   └── Trigger incremental sync on changes
```

### Serving Local Files

```python
async def serve_local_photo(photo: Photo) -> FileResponse:
    """Serve a local photo file."""
    if photo.connector_type != "local":
        raise ValueError("Not a local photo")

    file_path = Path(photo.source_path)
    if not file_path.exists():
        raise FileNotFoundError("Source file no longer exists")

    return FileResponse(file_path, media_type=photo.mime_type)
```

---

## Settings API

### Endpoints

```http
# Connector Management
GET    /api/v1/settings/connectors          # List all connectors
GET    /api/v1/settings/connectors/{type}   # Get connector config
PUT    /api/v1/settings/connectors/{type}   # Update connector config
DELETE /api/v1/settings/connectors/{type}   # Remove connector

# Google Photos OAuth
GET    /api/v1/connectors/google-photos/auth-url     # Get OAuth URL
GET    /api/v1/connectors/google-photos/callback     # OAuth callback
POST   /api/v1/connectors/google-photos/disconnect   # Revoke access
GET    /api/v1/connectors/google-photos/status       # Connection status

# Local Folders
GET    /api/v1/settings/folders              # List watched folders
POST   /api/v1/settings/folders              # Add folder
DELETE /api/v1/settings/folders/{id}         # Remove folder
POST   /api/v1/settings/folders/{id}/sync    # Trigger sync

# Sync Operations
POST   /api/v1/connectors/{type}/sync        # Trigger manual sync
GET    /api/v1/connectors/{type}/sync/status # Get sync status
```

---

## Data Model Updates

### Photo Entity Extensions

```python
@dataclass
class Photo:
    # ... existing fields ...

    # Connector reference
    connector_type: str              # "local", "google_photos", etc.
    external_id: Optional[str]       # ID in source system
    source_path: Optional[str]       # Original path/URL
    source_deleted: bool = False     # Source no longer exists
    last_synced: Optional[datetime]

    # Cached resources
    cached_thumbnail_path: Optional[str]
    thumbnail_expires_at: Optional[datetime]
```

### Connector Entity

```python
@dataclass
class Connector:
    id: UUID
    type: str                        # "google_photos", "local", etc.
    name: str                        # Display name
    enabled: bool
    config: dict                     # Connector-specific config
    status: str                      # "connected", "disconnected", "error"
    last_sync: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
```

---

## Security Considerations

### Token Storage

OAuth tokens are sensitive and must be:
1. **Encrypted at rest** using system keyring or AES-256
2. **Never logged** or exposed in API responses
3. **Scoped minimally** (readonly access only)

```python
class SecureTokenStorage:
    def __init__(self, key_path: Path):
        self.key = self._load_or_create_key(key_path)

    def save_token(self, connector: str, token_data: dict):
        encrypted = self._encrypt(json.dumps(token_data))
        path = CONFIG_DIR / "tokens" / f"{connector}.enc"
        path.write_bytes(encrypted)

    def load_token(self, connector: str) -> dict:
        path = CONFIG_DIR / "tokens" / f"{connector}.enc"
        encrypted = path.read_bytes()
        return json.loads(self._decrypt(encrypted))
```

### Path Validation

For local folders, validate paths to prevent:
- Path traversal attacks
- Access to sensitive system directories
- Symlink exploits

```python
def validate_folder_path(path: str) -> Path:
    resolved = Path(path).resolve()

    # Must be absolute
    if not resolved.is_absolute():
        raise ValueError("Path must be absolute")

    # Must exist and be a directory
    if not resolved.is_dir():
        raise ValueError("Path must be an existing directory")

    # Block sensitive paths
    blocked = ["/etc", "/var", "/root", "/sys", "/proc"]
    for blocked_path in blocked:
        if str(resolved).startswith(blocked_path):
            raise ValueError(f"Access to {blocked_path} is not allowed")

    return resolved
```

---

## UI Components

### Settings View Structure

```
Settings
├── Connectors
│   ├── Google Photos
│   │   ├── Status: Connected / Not Connected
│   │   ├── Connect / Disconnect button
│   │   ├── Last sync: 2 hours ago
│   │   ├── Photos indexed: 15,432
│   │   └── Sync Now button
│   │
│   └── Other Connectors (future)
│       └── + Add Connector
│
├── Local Folders
│   ├── /home/user/Pictures (450 photos)
│   │   ├── Recursive: Yes
│   │   ├── Auto-watch: Yes
│   │   └── [Sync Now] [Remove]
│   │
│   └── + Add Folder
│
└── General Settings
    ├── Sync interval: [6 hours ▼]
    ├── Thumbnail cache: [24 hours ▼]
    └── Parallel workers: [4]
```

---

## Future Connectors

The connector architecture is extensible. Potential future connectors:

| Connector | Authentication | Storage |
|-----------|---------------|---------|
| iCloud Photos | Apple ID OAuth | Remote |
| Dropbox | OAuth 2.0 | Remote |
| Amazon Photos | OAuth 2.0 | Remote |
| OneDrive | Microsoft OAuth | Remote |
| Nextcloud | OAuth / App Password | Remote |
| NAS (SMB/NFS) | Credentials | Local mount |
| S3/MinIO | Access keys | Remote |
