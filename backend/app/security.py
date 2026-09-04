"""Password hashing and session-token helpers.

Uses the ``bcrypt`` library directly rather than passlib — passlib 1.7.x's
bcrypt backend self-test is incompatible with bcrypt>=4.1 (raises on a
strict 72-byte length check), and passlib is unmaintained.
"""

from __future__ import annotations

import hashlib
import secrets

import bcrypt

_MAX_PASSWORD_BYTES = 72  # bcrypt's hard limit


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("ascii")


def verify_password(candidate: str, stored_hash: str) -> bool:
    encoded = candidate.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    try:
        return bcrypt.checkpw(encoded, stored_hash.encode("ascii"))
    except ValueError:
        return False


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


# One-time tokens (password reset, OAuth state) share the session token's
# randomness; reset tokens are stored hashed.
new_token = new_session_token


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
