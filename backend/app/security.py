"""Password hashing (scrypt) and signed bearer tokens, using only the standard library."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${key.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt_hex, key_hex = stored.split("$")
    except ValueError:
        return False
    if algo != "scrypt":
        return False
    key = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **_SCRYPT)
    return hmac.compare_digest(key.hex(), key_hex)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: str) -> str:
    return _b64(hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).digest())


def create_token(user_id: int) -> str:
    body = _b64(json.dumps({"sub": user_id, "exp": int(time.time()) + settings.token_ttl_hours * 3600}).encode())
    return f"{body}.{_sign(body)}"


def read_token(token: str) -> int | None:
    try:
        body, signature = token.split(".")
    except ValueError:
        return None
    if not hmac.compare_digest(signature, _sign(body)):
        return None
    try:
        claims = json.loads(_unb64(body))
    except ValueError:
        return None
    if claims.get("exp", 0) < time.time():
        return None
    return int(claims["sub"])


_bearer = HTTPBearer(auto_error=False)


def optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)
) -> User | None:
    if not creds:
        return None
    user_id = read_token(creds.credentials)
    return db.get(User, user_id) if user_id else None


def current_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue")
    return user
