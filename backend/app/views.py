"""ORM → response conversion, batching the trust lookups."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Exchange, ExchangeStatus, Skill, User
from .reputation import trust_stats
from .schemas import ExchangeOut, MemberOut, MeOut, RatingOut, SkillOut


def member(user: User, trust: dict[int, dict]) -> MemberOut:
    t = trust.get(user.id) or {"trust": 4.0, "ratings": 0, "sessions_taught": 0}
    return MemberOut(id=user.id, name=user.name, headline=user.headline, location=user.location, **t)


def escrow_of(db: Session, user_id: int) -> int:
    return db.scalar(
        select(func.coalesce(func.sum(Exchange.amount), 0)).where(
            Exchange.learner_id == user_id,
            Exchange.status.in_([ExchangeStatus.pending, ExchangeStatus.accepted]),
        )
    ) or 0


def me(db: Session, user: User) -> MeOut:
    t = trust_stats(db, [user.id])
    base = member(user, t).model_dump()
    return MeOut(**base, email=user.email, bio=user.bio, balance=user.balance,
                 escrow=escrow_of(db, user.id), created_at=user.created_at)


def skills(db: Session, items: list[Skill]) -> list[SkillOut]:
    trust = trust_stats(db, list({s.user_id for s in items}))
    return [
        SkillOut(id=s.id, name=s.name, kind=s.kind, category=s.category, level=s.level,
                 description=s.description, rate=s.rate, availability=s.availability,
                 created_at=s.created_at, owner=member(s.user, trust))
        for s in items
    ]


def exchanges(db: Session, items: list[Exchange], viewer: User | None) -> list[ExchangeOut]:
    ids = {e.provider_id for e in items} | {e.learner_id for e in items}
    trust = trust_stats(db, list(ids))
    out = []
    for e in items:
        role = "observer"
        if viewer and viewer.id == e.provider_id:
            role = "provider"
        elif viewer and viewer.id == e.learner_id:
            role = "learner"
        out.append(ExchangeOut(
            id=e.id, skill_id=e.skill_id, skill_name=e.skill_name, amount=e.amount, message=e.message,
            status=e.status, receipt_cid=e.receipt_cid, created_at=e.created_at, updated_at=e.updated_at,
            completed_at=e.completed_at, provider=member(e.provider, trust), learner=member(e.learner, trust),
            role=role,
            ratings=[RatingOut(rater_id=r.rater_id, ratee_id=r.ratee_id, score=r.score, comment=r.comment)
                     for r in e.ratings],
        ))
    return out
