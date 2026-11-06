from argon2 import PasswordHasher
from argon2.exceptions import (
    VerifyMismatchError,
    VerificationError,
    InvalidHashError,
)

# Argon2id password hasher
password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2id.
    """

    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verify a password against its stored Argon2id hash.
    """

    try:
        return password_hasher.verify(
            hashed_password,
            plain_password,
        )

    except (
        VerifyMismatchError,
        VerificationError,
        InvalidHashError,
    ):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """
    Check whether a password hash needs updating.
    """

    try:
        return password_hasher.check_needs_rehash(
            hashed_password
        )

    except (VerificationError, InvalidHashError):
        return True

