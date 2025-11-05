"""
Example script demonstrating OSM OAuth2 integration.

Usage:
    python examples/osm_oauth_example.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from osm_oauth import OSMOAuthClient


async def main():
    print("=" * 60)
    print("OSM OAuth2 Integration Example")
    print("=" * 60)
    
    oauth_client = OSMOAuthClient()
    
    print("\n1. Generate Authorization URL:")
    import secrets
    state = secrets.token_urlsafe(32)
    auth_url = oauth_client.get_authorization_url(state=state)
    
    print(f"\nAuthorization URL:\n{auth_url}\n")
    print("Redirect user to this URL to authorize.")
    print("\nAfter authorization:")
    print("  tokens = await oauth_client.exchange_code_for_token(code, user)")
    print("\nFor complete documentation, see OSM_OAUTH_SETUP.md")


if __name__ == "__main__":
    asyncio.run(main())
