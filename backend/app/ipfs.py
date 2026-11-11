"""Optional pinning of receipts to IPFS through a Kubo-compatible RPC API."""
from __future__ import annotations

import httpx

from .config import settings


def enabled() -> bool:
    return bool(settings.ipfs_rpc_url)


def pin(data: bytes, expected_cid: str) -> tuple[bool, str]:
    """Add and pin `data`. Returns (pinned, error). The node must assign the same CID we
    computed locally; a mismatch is reported rather than silently accepted."""
    if not enabled():
        return False, ""
    headers = {"Authorization": f"Bearer {settings.ipfs_rpc_token}"} if settings.ipfs_rpc_token else {}
    try:
        resp = httpx.post(
            f"{settings.ipfs_rpc_url}/api/v0/add",
            params={"cid-version": "1", "raw-leaves": "true", "pin": "true"},
            files={"file": ("receipt.json", data, "application/json")},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        returned = resp.json().get("Hash", "")
    except Exception as exc:  # network errors must never break an exchange
        return False, f"pin failed: {exc}"[:500]
    if returned != expected_cid:
        return False, f"node returned {returned}, expected {expected_cid}"
    return True, ""
