"""
OAuth2 client for OnlineScoutManager (OSM) API integration

Based on the OSM API documentation from MMollart/API-Documentation repository.
Supports both client credentials flow and authorization code flow.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import os

from authlib.integrations.httpx_client import OAuth2Client
from authlib.oauth2.rfc6749 import OAuth2Token
import httpx
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from models import OAuthToken, OAuthProvider, User

load_dotenv()


class OSMOAuthConfig:
    """Configuration for OSM OAuth2"""
    
    CLIENT_ID = os.getenv("OSM_CLIENT_ID", "")
    CLIENT_SECRET = os.getenv("OSM_CLIENT_SECRET", "")
    REDIRECT_URI = os.getenv("OSM_REDIRECT_URI", "http://localhost:8000/oauth/osm/callback")
    
    BASE_URL = os.getenv("OSM_BASE_URL", "https://www.onlinescoutmanager.co.uk")
    AUTHORIZE_URL = os.getenv("OSM_AUTHORIZE_URL", f"{BASE_URL}/oauth/authorize")
    TOKEN_URL = os.getenv("OSM_TOKEN_URL", f"{BASE_URL}/oauth/token")
    
    DEFAULT_SCOPES = os.getenv(
        "OSM_DEFAULT_SCOPES",
        "section:member:read section:finance:read section:event:read"
    )


class OSMOAuthClient:
    """
    OAuth2 client for OnlineScoutManager API.
    
    Supports two OAuth2 flows:
    1. Client Credentials Flow - For machine-to-machine, automated scripts
    2. Authorization Code Flow - For user-facing applications with login
    
    Based on OSM API documentation:
    https://github.com/MMollart/API-Documentation
    """
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize OSM OAuth client.
        
        Args:
            db: Optional database session for storing tokens
        """
        self.config = OSMOAuthConfig()
        self.db = db
        
        # Initialize OAuth2 client
        self.client = OAuth2Client(
            client_id=self.config.CLIENT_ID,
            client_secret=self.config.CLIENT_SECRET,
            token_endpoint=self.config.TOKEN_URL,
        )
    
    def get_authorization_url(
        self,
        state: Optional[str] = None,
        scope: Optional[str] = None
    ) -> str:
        """
        Generate authorization URL for authorization code flow.
        
        User should be redirected to this URL to log in and authorize.
        
        Args:
            state: Random string for CSRF protection (recommended)
            scope: Space-separated OAuth scopes. Defaults to DEFAULT_SCOPES
            
        Returns:
            Authorization URL string
            
        Example:
            >>> client = OSMOAuthClient()
            >>> url = client.get_authorization_url(state="random_state_123")
            >>> # Redirect user to `url`
        """
        scope = scope or self.config.DEFAULT_SCOPES
        
        params = {
            "response_type": "code",
            "client_id": self.config.CLIENT_ID,
            "redirect_uri": self.config.REDIRECT_URI,
            "scope": scope,
        }
        
        if state:
            params["state"] = state
        
        return f"{self.config.AUTHORIZE_URL}?{urlencode(params)}"
    
    async def exchange_code_for_token(
        self,
        code: str,
        user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token (authorization code flow).
        
        After user authorizes, OSM redirects to redirect_uri with a code.
        Call this method to exchange the code for tokens.
        
        Args:
            code: Authorization code from OSM callback
            user: Optional user to associate token with
            
        Returns:
            Token dictionary with access_token, refresh_token, expires_in, etc.
            
        Raises:
            httpx.HTTPError: If token exchange fails
            
        Example:
            >>> client = OSMOAuthClient(db)
            >>> tokens = await client.exchange_code_for_token(
            ...     code="AUTH_CODE_FROM_CALLBACK",
            ...     user=current_user
            ... )
            >>> access_token = tokens["access_token"]
        """
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                self.config.TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self.config.CLIENT_ID,
                    "client_secret": self.config.CLIENT_SECRET,
                    "redirect_uri": self.config.REDIRECT_URI,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            tokens = response.json()
        
        # Store token in database if user provided
        if user and self.db:
            self._store_token(user, tokens)
        
        return tokens
    
    async def get_client_credentials_token(
        self,
        scope: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get access token using client credentials flow.
        
        This flow is for machine-to-machine authentication without user interaction.
        
        Args:
            scope: Space-separated OAuth scopes. Defaults to DEFAULT_SCOPES
            
        Returns:
            Token dictionary with access_token, expires_in, etc.
            
        Raises:
            httpx.HTTPError: If token request fails
            
        Example:
            >>> client = OSMOAuthClient()
            >>> tokens = await client.get_client_credentials_token()
            >>> access_token = tokens["access_token"]
        """
        scope = scope or self.config.DEFAULT_SCOPES
        
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                self.config.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.config.CLIENT_ID,
                    "client_secret": self.config.CLIENT_SECRET,
                    "scope": scope,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return response.json()
    
    async def refresh_access_token(
        self,
        refresh_token: str,
        user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Refresh an expired access token using a refresh token.
        
        Args:
            refresh_token: The refresh token from previous authentication
            user: Optional user to update stored token
            
        Returns:
            New token dictionary with access_token, refresh_token, etc.
            
        Raises:
            httpx.HTTPError: If refresh fails
            
        Example:
            >>> client = OSMOAuthClient(db)
            >>> new_tokens = await client.refresh_access_token(
            ...     refresh_token="def502004a3c8b...",
            ...     user=current_user
            ... )
        """
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                self.config.TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.config.CLIENT_ID,
                    "client_secret": self.config.CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            tokens = response.json()
        
        # Update stored token if user provided
        if user and self.db:
            self._store_token(user, tokens)
        
        return tokens
    
    def _store_token(self, user: User, tokens: Dict[str, Any]) -> OAuthToken:
        """
        Store OAuth token in database.
        
        Args:
            user: User to associate token with
            tokens: Token dictionary from OAuth response
            
        Returns:
            Created or updated OAuthToken object
        """
        if not self.db:
            raise ValueError("Database session required to store token")
        
        # Calculate expiry time
        expires_at = None
        if "expires_in" in tokens:
            expires_at = datetime.utcnow() + timedelta(seconds=tokens["expires_in"])
        
        # Check if token exists for this user and provider
        oauth_token = self.db.query(OAuthToken).filter(
            OAuthToken.user_id == user.id,
            OAuthToken.provider == OAuthProvider.OSM
        ).first()
        
        if oauth_token:
            # Update existing token
            oauth_token.access_token = tokens["access_token"]
            oauth_token.refresh_token = tokens.get("refresh_token")
            oauth_token.token_type = tokens.get("token_type", "Bearer")
            oauth_token.expires_at = expires_at
            oauth_token.scope = tokens.get("scope")
            oauth_token.updated_at = datetime.utcnow()
        else:
            # Create new token
            oauth_token = OAuthToken(
                user_id=user.id,
                provider=OAuthProvider.OSM,
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token"),
                token_type=tokens.get("token_type", "Bearer"),
                expires_at=expires_at,
                scope=tokens.get("scope"),
            )
            self.db.add(oauth_token)
        
        self.db.commit()
        self.db.refresh(oauth_token)
        return oauth_token
    
    def get_stored_token(self, user: User) -> Optional[OAuthToken]:
        """
        Retrieve stored OAuth token for a user.
        
        Args:
            user: User to get token for
            
        Returns:
            OAuthToken if exists, None otherwise
        """
        if not self.db:
            raise ValueError("Database session required to retrieve token")
        
        return self.db.query(OAuthToken).filter(
            OAuthToken.user_id == user.id,
            OAuthToken.provider == OAuthProvider.OSM
        ).first()
    
    async def ensure_valid_token(self, user: User) -> str:
        """
        Ensure user has a valid access token, refreshing if necessary.
        
        Args:
            user: User to check token for
            
        Returns:
            Valid access token string
            
        Raises:
            ValueError: If no token found or refresh fails
            
        Example:
            >>> client = OSMOAuthClient(db)
            >>> token = await client.ensure_valid_token(current_user)
            >>> # Use token in API requests
        """
        oauth_token = self.get_stored_token(user)
        
        if not oauth_token:
            raise ValueError("No OAuth token found for user. Please authorize first.")
        
        # Check if token is expired or about to expire (within 5 minutes)
        if oauth_token.expires_at:
            expires_soon = datetime.utcnow() + timedelta(minutes=5)
            if oauth_token.expires_at <= expires_soon:
                # Token expired or expiring soon, refresh it
                if not oauth_token.refresh_token:
                    raise ValueError("Token expired and no refresh token available")
                
                new_tokens = await self.refresh_access_token(
                    oauth_token.refresh_token,
                    user
                )
                return new_tokens["access_token"]
        
        return oauth_token.access_token


class OSMAPIClient:
    """
    High-level client for making authenticated requests to OSM API.
    
    Automatically handles token management and authentication.
    
    Example:
        >>> from database import get_db
        >>> db = next(get_db())
        >>> api = OSMAPIClient(db, current_user)
        >>> 
        >>> # Get members list
        >>> members = await api.get_members(section_id=12345, term_id=67890)
        >>> 
        >>> # Get invoices
        >>> invoices = await api.get_invoices(section_id=12345)
    """
    
    def __init__(self, db: Session, user: User):
        """
        Initialize OSM API client.
        
        Args:
            db: Database session
            user: User with OAuth token
        """
        self.db = db
        self.user = user
        self.oauth_client = OSMOAuthClient(db)
        self.base_url = OSMOAuthConfig.BASE_URL
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get headers with valid access token."""
        token = await self.oauth_client.ensure_valid_token(self.user)
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    
    async def request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make authenticated request to OSM API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/ext/members/contact/")
            **kwargs: Additional arguments for httpx request
            
        Returns:
            JSON response as dictionary
            
        Raises:
            httpx.HTTPError: If request fails
        """
        headers = await self._get_headers()
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
    
    async def get_members(
        self,
        section_id: int,
        term_id: Optional[int] = None,
        member_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get members list or specific member details.
        
        Args:
            section_id: OSM section ID
            term_id: Optional term ID for filtering
            member_id: Optional member ID to get specific member
            
        Returns:
            Members data from OSM API
        """
        params = {"sectionid": section_id}
        
        if member_id:
            params["action"] = "getIndividualMember"
            params["scoutid"] = member_id
        else:
            params["action"] = "getListOfMembers"
            if term_id:
                params["termid"] = term_id
        
        return await self.request("GET", "/ext/members/contact/", params=params)
    
    async def get_invoices(
        self,
        section_id: int,
        invoice_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get invoices summary or specific invoice details.
        
        Args:
            section_id: OSM section ID
            invoice_id: Optional invoice ID for specific invoice
            
        Returns:
            Invoice data from OSM API
        """
        params = {"sectionid": section_id}
        
        if invoice_id:
            params["action"] = "getInvoice"
            params["invoiceid"] = invoice_id
            endpoint = "/ext/finances/invoices/"
        else:
            params["action"] = "getSummary"
            endpoint = "/ext/finances/invoices/summary/"
        
        return await self.request("GET", endpoint, params=params)
    
    async def get_events(self, section_id: int) -> Dict[str, Any]:
        """
        Get events list for a section.
        
        Args:
            section_id: OSM section ID
            
        Returns:
            Events data from OSM API
        """
        return await self.request(
            "GET",
            "/ext/events/summary/",
            params={"sectionid": section_id}
        )
