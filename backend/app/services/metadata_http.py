"""Small, defensive HTTP helper for paper metadata lookups.

Every outbound request made to resolve paper metadata goes through
``fetch``: short timeouts, a capped response size, a neutral User-Agent
and manual redirect handling. Requests for user-supplied links also pass
``public_only=True`` so every hop is checked against private, loopback
and link-local addresses (SSRF protection).
"""

import ipaddress
import json
import logging
import socket
from dataclasses import dataclass

import httpx

from app.core.errors import BadRequestError, NotFoundError, ServiceError

logger = logging.getLogger("prism.metadata")

USER_AGENT = "PrismDesk/1.0 (research library paper metadata lookup)"
TIMEOUT = httpx.Timeout(8.0, connect=4.0)
MAX_BYTES = 3_000_000
MAX_REDIRECTS = 5
ALLOWED_PORTS = {None, 80, 443}


class LookupUnavailableError(ServiceError):
    status_code = 502


class LookupTimeoutError(ServiceError):
    status_code = 504


class UnsafeUrlError(BadRequestError):
    status_code = 422


@dataclass
class FetchResult:
    status_code: int
    content_type: str
    content: bytes
    encoding: str
    url: str

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def text(self) -> str:
        return self.content.decode(self.encoding or "utf-8", errors="replace")

    def json(self):
        try:
            return json.loads(self.content)
        except ValueError:
            raise LookupUnavailableError("The metadata service returned an unexpected response.")


def _transport() -> httpx.BaseTransport | None:
    """Overridden in tests with an ``httpx.MockTransport``."""

    return None


def _resolve(host: str, port: int) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError):
        raise NotFoundError("That website could not be found. Check the link.")
    return [info[4][0] for info in infos]


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def ensure_public_url(url: str) -> None:
    """Reject links that are not plain http(s) to a public internet host."""

    try:
        parsed = httpx.URL(url)
    except httpx.InvalidURL:
        raise UnsafeUrlError("This link is not a valid web address.")
    if parsed.scheme not in ("http", "https") or not parsed.host:
        raise UnsafeUrlError("Only http:// and https:// links can be fetched.")
    if parsed.userinfo:
        raise UnsafeUrlError("Links with a username or password cannot be fetched.")
    if parsed.port not in ALLOWED_PORTS:
        raise UnsafeUrlError("Only links on the standard web ports can be fetched.")

    addresses = _resolve(parsed.host, parsed.port or (443 if parsed.scheme == "https" else 80))
    if not addresses or not all(_is_public(address) for address in addresses):
        raise UnsafeUrlError("This link points to a private or local address and cannot be fetched.")


def fetch(
    url: str,
    *,
    params: dict | None = None,
    accept: str | None = None,
    public_only: bool = False,
    timeout: httpx.Timeout = TIMEOUT,
    service: str = "the metadata service",
) -> FetchResult:
    """GET ``url`` and return at most ``MAX_BYTES`` of the body."""

    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept

    try:
        with httpx.Client(timeout=timeout, transport=_transport(), headers=headers) as client:
            for _ in range(MAX_REDIRECTS + 1):
                if public_only:
                    ensure_public_url(url)
                with client.stream("GET", url, params=params) as response:
                    if response.is_redirect and "location" in response.headers:
                        url = str(response.url.join(response.headers["location"]))
                        params = None
                        continue
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) >= MAX_BYTES:
                            break
                    return FetchResult(
                        status_code=response.status_code,
                        content_type=response.headers.get("content-type", "").split(";")[0].strip().lower(),
                        content=bytes(body[:MAX_BYTES]),
                        encoding=response.charset_encoding or "utf-8",
                        url=str(response.url),
                    )
    except httpx.TimeoutException:
        logger.warning("Metadata request to %s timed out", service)
        raise LookupTimeoutError(f"{service[0].upper()}{service[1:]} did not respond in time. Try again.")
    except httpx.HTTPError as error:
        logger.warning("Metadata request to %s failed: %s", service, type(error).__name__)
        raise LookupUnavailableError(f"Could not reach {service}. Try again later.")

    raise LookupUnavailableError("The link redirected too many times.")
