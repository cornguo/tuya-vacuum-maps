"""Send device commands through the Tuya Cloud API.

tuya-vacuum only makes GET requests, and signs them with the hash of an empty
body, so commands are sent here with the same signature algorithm including
the request body:
https://developer.tuya.com/en/docs/iot/new-singnature?id=Kbw0q34cs2e5g
"""

import hashlib
import hmac
import json
import time
import uuid

import httpx
from tuya_vacuum.tuya import ACCESS_TOKEN_ENDPOINT, TuyaCloudAPI


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


def send_commands(
    origin: str,
    client_id: str,
    client_secret: str,
    device_id: str,
    commands: list[dict],
) -> None:
    """Send commands to a device. This makes blocking network calls."""
    with httpx.Client(timeout=15) as client:
        api = TuyaCloudAPI(origin, client_id, client_secret, client)
        access_token = api.request("GET", ACCESS_TOKEN_ENDPOINT, fetch_token=False)[
            "result"
        ]["access_token"]

        path = f"/v1.0/devices/{device_id}/commands"
        body = json.dumps({"commands": commands}, separators=(",", ":"))
        timestamp = str(int(time.time() * 1000))
        nonce = uuid.uuid4().hex
        headers = {
            "client_id": client_id,
            "access_token": access_token,
            "sign": sign(
                client_id,
                client_secret,
                access_token,
                timestamp,
                nonce,
                "POST",
                body,
                path,
            ),
            "sign_method": "HMAC-SHA256",
            "t": timestamp,
            "nonce": nonce,
            "Content-Type": "application/json",
        }
        response = client.post(f"{origin}{path}", headers=headers, content=body)

    result = response.json()
    if not result.get("success"):
        raise RuntimeError(
            f"Tuya rejected the command: {result.get('msg')} ({result.get('code')})"
        )
