"""
Tests for OSM OAuth2 integration.

Tests the OAuth client, API client, and token management.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from models import User, OAuthToken, OAuthProvider
from osm_oauth import OSMOAuthClient, OSMOAuthConfig, OSMAPIClient


class TestOSMOAuthConfig:
    """Test OAuth configuration."""
    
    def test_config_defaults(self):
        """Test that configuration has expected defaults."""
        config = OSMOAuthConfig()
        
        assert config.BASE_URL == "https://www.onlinescoutmanager.co.uk"
        assert "/oauth/authorize" in config.AUTHORIZE_URL
        assert "/oauth/token" in config.TOKEN_URL
        assert "section:member:read" in config.DEFAULT_SCOPES


class TestOSMOAuthClient:
    """Test OAuth client functionality."""
    
    def test_get_authorization_url(self):
        """Test generation of authorization URL."""
        client = OSMOAuthClient()
        
        # Test without state
        url = client.get_authorization_url()
        assert "response_type=code" in url
        assert "client_id=" in url
        assert "redirect_uri=" in url
        assert "scope=" in url
        
        # Test with state
        url_with_state = client.get_authorization_url(state="test_state_123")
        assert "state=test_state_123" in url_with_state
    
    def test_get_authorization_url_custom_scope(self):
        """Test authorization URL with custom scope."""
        client = OSMOAuthClient()
        custom_scope = "section:member:read section:event:write"
        
        url = client.get_authorization_url(scope=custom_scope)
        # URL encode spaces as +
        assert "section%3Amember%3Aread" in url or "section:member:read" in url
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_token_success(self, monkeypatch):
        """Test successful code exchange for tokens."""
        # Mock httpx.AsyncClient
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "section:member:read"
        }
        mock_response.raise_for_status = Mock()
        
        async def mock_post(*args, **kwargs):
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            client = OSMOAuthClient()
            tokens = await client.exchange_code_for_token("test_code")
            
            assert tokens["access_token"] == "test_access_token"
            assert tokens["refresh_token"] == "test_refresh_token"
            assert tokens["expires_in"] == 3600
    
    @pytest.mark.asyncio
    async def test_get_client_credentials_token(self, monkeypatch):
        """Test client credentials flow."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "client_creds_token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        mock_response.raise_for_status = Mock()
        
        async def mock_post(*args, **kwargs):
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            client = OSMOAuthClient()
            tokens = await client.get_client_credentials_token()
            
            assert tokens["access_token"] == "client_creds_token"
    
    @pytest.mark.asyncio
    async def test_refresh_access_token(self, monkeypatch):
        """Test token refresh."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        mock_response.raise_for_status = Mock()
        
        async def mock_post(*args, **kwargs):
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            client = OSMOAuthClient()
            tokens = await client.refresh_access_token("old_refresh_token")
            
            assert tokens["access_token"] == "new_access_token"
    
    def test_store_token(self, db_session):
        """Test storing OAuth token in database."""
        # Create test user
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed"
        )
        db_session.add(user)
        db_session.commit()
        
        client = OSMOAuthClient(db_session)
        
        tokens = {
            "access_token": "test_token",
            "refresh_token": "test_refresh",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "section:member:read"
        }
        
        oauth_token = client._store_token(user, tokens)
        
        assert oauth_token.user_id == user.id
        assert oauth_token.provider == OAuthProvider.OSM
        assert oauth_token.access_token == "test_token"
        assert oauth_token.refresh_token == "test_refresh"
        assert oauth_token.scope == "section:member:read"
        assert oauth_token.expires_at is not None
    
    def test_store_token_update_existing(self, db_session):
        """Test updating existing OAuth token."""
        # Create test user and initial token
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed"
        )
        db_session.add(user)
        db_session.commit()
        
        initial_token = OAuthToken(
            user_id=user.id,
            provider=OAuthProvider.OSM,
            access_token="old_token",
            refresh_token="old_refresh"
        )
        db_session.add(initial_token)
        db_session.commit()
        
        client = OSMOAuthClient(db_session)
        
        new_tokens = {
            "access_token": "new_token",
            "refresh_token": "new_refresh",
            "expires_in": 3600
        }
        
        updated_token = client._store_token(user, new_tokens)
        
        # Should update existing token, not create new one
        assert updated_token.id == initial_token.id
        assert updated_token.access_token == "new_token"
        assert updated_token.refresh_token == "new_refresh"
        
        # Verify only one token exists
        token_count = db_session.query(OAuthToken).filter(
            OAuthToken.user_id == user.id,
            OAuthToken.provider == OAuthProvider.OSM
        ).count()
        assert token_count == 1
    
    def test_get_stored_token(self, db_session):
        """Test retrieving stored token."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed"
        )
        db_session.add(user)
        db_session.commit()
        
        oauth_token = OAuthToken(
            user_id=user.id,
            provider=OAuthProvider.OSM,
            access_token="stored_token",
            refresh_token="stored_refresh"
        )
        db_session.add(oauth_token)
        db_session.commit()
        
        client = OSMOAuthClient(db_session)
        retrieved_token = client.get_stored_token(user)
        
        assert retrieved_token is not None
        assert retrieved_token.access_token == "stored_token"
        assert retrieved_token.user_id == user.id
    
    def test_get_stored_token_not_found(self, db_session):
        """Test retrieving non-existent token."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed"
        )
        db_session.add(user)
        db_session.commit()
        
        client = OSMOAuthClient(db_session)
        token = client.get_stored_token(user)
        
        assert token is None
    
    @pytest.mark.asyncio
    async def test_ensure_valid_token_not_expired(self, db_session):
        """Test ensuring valid token when not expired."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed"
        )
        db_session.add(user)
        db_session.commit()
        
        # Token expires in 1 hour
        expires_at = datetime.utcnow() + timedelta(hours=1)
        oauth_token = OAuthToken(
            user_id=user.id,
            provider=OAuthProvider.OSM,
            access_token="valid_token",
            refresh_token="refresh_token",
            expires_at=expires_at
        )
        db_session.add(oauth_token)
        db_session.commit()
        
        client = OSMOAuthClient(db_session)
        token = await client.ensure_valid_token(user)
        
        assert token == "valid_token"
    
    @pytest.mark.asyncio
    async def test_ensure_valid_token_expired(self, db_session, monkeypatch):
        """Test ensuring valid token when expired (should refresh)."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed"
        )
        db_session.add(user)
        db_session.commit()
        
        # Token expired 1 hour ago
        expires_at = datetime.utcnow() - timedelta(hours=1)
        oauth_token = OAuthToken(
            user_id=user.id,
            provider=OAuthProvider.OSM,
            access_token="expired_token",
            refresh_token="refresh_token",
            expires_at=expires_at
        )
        db_session.add(oauth_token)
        db_session.commit()
        
        # Mock refresh response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "refreshed_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600
        }
        mock_response.raise_for_status = Mock()
        
        async def mock_post(*args, **kwargs):
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            client = OSMOAuthClient(db_session)
            token = await client.ensure_valid_token(user)
            
            assert token == "refreshed_token"


class TestOSMAPIClient:
    """Test high-level API client."""
    
    @pytest.mark.asyncio
    async def test_api_client_get_headers(self, db_session):
        """Test getting headers with valid token."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed"
        )
        db_session.add(user)
        db_session.commit()
        
        # Token not expired
        expires_at = datetime.utcnow() + timedelta(hours=1)
        oauth_token = OAuthToken(
            user_id=user.id,
            provider=OAuthProvider.OSM,
            access_token="api_token",
            expires_at=expires_at
        )
        db_session.add(oauth_token)
        db_session.commit()
        
        api_client = OSMAPIClient(db_session, user)
        headers = await api_client._get_headers()
        
        assert headers["Authorization"] == "Bearer api_token"
        assert "Content-Type" in headers
    
    @pytest.mark.asyncio
    async def test_api_client_get_members(self, db_session):
        """Test getting members via API client."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed"
        )
        db_session.add(user)
        db_session.commit()
        
        expires_at = datetime.utcnow() + timedelta(hours=1)
        oauth_token = OAuthToken(
            user_id=user.id,
            provider=OAuthProvider.OSM,
            access_token="api_token",
            expires_at=expires_at
        )
        db_session.add(oauth_token)
        db_session.commit()
        
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [
                {"scoutid": 1, "firstname": "John", "lastname": "Doe"}
            ]
        }
        mock_response.raise_for_status = Mock()
        
        async def mock_request(*args, **kwargs):
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = mock_request
            
            api_client = OSMAPIClient(db_session, user)
            members = await api_client.get_members(section_id=12345)
            
            assert "items" in members
            assert len(members["items"]) == 1


# Fixtures

@pytest.fixture
def db_session():
    """Create a test database session."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base
    
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()
