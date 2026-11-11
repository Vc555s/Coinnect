"""Exchange lifecycle with escrow.

    learner requests ──► pending ──(provider accepts)──► accepted ──(learner confirms)──► completed
                            │                                │
                            ├─(provider declines)─► declined │
                            └─(learner cancels)──► cancelled ◄┘

Coins leave the learner's balance at request time and are held until the exchange either
completes (paid to the provider) or ends early (refunded). Completion and every rating are
written to the receipt ledger in the same database transaction.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import ledger, views
from ..db import get_db
from ..models import Exchange, ExchangeStatus, Rating, Skill, SkillKind, User, utcnow
from ..schemas import ExchangeIn, ExchangeOut, RatingIn
from ..security import current_user

router = APIRouter(prefix="/api/exchanges", tags=["exchanges"])


def rating_record(ex: Exchange, rater_id: int, score: int) -> dict:
    people = {ex.provider_id: ex.provider, ex.learner_id: ex.learner}
    ratee_id = ex.learner_id if rater_id == ex.provider_id else ex.provider_id
    return {
        "exchange_id": ex.id,
        "receipt": ex.receipt_cid,
        "skill": ex.skill_name,
        "rater": {"id": rater_id, "name": people[rater_id].name},
        "ratee": {"id": ratee_id, "name": people[ratee_id].name},
        "score": score,
    }

OPEN = (ExchangeStatus.pending, ExchangeStatus.accepted)


def _load(db: Session, exchange_id: int) -> Exchange:
    ex = db.scalar(
        select(Exchange).where(Exchange.id == exchange_id).options(
            selectinload(Exchange.provider), selectinload(Exchange.learner), selectinload(Exchange.ratings)
        )
    )
    if not ex:
        raise HTTPException(404, "Exchange not found")
    return ex


def _out(db: Session, ex: Exchange, user: User) -> ExchangeOut:
    db.refresh(ex)
    return views.exchanges(db, [ex], user)[0]


@router.get("", response_model=list[ExchangeOut])
def my_exchanges(
    box: Literal["all", "incoming", "outgoing"] = "all",
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Exchange).options(
        selectinload(Exchange.provider), selectinload(Exchange.learner), selectinload(Exchange.ratings)
    )
    if box == "incoming":
        stmt = stmt.where(Exchange.provider_id == user.id)
    elif box == "outgoing":
        stmt = stmt.where(Exchange.learner_id == user.id)
    else:
        stmt = stmt.where((Exchange.provider_id == user.id) | (Exchange.learner_id == user.id))
    return views.exchanges(db, list(db.scalars(stmt.order_by(Exchange.updated_at.desc()))), user)


@router.get("/{exchange_id}", response_model=ExchangeOut)
def get_exchange(exchange_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ex = _load(db, exchange_id)
    if user.id not in (ex.provider_id, ex.learner_id) and ex.status != ExchangeStatus.completed:
        raise HTTPException(403, "Only the two members can see an open exchange")
    return views.exchanges(db, [ex], user)[0]


@router.post("", response_model=ExchangeOut, status_code=201)
def request_exchange(body: ExchangeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    skill = db.get(Skill, body.skill_id)
    if not skill or skill.kind != SkillKind.offer:
        raise HTTPException(404, "That skill is not on offer")
    if skill.user_id == user.id:
        raise HTTPException(400, "You can't book your own session")
    duplicate = db.scalar(select(Exchange).where(
        Exchange.skill_id == skill.id, Exchange.learner_id == user.id, Exchange.status.in_(OPEN)))
    if duplicate:
        raise HTTPException(409, "You already have an open request for this skill")
    if user.balance < skill.rate:
        raise HTTPException(402, f"This session costs {skill.rate} coins; you have {user.balance}")

    user.balance -= skill.rate  # into escrow
    ex = Exchange(skill_id=skill.id, skill_name=skill.name, provider_id=skill.user_id, learner_id=user.id,
                  amount=skill.rate, message=body.message)
    db.add(ex)
    db.commit()
    return _out(db, _load(db, ex.id), user)


def _transition(db: Session, ex: Exchange, actor: User, action: str) -> None:
    is_provider, is_learner = actor.id == ex.provider_id, actor.id == ex.learner_id
    rules = {
        "accept": (is_provider, (ExchangeStatus.pending,), ExchangeStatus.accepted),
        "decline": (is_provider, (ExchangeStatus.pending,), ExchangeStatus.declined),
        "cancel": (is_learner, OPEN, ExchangeStatus.cancelled),
        "complete": (is_learner, (ExchangeStatus.accepted,), ExchangeStatus.completed),
    }
    allowed, from_states, to_state = rules[action]
    if not allowed:
        who = "teacher" if action in ("accept", "decline") else "learner"
        raise HTTPException(403, f"Only the {who} can {action} this exchange")
    if ex.status not in from_states:
        raise HTTPException(409, f"Can't {action} an exchange that is {ex.status.value}")

    now = utcnow()
    if to_state in (ExchangeStatus.declined, ExchangeStatus.cancelled):
        ex.learner.balance += ex.amount  # refund escrow
    elif to_state == ExchangeStatus.completed:
        ex.provider.balance += ex.amount  # release escrow
        ex.completed_at = now
        entry = ledger.append(db, "exchange", {
            "exchange_id": ex.id,
            "skill": ex.skill_name,
            "amount": ex.amount,
            "unit": "SkillCoin",
            "provider": {"id": ex.provider_id, "name": ex.provider.name},
            "learner": {"id": ex.learner_id, "name": ex.learner.name},
            "requested_at": ex.created_at.isoformat(timespec="seconds"),
            "completed_at": now.isoformat(timespec="seconds"),
        })
        ex.receipt_cid = entry.cid
    ex.status = to_state
    ex.updated_at = now
    db.commit()


@router.post("/{exchange_id}/rate", response_model=ExchangeOut)
def rate(exchange_id: int, body: RatingIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ex = _load(db, exchange_id)
    if user.id not in (ex.provider_id, ex.learner_id):
        raise HTTPException(403, "Only the two members can rate this exchange")
    if ex.status != ExchangeStatus.completed:
        raise HTTPException(409, "You can rate an exchange once it is completed")
    if any(r.rater_id == user.id for r in ex.ratings):
        raise HTTPException(409, "You already rated this exchange")
    ratee = ex.learner_id if user.id == ex.provider_id else ex.provider_id
    db.add(Rating(exchange_id=ex.id, rater_id=user.id, ratee_id=ratee, score=body.score, comment=body.comment))
    ledger.append(db, "rating", rating_record(ex, user.id, body.score))
    db.commit()
    return _out(db, _load(db, ex.id), user)


# Declared last so the literal /rate route above takes precedence.
@router.post("/{exchange_id}/{action}", response_model=ExchangeOut)
def act(
    exchange_id: int,
    action: Literal["accept", "decline", "cancel", "complete"],
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    ex = _load(db, exchange_id)
    _transition(db, ex, user, action)
    return _out(db, ex, user)
