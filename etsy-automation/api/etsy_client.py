"""
Etsy API v3 Client
Handles OAuth 2.0 authentication and all HTTP calls to the Etsy API.

Setup:
  1. Create an Etsy app at https://www.etsy.com/developers/register
  2. Copy .env.example to .env and fill in ETSY_API_KEY + ETSY_SHOP_ID
  3. Run `python api/etsy_client.py --auth` to complete OAuth flow and get tokens
"""

import json
import os
import sys
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Optional

import requests

BASE_URL = "https://openapi.etsy.com/v3"
OAUTH_URL = "https://www.etsy.com/oauth/connect"
TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
REDIRECT_URI = "http://localhost:3003/oauth/redirect"
SCOPES = "listings_r listings_w transactions_r conversations_r conversations_w shops_r"


def _env(key: str, required: bool = True) -> str:
    val = os.environ.get(key, "")
    if required and not val:
        sys.exit(f"[etsy_client] Missing env var: {key}. See .env.example")
    return val


class EtsyClient:
    """Thin wrapper around the Etsy API v3.  One instance per shop."""

    def __init__(self):
        self.api_key = _env("ETSY_API_KEY")
        self.shop_id = _env("ETSY_SHOP_ID")
        self.access_token = os.environ.get("ETSY_ACCESS_TOKEN", "")
        self.refresh_token = os.environ.get("ETSY_REFRESH_TOKEN", "")
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": self.api_key})

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _auth_headers(self) -> dict:
        if not self.access_token:
            sys.exit("[etsy_client] No access token. Run --auth to authenticate.")
        return {"Authorization": f"Bearer {self.access_token}"}

    def _get(self, path: str, params: Optional[dict] = None, auth: bool = False) -> Any:
        headers = self._auth_headers() if auth else {}
        resp = self.session.get(f"{BASE_URL}{path}", params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict, auth: bool = True) -> Any:
        headers = {**self._auth_headers(), "Content-Type": "application/json"}
        resp = self.session.post(f"{BASE_URL}{path}", json=body, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def _patch(self, path: str, body: dict, auth: bool = True) -> Any:
        headers = {**self._auth_headers(), "Content-Type": "application/json"}
        resp = self.session.patch(f"{BASE_URL}{path}", json=body, headers=headers)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------ #
    # OAuth helpers                                                        #
    # ------------------------------------------------------------------ #

    def _start_oauth_flow(self) -> str:
        """Open browser to Etsy OAuth and capture the redirect code."""
        import hashlib, base64, secrets
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()

        params = urllib.parse.urlencode({
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "client_id": self.api_key,
            "state": secrets.token_hex(8),
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        })
        url = f"{OAUTH_URL}?{params}"
        print(f"\n[etsy_client] Opening browser for Etsy OAuth...\n{url}\n")
        webbrowser.open(url)

        code = [None]

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                code[0] = qs.get("code", [None])[0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Auth complete. You can close this tab.")
                self.server.code = code[0]

            def log_message(self, *_):
                pass

        server = HTTPServer(("localhost", 3003), _Handler)
        server.handle_request()
        return server.code, verifier

    def authenticate(self):
        """Full OAuth 2.0 PKCE flow. Prints tokens to stdout."""
        code, verifier = self._start_oauth_flow()
        resp = requests.post(TOKEN_URL, data={
            "grant_type": "authorization_code",
            "client_id": self.api_key,
            "redirect_uri": REDIRECT_URI,
            "code": code,
            "code_verifier": verifier,
        })
        resp.raise_for_status()
        tokens = resp.json()
        print("\n[etsy_client] Auth successful! Add these to your .env:\n")
        print(f"ETSY_ACCESS_TOKEN={tokens['access_token']}")
        print(f"ETSY_REFRESH_TOKEN={tokens['refresh_token']}")

    # ------------------------------------------------------------------ #
    # Public API methods                                                   #
    # ------------------------------------------------------------------ #

    def ping(self) -> bool:
        try:
            self._get("/application/openapi-ping")
            return True
        except Exception:
            return False

    def get_shop(self) -> dict:
        return self._get(f"/application/shops/{self.shop_id}", auth=True)

    # --- Listings ---

    def search_listings(self, keywords: str, limit: int = 25, sort_on: str = "score") -> list:
        """Search active Etsy listings (public, no OAuth needed)."""
        data = self._get("/application/listings/active", params={
            "keywords": keywords,
            "limit": limit,
            "sort_on": sort_on,
            "includes": "Images",
        })
        return data.get("results", [])

    def get_shop_listings(self, state: str = "active", limit: int = 25) -> list:
        data = self._get(
            f"/application/shops/{self.shop_id}/listings/{state}",
            params={"limit": limit},
            auth=True,
        )
        return data.get("results", [])

    def create_listing(
        self,
        title: str,
        description: str,
        price_usd: float,
        quantity: int,
        tags: list[str],
        taxonomy_id: int,
        listing_type: str = "download",   # "download" | "physical"
        shipping_profile_id: Optional[int] = None,
    ) -> dict:
        body = {
            "title": title[:140],
            "description": description,
            "price": price_usd,
            "quantity": quantity,
            "tags": tags[:13],
            "taxonomy_id": taxonomy_id,
            "who_made": "i_did",
            "when_made": "made_to_order",
            "is_supply": False,
            "type": listing_type,
        }
        if shipping_profile_id:
            body["shipping_profile_id"] = shipping_profile_id
        return self._post(f"/application/shops/{self.shop_id}/listings", body)

    def update_listing(self, listing_id: int, **kwargs) -> dict:
        return self._patch(f"/application/listings/{listing_id}", kwargs)

    # --- Transactions / Analytics ---

    def get_receipts(self, limit: int = 100) -> list:
        data = self._get(
            f"/application/shops/{self.shop_id}/receipts",
            params={"limit": limit, "was_paid": True},
            auth=True,
        )
        return data.get("results", [])

    def get_transactions(self, limit: int = 100) -> list:
        data = self._get(
            f"/application/shops/{self.shop_id}/transactions",
            params={"limit": limit},
            auth=True,
        )
        return data.get("results", [])

    # --- Conversations (Customer Service) ---

    def get_conversations(self, limit: int = 25) -> list:
        data = self._get(
            f"/application/shops/{self.shop_id}/conversations",
            params={"limit": limit},
            auth=True,
        )
        return data.get("results", [])

    def send_message(self, conversation_id: int, message: str) -> dict:
        return self._post(
            f"/application/shops/{self.shop_id}/conversations/{conversation_id}/messages",
            {"message": message},
        )


if __name__ == "__main__":
    if "--auth" in sys.argv:
        client = EtsyClient()
        client.authenticate()
    elif "--ping" in sys.argv:
        client = EtsyClient()
        ok = client.ping()
        print(f"[etsy_client] API reachable: {ok}")
    else:
        print("Usage: python api/etsy_client.py [--auth | --ping]")
