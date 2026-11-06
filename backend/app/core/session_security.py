import hashlib
import hmac
import secrets


def generate_session_token() -> str:
    """
    Generate a cryptographically secure session token.
    """

    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """
    Generate a SHA-256 hash of the session token.
    """

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def derive_csrf_token(session_token: str) -> str:
    """
    Derive the CSRF token bound to a session.

    The session cookie is HttpOnly, so a cross-site attacker can neither
    read it nor compute this value. The browser receives the token in
    the login and /auth/me responses and echoes it in a request header.
    """

    return hashlib.sha256(
        f"prism-csrf:{session_token}".encode("utf-8")
    ).hexdigest()


def csrf_token_matches(session_token: str, supplied: str | None) -> bool:
    if not supplied:
        return False

    return hmac.compare_digest(
        derive_csrf_token(session_token),
        supplied,
    )
