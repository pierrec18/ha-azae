from datetime import date
from unittest.mock import MagicMock, AsyncMock
import pytest
from aiohttp import ClientConnectionError
from custom_components.azae.api import AzaeApi, ApiError, AuthError, RateLimitError
from custom_components.azae.model import SchemaError

class Response:
    def __init__(self, status=200, payload=None, headers=None):
        self.status, self.payload, self.headers = status, payload, headers or {}
    async def __aenter__(self): return self
    async def __aexit__(self, *args): return False
    async def json(self):
        if isinstance(self.payload, Exception): raise self.payload
        return self.payload

def api(responses):
    session = MagicMock()
    session.post.side_effect = responses
    return AzaeApi(session, "client@example.invalid", "synthetic-test-password", "0001", "client", "/data/user/token")

def token():
    return Response(payload={"success": True, "data": {"user": {"token": "synthetic-token"}}})

async def test_payload_headers_and_refresh():
    client = api([token(), Response(401), token(), Response(payload=[])])
    assert await client.hours(date(2026, 10, 9), date(2026, 10, 10)) == []
    calls = client.session.post.call_args_list
    assert len(calls) == 4
    assert calls[0].kwargs["headers"]["client-name"] == "Extranet.Front"
    assert calls[1].kwargs["json"] == {"type": "Usager", "code_agence": "0001", "matricule": "client", "matricules": None, "start": "2026-10-08", "end": "2026-10-11"}
    assert calls[1].kwargs["headers"]["Authorization"] == "Bearer synthetic-token"
    assert calls[0].kwargs["allow_redirects"] is False

async def test_one_retry_and_no_loop():
    client = api([token(), Response(403), token(), Response(401)])
    with pytest.raises(AuthError):
        await client.hours(date.today(), date.today())
    assert client.session.post.call_count == 4
    assert client._token is None

@pytest.mark.parametrize("response,error", [
    (Response(401), AuthError), (Response(200, {"success": False}), AuthError),
    (Response(500), ApiError), (Response(302), ApiError),
    (Response(200, ValueError("sensitive-body")), SchemaError),
    (Response(200, {"token": "wrong-path"}), SchemaError),
    (ClientConnectionError("sensitive-body"), ApiError)])
async def test_safe_errors(response, error):
    client = api([response])
    with pytest.raises(error) as result:
        await client.login()
    assert "sensitive" not in str(result.value)

async def test_rate_limit():
    client = api([Response(429, headers={"Retry-After": "1200"})])
    with pytest.raises(RateLimitError) as result:
        await client.login()
    assert result.value.retry_after == 1200

async def test_shared_backoff_blocks_calendar_and_poll():
    client = api([Response(429, headers={"Retry-After": "1200"})])
    with pytest.raises(RateLimitError):
        await client.hours(date.today(), date.today())
    with pytest.raises(RateLimitError):
        await client.hours(date.today(), date.today())
    assert client.session.post.call_count == 1
