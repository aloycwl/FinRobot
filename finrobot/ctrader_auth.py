from __future__ import annotations

import webbrowser
import requests
from urllib.parse import urlencode, urlparse, parse_qs

CTRADER_AUTH_URL = "https://connect.spotware.com/apps/authorize"
CTRADER_TOKEN_URL = "https://connect.spotware.com/apps/token"


def generate_auth_url(client_id: str, redirect_uri: str = "https://localhost/callback") -> str:
    """Generate cTrader OAuth authorization URL for user login"""
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": "trading",
        "access_type": "offline"
    }
    return f"{CTRADER_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(client_id: str, client_secret: str, code: str, redirect_uri: str = "https://localhost/callback"):
    """Exchange authorization code for long-lived access token"""
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri
    }

    response = requests.post(CTRADER_TOKEN_URL, data=payload)
    response.raise_for_status()
    return response.json()


def extract_code_from_redirect_url(redirect_url: str) -> str:
    """Extract authorization code from the browser redirect URL"""
    parsed = urlparse(redirect_url)
    query_params = parse_qs(parsed.query)
    if "code" not in query_params:
        raise ValueError("No authorization code found in URL")
    return query_params["code"][0]


def start_oauth_flow(client_id: str, client_secret: str):
    """Interactive full OAuth flow for headless setup"""
    auth_url = generate_auth_url(client_id)

    print("\n=== cTrader OAuth Authentication ===")
    print("1. Open this link in your browser and login:")
    print(f"\n{auth_url}\n")
    print("2. After login you will be redirected to a localhost page")
    print("3. Copy the FULL URL from your browser address bar")

    redirect_url = input("\nPaste the full redirected URL here: ").strip()

    code = extract_code_from_redirect_url(redirect_url)
    tokens = exchange_code_for_token(client_id, client_secret, code)

    print("\n✅ Authentication successful!")
    print(f"\nAdd these values to your .env file:")
    print(f"CTRADER_ACCESS_TOKEN={tokens['access_token']}")
    print(f"CTRADER_EXPIRES_IN={tokens['expires_in']}")
    print(f"\nThis access token will be valid for 1 full year.")

    return tokens


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3:
        start_oauth_flow(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python -m finrobot.ctrader_auth <CLIENT_ID> <CLIENT_SECRET>")
