import hashlib
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