"""Append-only, hash-chained receipt ledger.

Each entry embeds the CID of the previous one, so changing any historical record changes
its CID and breaks every link after it. `verify_chain` walks the whole chain and reports
the first inconsistency.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import ipfs
from .cid import canonical_json, cid_for_bytes
from .models import LedgerEntry, utcnow

SCHEMA = "coinnect/receipt@1"


def head(db: Session) -> LedgerEntry | None:
    return db.scalar(select(LedgerEntry).order_by(LedgerEntry.seq.desc()).limit(1))


def append(db: Session, kind: str, data: dict[str, Any]) -> LedgerEntry:
    """Add an entry inside the caller's transaction (committed together with the change
    it records)."""
    last = head(db)
    seq = (last.seq + 1) if last else 1
    now = utcnow()
    record = {
        "schema": SCHEMA,
        "seq": seq,
        "kind": kind,
        "prev": last.cid if last else None,
        "timestamp": now.isoformat(timespec="seconds"),
        "data": data,
    }
    raw = canonical_json(record)
    entry = LedgerEntry(
        seq=seq,
        cid=cid_for_bytes(raw),
        prev_cid=record["prev"],
        kind=kind,
        raw=raw.decode("utf-8"),
        created_at=now,
    )
    entry.pinned, entry.pin_error = ipfs.pin(raw, entry.cid)
    db.add(entry)
    db.flush()
    return entry


def ensure_genesis(db: Session) -> None:
    if head(db) is None:
        append(db, "genesis", {"network": "coinnect", "note": "SkillCoin ledger initialised"})
        db.commit()


def verify_entry(entry: LedgerEntry) -> dict[str, Any]:
    raw = entry.raw.encode("utf-8")
    recomputed = cid_for_bytes(raw)
    try:
        record = json.loads(raw)
        canonical = canonical_json(record) == raw
        prev_ok = record.get("prev") == entry.prev_cid and record.get("seq") == entry.seq
    except ValueError:
        canonical, prev_ok = False, False
    return {
        "cid": entry.cid,
        "recomputed_cid": recomputed,
        "hash_matches": recomputed == entry.cid,
        "canonical": canonical,
        "header_matches": prev_ok,
        "valid": recomputed == entry.cid and canonical and prev_ok,
    }


def verify_chain(db: Session) -> dict[str, Any]:
    entries = db.scalars(select(LedgerEntry).order_by(LedgerEntry.seq)).all()
    expected_prev: str | None = None
    for position, entry in enumerate(entries, start=1):
        check = verify_entry(entry)
        problem = None
        if entry.seq != position:
            problem = f"sequence gap: expected {position}, found {entry.seq}"
        elif not check["valid"]:
            problem = "content does not match its CID"
        elif entry.prev_cid != expected_prev:
            problem = "broken link to the previous entry"
        if problem:
            return {"valid": False, "length": len(entries), "checked": position, "broken_at": entry.cid, "problem": problem}
        expected_prev = entry.cid
    return {
        "valid": True,
        "length": len(entries),
        "checked": len(entries),
        "head": expected_prev,
        "broken_at": None,
        "problem": None,
    }
