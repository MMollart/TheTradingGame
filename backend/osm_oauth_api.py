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

from database import get_db
from auth import get_current_user
from models import User
from osm_oauth import OSMOAuthClient, OSMAPIClient

router = APIRouter(prefix="/oauth/osm", tags=["OAuth - OnlineScoutManager"])


# In-memory state storage for CSRF protection
# In production, use Redis or database-backed sessions
_oauth_states = {}


@router.get("/authorize")
async def initiate_oauth(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiate OAuth2 authorization flow with OSM.
    
    Redirects user to OSM login page. After successful login and authorization,
    user will be redirected back to /oauth/osm/callback with an authorization code.
    
    **Flow:**
    1. User clicks "Connect to OnlineScoutManager"
    2. Redirect to this endpoint
    3. Redirect to OSM login page
    4. User logs in and authorizes
    5. OSM redirects to /oauth/osm/callback
    6. Exchange code for tokens
    7. Store tokens and redirect to success page
    
    **Security:**
    Uses state parameter for CSRF protection.
    """
    # Generate random state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Store state associated with user
    _oauth_states[state] = current_user.id
    
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
    This endpoint exchanges the code for access and refresh tokens, stores them,
    and redirects to a success page.
    
    **Query Parameters:**
    - code: Authorization code from OSM
    - state: CSRF protection token
    - error: Error code if authorization failed
    - error_description: Human-readable error description
    
    **Returns:**
    Redirect to success page or error page with appropriate message.
    """
    # Check for OAuth errors
    if error:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": error,
                "error_description": error_description or "OAuth authorization failed"
            }
        )
    
    # Validate required parameters
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required parameters: code and state"
        )
    
    # Verify state (CSRF protection)
    user_id = _oauth_states.get(state)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter. Possible CSRF attack."
        )
    
    # Remove used state
    del _oauth_states[state]
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Initialize OAuth client
    oauth_client = OSMOAuthClient(db)
    
    try:
        # Exchange code for tokens
        tokens = await oauth_client.exchange_code_for_token(code, user)
        
        # Return success response
        # In production, redirect to a success page in your frontend
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Successfully connected to OnlineScoutManager",
                "user_id": user.id,
                "username": user.username,
                "scopes": tokens.get("scope", ""),
                "expires_in": tokens.get("expires_in"),
            }
        )
    
    except Exception as e:
        # Log error and return user-friendly message
        print(f"OAuth callback error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to exchange authorization code: {str(e)}"
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
        print(f"Token refresh error: {str(e)}")
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
        print(f"OSM API error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch members from OSM: {str(e)}"
        )
