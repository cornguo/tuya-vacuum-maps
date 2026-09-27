"""Tuya Cloud API client that reuses its access token.

tuya-vacuum fetches a new access token before every request, doubling the
number of API calls, and only makes GET requests. This client keeps the token
until shortly before it expires and one HTTP connection, and signs requests
with their body, following
https://developer.tuya.com/en/docs/iot/new-singnature?id=Kbw0q34cs2e5g
"""

import hashlib
import hmac
import json
import threading
import time
import uuid

import httpx

TOKEN_PATH = "/v1.0/token?grant_type=1"

# Renew the token this many seconds before it expires
TOKEN_RENEW_MARGIN = 60

# Error codes of a token that's invalid or expired
TOKEN_ERROR_CODES = {1010, 1011}


class TuyaCloudError(Exception):
    """A Tuya Cloud API request failed."""

    def __init__(self, response: dict) -> None:
        """Initialize the error from Tuya's response."""
        super().__init__(f"{response.get('msg')} ({response.get('code')})")
        self.code = response.get("code")


def sign(
    client_id: str,
    client_secret: str,
    access_token: str,
    timestamp: str,
    nonce: str,
    method: str,
    body: str,
    path: str,
) -> str:
    """Return the signature of a Tuya Cloud API request."""
    body_hash = hashlib.sha256(body.encode()).hexdigest()
    string_to_sign = (
        f"{client_id}{access_token}{timestamp}{nonce}{method}\n{body_hash}\n\n{path}"
    )
    return (
        hmac.new(client_secret.encode(), string_to_sign.encode(), "sha256")
        .hexdigest()
        .upper()
    )


class TuyaCloud:
    """Make Tuya Cloud API requests. The methods make blocking network calls."""

    def __init__(
        self,
        origin: str,
        client_id: str,
        client_secret: str,
        client: httpx.Client | None = None,
    ) -> None:
        """Initialize the client."""
        self._origin = origin
        self._client_id = client_id
        self._client_secret = client_secret
        self._client = client or httpx.Client(timeout=15)
        self._token: str | None = None
        self._token_expires_at = 0.0
        # Updates and commands run in different executor threads
        self._token_lock = threading.Lock()

    def close(self) -> None:
        """Close the HTTP connection."""
        self._client.close()

    def get(self, path: str) -> dict:
        """Make a GET request and return its result."""
        return self._request("GET", path)

    def post(self, path: str, body: dict) -> dict:
        """Make a POST request with a JSON body and return its result."""
        return self._request("POST", path, json.dumps(body, separators=(",", ":")))

    def download(self, url: str) -> bytes:
        """Download a file, e.g. from a link returned by the API."""
        response = self._client.get(url)
        response.raise_for_status()
        return response.content

    def _request(self, method: str, path: str, body: str = "") -> dict:
        """Make a request, renewing the token once if Tuya rejects it."""
        try:
            return self._send(method, path, body, self._access_token())
        except TuyaCloudError as err:
            if err.code not in TOKEN_ERROR_CODES:
                raise
            with self._token_lock:
                self._token = None
            return self._send(method, path, body, self._access_token())

    def _access_token(self) -> str:
        """Return the access token, fetching a new one when needed."""
        with self._token_lock:
            if self._token is None or time.monotonic() >= self._token_expires_at:
                result = self._send("GET", TOKEN_PATH, "", "")
                self._token = result["access_token"]
                self._token_expires_at = (
                    time.monotonic() + result["expire_time"] - TOKEN_RENEW_MARGIN
                )
            return self._token

    def _send(self, method: str, path: str, body: str, access_token: str):
        """Send a signed request and return its result."""
        timestamp = str(int(time.time() * 1000))
        nonce = uuid.uuid4().hex
        headers = {
            "client_id": self._client_id,
            "sign": sign(
                self._client_id,
                self._client_secret,
                access_token,
                timestamp,
                nonce,
                method,
                body,
                path,
            ),
            "sign_method": "HMAC-SHA256",
            "t": timestamp,
            "nonce": nonce,
            "Content-Type": "application/json",
        }
        if access_token:
            headers["access_token"] = access_token

        response = self._client.request(
            method, f"{self._origin}{path}", headers=headers, content=body or None
        ).json()
        if not response.get("success"):
            raise TuyaCloudError(response)
        return response["result"]
