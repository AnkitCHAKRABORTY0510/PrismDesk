"""Minimal Discord REST client used by the worker and OAuth linking.

The bot token and OAuth secret are only ever placed in request headers
or form bodies; they are never logged or returned by the API.
"""

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.config import settings

TIMEOUT = httpx.Timeout(10.0)


@dataclass
class DeliveryResult:
    success: bool
    http_status: int | None = None
    error: str | None = None
    retryable: bool = True
    channel_id: str | None = None


class DiscordSender:
    """Sends DMs and channel messages through the bot account."""

    def __init__(self, client: httpx.Client | None = None):
        self._client = client or httpx.Client(timeout=TIMEOUT)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bot {settings.DISCORD_BOT_TOKEN}"}

    def _result(self, response: httpx.Response) -> DeliveryResult:
        if response.is_success:
            return DeliveryResult(True, response.status_code)

        # 4xx other than rate limiting will not fix themselves (blocked
        # DMs, unknown user, missing permissions).
        retryable = response.status_code == 429 or response.status_code >= 500
        return DeliveryResult(
            False,
            response.status_code,
            f"Discord API returned HTTP {response.status_code}.",
            retryable,
        )

    def open_dm_channel(self, discord_user_id: str) -> DeliveryResult:
        response = self._client.post(
            f"{settings.DISCORD_API_BASE_URL}/users/@me/channels",
            headers=self._headers(),
            json={"recipient_id": discord_user_id},
        )
        result = self._result(response)
        if result.success:
            result.channel_id = response.json().get("id")
        return result

    def send_message(self, channel_id: str, content: str) -> DeliveryResult:
        response = self._client.post(
            f"{settings.DISCORD_API_BASE_URL}/channels/{channel_id}/messages",
            headers=self._headers(),
            # Never ping @everyone/roles from generated content.
            json={"content": content[:2000], "allowed_mentions": {"parse": []}},
        )
        return self._result(response)


def oauth_authorize_url(state: str) -> str:
    query = urlencode(
        {
            "client_id": settings.DISCORD_CLIENT_ID,
            "redirect_uri": settings.DISCORD_REDIRECT_URI,
            "response_type": "code",
            "scope": "identify",
            "state": state,
            "prompt": "consent",
        }
    )
    return f"https://discord.com/oauth2/authorize?{query}"


def oauth_fetch_identity(code: str) -> dict:
    """Exchange an authorization code and return the Discord user object.

    The access token is used for this single call and then dropped.
    """

    with httpx.Client(timeout=TIMEOUT) as client:
        token_response = client.post(
            f"{settings.DISCORD_API_BASE_URL}/oauth2/token",
            data={
                "client_id": settings.DISCORD_CLIENT_ID,
                "client_secret": settings.DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.DISCORD_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_response.raise_for_status()
        access_token = token_response.json()["access_token"]

        user_response = client.get(
            f"{settings.DISCORD_API_BASE_URL}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_response.raise_for_status()
        return user_response.json()
