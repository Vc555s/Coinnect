from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import ipfs, ledger
from ..config import settings
from ..db import get_db
from ..models import Exchange, ExchangeStatus, LedgerEntry, Rating, Skill, SkillKind, User
from ..reputation import integrity_signals
from ..schemas import as_utc

router = APIRouter(prefix="/api", tags=["ledger"])


def _entry(e: LedgerEntry) -> dict:
    return {
        "seq": e.seq,
        "cid": e.cid,
        "prev_cid": e.prev_cid,
        "kind": e.kind,
        "created_at": as_utc(e.created_at),
        "record": json.loads(e.raw),
        "pinned": e.pinned,
        "pin_error": e.pin_error or None,
        "gateway_url": f"{settings.ipfs_gateway}{e.cid}" if e.pinned else None,
    }


@router.get("/ledger")
def list_ledger(
    before: int | None = None, limit: int = Query(25, le=100), kind: str | None = None, db: Session = Depends(get_db)
):
    stmt = select(LedgerEntry).order_by(LedgerEntry.seq.desc()).limit(limit)
    if before:
        stmt = stmt.where(LedgerEntry.seq < before)
    if kind:
        stmt = stmt.where(LedgerEntry.kind == kind)
    entries = db.scalars(stmt).all()
    total = db.scalar(select(func.count(LedgerEntry.seq)))
    return {"total": total, "entries": [_entry(e) for e in entries], "ipfs_pinning": ipfs.enabled()}


@router.get("/ledger/verify")
def verify_whole_chain(db: Session = Depends(get_db)):
    return ledger.verify_chain(db)


def _by_cid(db: Session, cid: str) -> LedgerEntry:
    entry = db.scalar(select(LedgerEntry).where(LedgerEntry.cid == cid))
    if not entry:
        raise HTTPException(404, "No receipt with that CID on this ledger")
    return entry


@router.get("/ledger/{cid}")
def get_entry(cid: str, db: Session = Depends(get_db)):
    entry = _by_cid(db, cid)
    nxt = db.scalar(select(LedgerEntry.cid).where(LedgerEntry.prev_cid == cid))
    return {**_entry(entry), "next_cid": nxt, "verification": ledger.verify_entry(entry)}


@router.get("/ledger/{cid}/raw")
def get_raw(cid: str, db: Session = Depends(get_db)):
    """The exact bytes that were hashed — fetch these to verify the CID yourself."""
    return Response(_by_cid(db, cid).raw.encode("utf-8"), media_type="application/json")


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    def top(kind: SkillKind):
        rows = db.execute(
            select(Skill.name, func.count(Skill.id).label("n"))
            .where(Skill.kind == kind).group_by(Skill.normalized).order_by(func.count(Skill.id).desc()).limit(6)
        ).all()
        return [{"name": n, "count": c} for n, c in rows]

    completed = select(Exchange).where(Exchange.status == ExchangeStatus.completed)
    by_cat = db.execute(
        select(Skill.category, func.count(Skill.id)).where(Skill.kind == SkillKind.offer).group_by(Skill.category)
    ).all()
    return {
        "members": db.scalar(select(func.count(User.id))),
        "offers": db.scalar(select(func.count(Skill.id)).where(Skill.kind == SkillKind.offer)),
        "requests": db.scalar(select(func.count(Skill.id)).where(Skill.kind == SkillKind.request)),
        "sessions": db.scalar(select(func.count()).select_from(completed.subquery())),
        "coins_circulated": db.scalar(
            select(func.coalesce(func.sum(Exchange.amount), 0)).where(Exchange.status == ExchangeStatus.completed)
        ),
        "average_rating": round(db.scalar(select(func.avg(Rating.score))) or 0, 2),
        "receipts": db.scalar(select(func.count(LedgerEntry.seq))),
        "top_offered": top(SkillKind.offer),
        "top_wanted": top(SkillKind.request),
        "categories": [{"name": c, "count": n} for c, n in sorted(by_cat, key=lambda r: -r[1])],
    }


@router.get("/integrity")
def integrity(db: Session = Depends(get_db)):
    return {"signals": integrity_signals(db)}
