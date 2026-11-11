"""Content addressing compatible with IPFS.

A receipt is serialised to canonical JSON and identified by its CIDv1:

    multibase 'b' (base32, lowercase, no padding) of
        <version 0x01> <codec raw 0x55> <multihash sha2-256 0x12> <length 0x20> <digest>

This is exactly the CID `ipfs add --cid-version=1 --raw-leaves` assigns to a single-block
file, so a pinned receipt keeps the same identifier on the IPFS network. Anyone can
re-derive it from the bytes; no node or third-party service is required to verify.
"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

_PREFIX = bytes([0x01, 0x55, 0x12, 0x20])


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def cid_for_bytes(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return "b" + base64.b32encode(_PREFIX + digest).decode("ascii").lower().rstrip("=")


def digest_from_cid(cid: str) -> bytes | None:
    """Return the sha256 digest inside a CIDv1/raw/sha256 string, or None if malformed."""
    if not cid.startswith("b"):
        return None
    body = cid[1:].upper()
    body += "=" * (-len(body) % 8)
    try:
        raw = base64.b32decode(body)
    except Exception:
        return None
    if len(raw) != 36 or raw[:4] != _PREFIX:
        return None
    return raw[4:]
