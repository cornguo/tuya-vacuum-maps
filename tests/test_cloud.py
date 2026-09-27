"""Tests for the Tuya Cloud client, with a fake server instead of the network."""

import hmac
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

# Load the module by path so the test doesn't import the integration package,
# whose __init__ requires Home Assistant.
_SPEC = importlib.util.spec_from_file_location(
    "cloud",
    Path(__file__).parent.parent / "custom_components" / "tuya_vacuum_maps" / "cloud.py",
)
cloud = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cloud)

ORIGIN = "https://tuya.test"


class FakeTuya:
    """Answer token and API requests like Tuya, recording them."""

    def __init__(self, expire_time: int = 7200) -> None:
        self.expire_time = expire_time
        self.requests: list[httpx.Request] = []
        self.tokens_issued = 0
        # Token the next API request is rejected with, as if it expired
        self.reject_token: str | None = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == "/v1.0/token":
            self.tokens_issued += 1
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "result": {
                        "access_token": f"token-{self.tokens_issued}",
                        "expire_time": self.expire_time,
                    },
                },
            )
        token = request.headers.get("access_token")
        if token == self.reject_token:
            return httpx.Response(200, json={"success": False, "code": 1010})
        return httpx.Response(
            200, json={"success": True, "result": {"token": token}}
        )

    def api_requests(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.url.path != "/v1.0/token"]


def _cloud(fake: FakeTuya):
    return cloud.TuyaCloud(
        ORIGIN, "id", "secret", httpx.Client(transport=httpx.MockTransport(fake.handler))
    )


def test_token_is_reused_until_it_expires():
    """Several requests share one token instead of fetching one each."""
    fake = FakeTuya()
    client = _cloud(fake)

    for _ in range(3):
        assert client.get("/v1.0/devices/d/status") == {"token": "token-1"}

    assert fake.tokens_issued == 1
    assert len(fake.api_requests()) == 3


def test_token_is_renewed_before_it_expires():
    """A token about to expire is replaced before it's used."""
    # Expires within the renew margin, so every request needs a new one
    fake = FakeTuya(expire_time=cloud.TOKEN_RENEW_MARGIN)
    client = _cloud(fake)

    client.get("/p")
    client.get("/p")

    assert fake.tokens_issued == 2


def test_rejected_token_is_renewed_once():
    """A request rejected for its token is retried with a new token."""
    fake = FakeTuya()
    client = _cloud(fake)
    client.get("/p")
    fake.reject_token = "token-1"

    assert client.get("/p") == {"token": "token-2"}


def test_other_errors_are_raised():
    """Errors other than token errors aren't retried."""
    fake = FakeTuya()
    fake.handler = lambda request: httpx.Response(
        200, json={"success": False, "code": 28841101, "msg": "not subscribed"}
    )
    client = _cloud(fake)

    with pytest.raises(cloud.TuyaCloudError, match="28841101"):
        client.get("/p")


def test_post_sends_and_signs_its_body():
    """Commands are sent as JSON and signed with the hash of that body."""
    fake = FakeTuya()
    client = _cloud(fake)

    client.post("/v1.0/devices/d/commands", {"commands": [{"code": "a"}]})

    request = fake.api_requests()[0]
    body = request.content.decode()
    assert json.loads(body) == {"commands": [{"code": "a"}]}
    assert request.headers["sign"] == cloud.sign(
        "id",
        "secret",
        "token-1",
        request.headers["t"],
        request.headers["nonce"],
        "POST",
        body,
        "/v1.0/devices/d/commands",
    )


def test_signature_follows_tuya_documentation():
    """The signed string has Tuya's layout, with the SHA-256 of the body."""
    args = ("id", "secret", "token", "1700000000000", "nonce", "POST")

    assert cloud.sign(*args, '{"a":1}', "/p") != cloud.sign(*args, '{"a":2}', "/p")
    assert cloud.sign(*args, "", "/p") == hmac.new(
        b"secret",
        (
            "idtoken1700000000000noncePOST\n"
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n\n/p"
        ).encode(),
        "sha256",
    ).hexdigest().upper()
