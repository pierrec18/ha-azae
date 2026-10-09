"""Async API client. Tokens are kept in memory and never logged."""
import asyncio
from time import monotonic
from datetime import timedelta
from aiohttp import ClientError, ClientTimeout
from .const import BASE_URL
from .model import SchemaError, pointer

class ApiError(Exception):
    """Sanitized transport/server error."""

class AuthError(ApiError):
    """Credentials rejected."""

class RateLimitError(ApiError):
    """Server asked for backoff."""
    def __init__(self, retry_after=300):
        super().__init__("rate_limited")
        self.retry_after = retry_after

class AzaeApi:
    def __init__(self, session, email, password, agency, matricule, token_path):
        self.session = session
        self.email = email
        self.password = password
        self.agency = agency
        self.matricule = matricule
        self.token_path = token_path
        self._token = None
        self._lock = asyncio.Lock()
        self._retry_until = 0.0

    async def _post(self, endpoint, body, token=None):
        if self._retry_until > monotonic():
            raise RateLimitError(max(60, int(self._retry_until - monotonic())))
        headers = {"Accept": "application/json", "client-name": "Extranet.Front",
                   "Origin": "https://extranet.a2micile.com",
                   "Referer": "https://extranet.a2micile.com/"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            async with self.session.post(
                f"{BASE_URL}/{endpoint}", headers=headers, json=body,
                timeout=ClientTimeout(total=20), allow_redirects=False,
            ) as response:
                if response.status in (401, 403):
                    raise AuthError("authentication_rejected")
                if response.status == 429:
                    value = response.headers.get("Retry-After", "300")
                    delay = int(value) if value.isdecimal() else 300
                    delay = max(60, min(delay, 86400))
                    self._retry_until = monotonic() + delay
                    raise RateLimitError(delay)
                if response.status < 200 or response.status >= 300:
                    raise ApiError("http_error")
                try:
                    payload = await response.json()
                except (ValueError, ClientError):
                    raise SchemaError("invalid_json") from None
                # Observed login envelope: a 200 response can still carry failure.
                if isinstance(payload, dict) and payload.get("success") is False:
                    if endpoint == "login":
                        raise AuthError("login_rejected")
                    raise ApiError("application_error")
                if isinstance(payload, dict) and payload.get("status") in (401, 403):
                    raise AuthError("authentication_rejected")
                return payload
        except (ClientError, TimeoutError):
            raise ApiError("cannot_connect") from None

    async def _login_unlocked(self):
        payload = await self._post("login", {"email": self.email, "password": self.password})
        token = pointer(payload, self.token_path)
        if not isinstance(token, str) or not token.strip() or any(char.isspace() for char in token):
            raise SchemaError("invalid_token")
        self._token = token

    async def login(self):
        async with self._lock:
            await self._login_unlocked()

    async def hours(self, start, end):
        """Date query bounds are padded; API end-date inclusivity is undocumented."""
        async with self._lock:
            if self._token is None:
                await self._login_unlocked()
            body = {"type": "Usager", "code_agence": self.agency,
                    "matricule": self.matricule, "matricules": None,
                    "start": (start - timedelta(days=1)).isoformat(),
                    "end": (end + timedelta(days=1)).isoformat()}
            try:
                return await self._post("get_liste_heures", body, self._token)
            except AuthError:
                self._token = None
                await self._login_unlocked()
                # One retry only. No undocumented refresh-token endpoint.
                try:
                    return await self._post("get_liste_heures", body, self._token)
                except AuthError:
                    self._token = None
                    raise
