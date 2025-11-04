# OnlineScoutManager OAuth2 Integration

This document explains how to set up and use the OAuth2 authentication framework for connecting to the OnlineScoutManager (OSM) API.

## Overview

The Trading Game now includes a complete OAuth2 integration framework that allows users to:
- Connect their OnlineScoutManager accounts
- Access OSM data (members, events, invoices, etc.) within the game
- Automatically manage OAuth tokens (refresh, expiry, etc.)

This implementation is based on the [OSM API Documentation](https://github.com/MMollart/API-Documentation) and follows OAuth2 best practices.

## Architecture

### Components

1. **OAuthToken Model** (`backend/models.py`)
   - Database model for storing OAuth tokens
   - Links tokens to user accounts
   - Tracks expiry and refresh tokens

2. **OSMOAuthClient** (`backend/osm_oauth.py`)
   - Core OAuth2 client implementation
   - Supports both authorization code flow and client credentials flow
   - Handles token refresh automatically
   - Manages token storage in database

3. **OSMAPIClient** (`backend/osm_oauth.py`)
   - High-level API client for OSM endpoints
   - Automatically handles authentication
   - Provides convenient methods for common OSM operations

4. **OAuth API Endpoints** (`backend/osm_oauth_api.py`)
   - `/oauth/osm/authorize` - Initiate OAuth flow
   - `/oauth/osm/callback` - Handle OAuth callback
   - `/oauth/osm/status` - Check connection status
   - `/oauth/osm/refresh` - Manually refresh token
   - `/oauth/osm/disconnect` - Remove OAuth connection

## Configuration

### 1. Environment Variables

Add the following to your `.env` file (see `.env.example`):

```bash
# OnlineScoutManager OAuth2 Configuration
OSM_CLIENT_ID=your-osm-client-id
OSM_CLIENT_SECRET=your-osm-client-secret
OSM_REDIRECT_URI=https://your-domain.com/oauth/osm/callback
OSM_BASE_URL=https://www.onlinescoutmanager.co.uk
OSM_AUTHORIZE_URL=https://www.onlinescoutmanager.co.uk/oauth/authorize
OSM_TOKEN_URL=https://www.onlinescoutmanager.co.uk/oauth/token
OSM_DEFAULT_SCOPES=section:member:read section:finance:read
```

### 2. Get OSM API Credentials

To get your OAuth credentials:

1. Contact OnlineScoutManager support or access their developer portal
2. Register your application
3. Obtain your `CLIENT_ID` and `CLIENT_SECRET`
4. Register your redirect URI (must use HTTPS, even for local development)

### 3. HTTPS Redirect URI Requirement

**Important**: OSM requires all redirect URIs to start with `https://`. For local development:

#### Option 1: ngrok (Recommended)

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com/download

# Start your backend server
cd backend
python main.py

# In another terminal, create HTTPS tunnel
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Update .env: OSM_REDIRECT_URI=https://abc123.ngrok.io/oauth/osm/callback
```

#### Option 2: localhost.run (Free Alternative)

```bash
# Start your backend server
cd backend
python main.py

# In another terminal
ssh -R 80:localhost:8000 localhost.run

# Use the provided HTTPS URL
```

#### Option 3: Production Deployment

For production, deploy to a server with HTTPS:
- Heroku (free tier with auto HTTPS)
- Railway.app
- Your own domain with Let's Encrypt SSL

## Usage

### For End Users (Web Interface)

1. **Connect OSM Account**
   - Navigate to user settings/profile
   - Click "Connect to OnlineScoutManager"
   - Log in with OSM credentials
   - Grant permissions
   - Redirected back to the app

2. **Use OSM Features**
   - Once connected, access OSM data within the game
   - Token refresh happens automatically
   - No need to re-authenticate unless disconnected

3. **Disconnect OSM Account**
   - Go to settings
   - Click "Disconnect OnlineScoutManager"
   - Tokens are removed from database

### For Developers (API Usage)

#### 1. Initiate OAuth Flow

```python
from osm_oauth import OSMOAuthClient
from database import get_db

db = next(get_db())
oauth_client = OSMOAuthClient(db)

# Generate authorization URL
auth_url = oauth_client.get_authorization_url(state="random_csrf_token")

# Redirect user to auth_url
# User logs in, authorizes, and is redirected to callback
```

#### 2. Handle OAuth Callback

```python
# In your callback endpoint
code = request.query_params.get("code")
state = request.query_params.get("state")

# Verify state for CSRF protection
# Exchange code for tokens
tokens = await oauth_client.exchange_code_for_token(code, current_user)

# Tokens are automatically stored in database
```

#### 3. Make API Requests

```python
from osm_oauth import OSMAPIClient

# Create API client (automatically handles authentication)
api = OSMAPIClient(db, current_user)

# Get members
members = await api.get_members(section_id=12345, term_id=67890)

# Get invoices
invoices = await api.get_invoices(section_id=12345)

# Get events
events = await api.get_events(section_id=12345)

# Token refresh happens automatically if needed
```

#### 4. Manual Token Operations

```python
# Check if user has connected OSM
oauth_token = oauth_client.get_stored_token(current_user)
if not oauth_token:
    # Redirect to authorization flow
    pass

# Ensure token is valid (auto-refresh if expired)
access_token = await oauth_client.ensure_valid_token(current_user)

# Manual refresh
new_tokens = await oauth_client.refresh_access_token(
    oauth_token.refresh_token,
    current_user
)
```

## Available OAuth Scopes

Configure which permissions your app needs:

| Scope | Description |
|-------|-------------|
| `section:member:read` | Read member information |
| `section:member:write` | Update member data |
| `section:finance:read` | View financial data (invoices, payments) |
| `section:finance:write` | Manage invoices and payments |
| `section:event:read` | Access event information |
| `section:event:write` | Create and manage events |
| `section:badge:read` | View badge records |
| `section:programme:read` | View programme activities |
| `section:programme:write` | Manage programme |
| `section:admin:write` | Administrative operations |
| `section:attendance:write` | Manage attendance |

Set scopes in `.env`:
```bash
OSM_DEFAULT_SCOPES=section:member:read section:finance:read section:event:read
```

## API Endpoints

### GET /oauth/osm/authorize
Initiate OAuth2 authorization flow. Redirects user to OSM login page.

**Authentication**: Required (JWT token)

**Response**: Redirect to OSM authorization page

---

### GET /oauth/osm/callback
Handle OAuth2 callback from OSM. Exchanges authorization code for tokens.

**Query Parameters**:
- `code`: Authorization code from OSM
- `state`: CSRF protection token
- `error`: Error code (if authorization failed)
- `error_description`: Human-readable error

**Response**:
```json
{
  "message": "Successfully connected to OnlineScoutManager",
  "user_id": 123,
  "username": "john_doe",
  "scopes": "section:member:read section:finance:read",
  "expires_in": 3600
}
```

---

### GET /oauth/osm/status
Check OAuth connection status for current user.

**Authentication**: Required (JWT token)

**Response**:
```json
{
  "connected": true,
  "expires_at": "2025-11-05T12:34:56",
  "scopes": "section:member:read section:finance:read",
  "needs_refresh": false,
  "updated_at": "2025-11-04T10:30:00"
}
```

---

### POST /oauth/osm/refresh
Manually refresh access token.

**Authentication**: Required (JWT token)

**Response**:
```json
{
  "message": "Token refreshed successfully",
  "expires_in": 3600,
  "scopes": "section:member:read section:finance:read"
}
```

---

### DELETE /oauth/osm/disconnect
Disconnect OSM account from current user.

**Authentication**: Required (JWT token)

**Response**:
```json
{
  "message": "Successfully disconnected from OnlineScoutManager"
}
```

---

### GET /oauth/osm/test/members
Example endpoint demonstrating OSM API usage.

**Authentication**: Required (JWT token)

**Query Parameters**:
- `section_id`: OSM section ID (required)
- `term_id`: OSM term ID (optional)

**Response**: Members data from OSM API

## Database Schema

### oauth_tokens Table

```sql
CREATE TABLE oauth_tokens (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    provider VARCHAR(50) NOT NULL,  -- 'osm'
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_type VARCHAR(50) DEFAULT 'Bearer',
    expires_at DATETIME,
    scope VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Security Considerations

### Production Checklist

- [ ] Use HTTPS for all redirect URIs
- [ ] Store CLIENT_SECRET in environment variables (never in code)
- [ ] Implement proper CSRF protection with state parameter
- [ ] Consider encrypting tokens at rest in database
- [ ] Use secure session storage for OAuth states
- [ ] Implement rate limiting on OAuth endpoints
- [ ] Log OAuth events for audit trail
- [ ] Set appropriate token expiry times
- [ ] Validate redirect_uri matches registered URI
- [ ] Handle token expiry gracefully in UI

### Token Storage

Currently, tokens are stored in plain text in the database. For production:

1. **Encrypt tokens at rest**:
   ```python
   from cryptography.fernet import Fernet
   
   # Generate encryption key (store securely)
   key = Fernet.generate_key()
   cipher = Fernet(key)
   
   # Encrypt before storing
   encrypted_token = cipher.encrypt(access_token.encode())
   
   # Decrypt when retrieving
   decrypted_token = cipher.decrypt(encrypted_token).decode()
   ```

2. **Use environment-specific encryption keys**
3. **Rotate encryption keys periodically**
4. **Consider using a secrets manager (AWS Secrets Manager, HashiCorp Vault)**

## Testing

### Manual Testing

1. Start the backend server:
   ```bash
   cd backend
   python main.py
   ```

2. Get a JWT token:
   ```bash
   curl -X POST http://localhost:8000/auth/register \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser", "email": "test@example.com", "password": "testpass"}'
   
   curl -X POST http://localhost:8000/auth/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=testuser&password=testpass"
   ```

3. Initiate OAuth flow:
   ```bash
   # In browser, navigate to:
   http://localhost:8000/oauth/osm/authorize
   # (with Authorization: Bearer <token> header or authenticated session)
   ```

4. Check status:
   ```bash
   curl -X GET http://localhost:8000/oauth/osm/status \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
   ```

### Unit Tests

Create tests for OAuth functionality:

```python
import pytest
from osm_oauth import OSMOAuthClient, OSMAPIClient
from models import User, OAuthToken

def test_generate_authorization_url():
    client = OSMOAuthClient()
    url = client.get_authorization_url(state="test123")
    assert "response_type=code" in url
    assert "state=test123" in url

@pytest.mark.asyncio
async def test_token_storage(db_session):
    user = User(username="test", email="test@test.com")
    client = OSMOAuthClient(db_session)
    
    tokens = {
        "access_token": "test_token",
        "refresh_token": "refresh_token",
        "expires_in": 3600
    }
    
    oauth_token = client._store_token(user, tokens)
    assert oauth_token.access_token == "test_token"
```

## Troubleshooting

### Common Issues

**1. "Invalid redirect_uri"**
- Ensure redirect URI in `.env` exactly matches registered URI in OSM
- Check for trailing slashes
- Verify HTTPS is used

**2. "No OAuth token found"**
- User hasn't completed authorization flow
- Token was disconnected
- Database migration didn't run

**3. "Token expired and no refresh token available"**
- User needs to re-authorize
- Refresh token might have expired (typically 30-90 days)

**4. ngrok URL changes on restart**
- Free ngrok tier generates new URLs
- Update `.env` and re-register with OSM
- Consider paid ngrok plan for persistent URLs

**5. CORS errors**
- Check CORS configuration in main.py
- Ensure allowed origins include your frontend URL

## Future Enhancements

- [ ] Token encryption at rest
- [ ] Multiple OAuth provider support (Google, Microsoft, etc.)
- [ ] OAuth token rotation
- [ ] Webhook support for OSM events
- [ ] Caching layer for OSM API responses
- [ ] Rate limiting per OSM account
- [ ] OAuth scope management UI
- [ ] Bulk operations with OSM API
- [ ] OSM data synchronization
- [ ] Real-time OSM event notifications

## References

- [OSM API Documentation](https://github.com/MMollart/API-Documentation)
- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [Authlib Documentation](https://docs.authlib.org/)
- [FastAPI OAuth2 Guide](https://fastapi.tiangolo.com/advanced/security/oauth2/)

## Support

For issues or questions:
- GitHub Issues: [TheTradingGame/issues](https://github.com/MMollart/TheTradingGame/issues)
- OSM API Documentation: [API-Documentation](https://github.com/MMollart/API-Documentation)

---

**Last Updated**: November 4, 2025
