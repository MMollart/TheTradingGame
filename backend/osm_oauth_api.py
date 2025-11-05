"""
API endpoints for OSM OAuth2 authentication.

Provides endpoints for:
- Initiating OAuth authorization flow
- Handling OAuth callback
- Token management and refresh
- Checking OAuth connection status
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import secrets
import logging

from database import get_db
from auth import get_current_user
from models import User
from osm_oauth import OSMOAuthClient, OSMAPIClient

router = APIRouter(prefix="/oauth/osm", tags=["OAuth - OnlineScoutManager"])

# Configure logging
logger = logging.getLogger(__name__)

# In-memory state storage for CSRF protection
# WARNING: This is not suitable for production use!
# In production, use Redis or database-backed sessions for:
# - Thread safety
# - Persistence across restarts
# - Multi-server deployment support
# Example production implementation:
#   from redis import Redis
#   redis_client = Redis(host='localhost', port=6379, db=0)
#   redis_client.setex(f"oauth_state:{state}", 600, user_id)
_oauth_states = {}


@router.get("/authorize")
async def initiate_oauth(
    db: Session = Depends(get_db)
):
    """
    Initiate OAuth2 authorization flow with OSM.
    
    Redirects user to OSM login page. After successful login and authorization,
    user will be redirected back to /oauth/osm/callback with an authorization code.
    
    **Flow:**
    1. User clicks "Login with Online Scout Manager"
    2. Redirect to this endpoint
    3. Redirect to OSM login page
    4. User logs in and authorizes
    5. OSM redirects to /oauth/osm/callback
    6. Exchange code for tokens
    7. Fetch user info from OSM
    8. Create or update user account
    9. Generate JWT token and redirect to dashboard
    
    **Security:**
    Uses state parameter for CSRF protection.
    No authentication required - this is the entry point for OSM login.
    """
    # Generate random state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Store state (no user ID yet, user will be created in callback)
    _oauth_states[state] = None
    
    # Initialize OAuth client
    oauth_client = OSMOAuthClient(db)
    
    # Get authorization URL
    auth_url = oauth_client.get_authorization_url(state=state)
    
    # Redirect user to OSM login page
    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


@router.get("/callback")
async def oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Handle OAuth2 callback from OSM.
    
    After user authorizes on OSM, they are redirected here with an authorization code.
    This endpoint:
    1. Exchanges the code for access tokens
    2. Fetches user info from OSM /oauth/resource endpoint
    3. Creates or updates user account with OSM data
    4. Generates JWT token
    5. Redirects to dashboard with token
    
    **Query Parameters:**
    - code: Authorization code from OSM
    - state: CSRF protection token
    - error: Error code if authorization failed
    - error_description: Human-readable error description
    
    **Returns:**
    Redirect to dashboard with JWT token
    """
    # Check for OAuth errors
    if error:
        logger.error(f"OSM OAuth error: {error} - {error_description}")
        # Redirect to login page with error message
        return RedirectResponse(
            url=f"/?error={error}&message={error_description or 'OAuth authorization failed'}",
            status_code=status.HTTP_302_FOUND
        )
    
    # Validate required parameters
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required parameters: code and state"
        )
    
    # Verify state (CSRF protection)
    if state not in _oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter. Possible CSRF attack."
        )
    
    # Remove used state
    del _oauth_states[state]
    
    # Initialize OAuth client
    oauth_client = OSMOAuthClient(db)
    
    try:
        # Exchange code for tokens (without user, since we haven't created/found them yet)
        logger.info("Exchanging authorization code for access token...")
        import httpx
        async with httpx.AsyncClient() as http_client:
            token_response = await http_client.post(
                "https://www.onlinescoutmanager.co.uk/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": oauth_client.config.CLIENT_ID,
                    "client_secret": oauth_client.config.CLIENT_SECRET,
                    "redirect_uri": oauth_client.config.REDIRECT_URI,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            token_response.raise_for_status()
            tokens = token_response.json()
            access_token = tokens["access_token"]
        
        # Fetch user info from OSM resource endpoint
        logger.info("Fetching user info from OSM /oauth/resource endpoint...")
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                "https://www.onlinescoutmanager.co.uk/oauth/resource",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            user_info = response.json()
        
        # Extract user data
        osm_data = user_info.get("data", {})
        full_name = osm_data.get("full_name", "OSM User")
        email = osm_data.get("email")
        osm_user_id = osm_data.get("user_id")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OSM account has no email address"
            )
        
        logger.info(f"OSM user info: name={full_name}, email={email}, osm_id={osm_user_id}")
        
        # Check if user already exists by email
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            logger.info(f"Existing user found: {user.username} (id={user.id})")
        else:
            # Create new user account
            logger.info(f"Creating new user account for {full_name} ({email})")
            
            # Ensure username is unique (use full_name, append number if needed)
            username = full_name
            counter = 1
            while db.query(User).filter(User.username == username).first():
                username = f"{full_name}_{counter}"
                counter += 1
            
            user = User(
                username=username,
                email=email,
                hashed_password="",  # OSM users don't need password
                is_active=True,  # Auto-approve OSM users
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Created new user: {user.username} (id={user.id})")
        
        # Store OAuth tokens for this user
        oauth_client._store_token(user, tokens)
        
        # Generate JWT token for authentication
        from auth import create_access_token
        jwt_token = create_access_token(data={"sub": user.username})
        
        # Return HTML page that stores token in localStorage and redirects to index
        logger.info(f"Redirecting user {user.username} to main page")
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login Successful</title>
        </head>
        <body>
            <h2>Login successful! Redirecting...</h2>
            <script>
                // Store authentication token and username
                localStorage.setItem('authToken', '{jwt_token}');
                localStorage.setItem('username', '{user.username}');
                
                // Redirect to main page
                window.location.href = '/';
            </script>
        </body>
        </html>
        """
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content, status_code=200)
    
    except Exception as e:
        # Log error and redirect to login with error message
        logger.error(f"OAuth callback error: {str(e)}", exc_info=True)
        return RedirectResponse(
            url=f"/?error=callback_failed&message={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.get("/status")
async def check_oauth_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if current user has connected their OSM account.
    
    Returns information about the OAuth connection status, including:
    - Whether user is connected
    - Token expiry status
    - Granted scopes
    
    **Returns:**
    ```json
    {
        "connected": true,
        "expires_at": "2025-11-05T12:34:56",
        "scopes": "section:member:read section:finance:read",
        "needs_refresh": false
    }
    ```
    """
    oauth_client = OSMOAuthClient(db)
    oauth_token = oauth_client.get_stored_token(current_user)
    
    if not oauth_token:
        return {
            "connected": False,
            "message": "No OSM account connected. Use /oauth/osm/authorize to connect."
        }
    
    # Check if token needs refresh
    from datetime import datetime, timedelta
    needs_refresh = False
    if oauth_token.expires_at:
        expires_soon = datetime.utcnow() + timedelta(minutes=5)
        needs_refresh = oauth_token.expires_at <= expires_soon
    
    return {
        "connected": True,
        "expires_at": oauth_token.expires_at.isoformat() if oauth_token.expires_at else None,
        "scopes": oauth_token.scope,
        "needs_refresh": needs_refresh,
        "updated_at": oauth_token.updated_at.isoformat()
    }


@router.post("/refresh")
async def refresh_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually refresh the OAuth access token.
    
    Normally, tokens are automatically refreshed when needed, but this endpoint
    allows manual refresh if desired.
    
    **Returns:**
    ```json
    {
        "message": "Token refreshed successfully",
        "expires_in": 3600
    }
    ```
    """
    oauth_client = OSMOAuthClient(db)
    oauth_token = oauth_client.get_stored_token(current_user)
    
    if not oauth_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No OAuth token found. Please authorize first."
        )
    
    if not oauth_token.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No refresh token available. Please re-authorize."
        )
    
    try:
        new_tokens = await oauth_client.refresh_access_token(
            oauth_token.refresh_token,
            current_user
        )
        
        return {
            "message": "Token refreshed successfully",
            "expires_in": new_tokens.get("expires_in"),
            "scopes": new_tokens.get("scope")
        }
    
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh token: {str(e)}"
        )


@router.delete("/disconnect")
async def disconnect_oauth(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect OSM account from current user.
    
    Removes stored OAuth tokens. User will need to re-authorize to use OSM features.
    
    **Returns:**
    ```json
    {
        "message": "Successfully disconnected from OnlineScoutManager"
    }
    ```
    """
    oauth_client = OSMOAuthClient(db)
    oauth_token = oauth_client.get_stored_token(current_user)
    
    if not oauth_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No OAuth connection found"
        )
    
    # Delete token from database
    db.delete(oauth_token)
    db.commit()
    
    return {
        "message": "Successfully disconnected from OnlineScoutManager"
    }


# Example OSM API endpoint (demonstrating usage)
@router.get("/test/members")
async def test_get_members(
    section_id: int,
    term_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    **Example endpoint**: Get members from OSM.
    
    Demonstrates how to use the OSMAPIClient to make authenticated requests.
    
    **Parameters:**
    - section_id: Your OSM section ID
    - term_id: Optional term ID for filtering
    
    **Returns:**
    Member data from OnlineScoutManager API
    
    **Note:** Requires user to have authorized OSM connection first.
    """
    try:
        api_client = OSMAPIClient(db, current_user)
        members = await api_client.get_members(section_id, term_id)
        return members
    
    except ValueError as e:
        # No token or token invalid
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(f"OSM API error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch members from OSM: {str(e)}"
        )
