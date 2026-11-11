from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import views
from ..db import get_db
from ..matching import matches_for, normalize, similarity
from ..models import Skill, SkillKind, User
from ..reputation import trust_stats
from ..schemas import CATEGORIES, SkillIn, SkillOut, SkillPatch
from ..security import current_user, optional_user

router = APIRouter(prefix="/api", tags=["skills"])


@router.get("/skills", response_model=list[SkillOut])
def search_skills(
    q: str = "",
    kind: SkillKind = SkillKind.offer,
    category: str | None = None,
    sort: Literal["relevance", "trust", "rate", "newest"] = "relevance",
    limit: int = Query(60, le=200),
    viewer: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
):
    stmt = select(Skill).where(Skill.kind == kind).options(selectinload(Skill.user))
    if category and category != "All":
        stmt = stmt.where(Skill.category == category)
    items = list(db.scalars(stmt).all())

    scores: dict[int, float] = {}
    if q.strip():
        needle = normalize(q)
        for s in items:
            # substring hits rank above fuzzy ones
            scores[s.id] = 1.0 if needle in s.normalized else similarity(q, s.name)
        items = [s for s in items if scores[s.id] >= 0.5]

    trust = trust_stats(db, list({s.user_id for s in items}))
    t = lambda s: trust.get(s.user_id, {}).get("trust", 0)  # noqa: E731
    if sort == "trust" or (sort == "relevance" and not q.strip()):
        items.sort(key=lambda s: (t(s), s.created_at), reverse=True)
    elif sort == "relevance":
        items.sort(key=lambda s: (scores[s.id], t(s)), reverse=True)
    elif sort == "rate":
        items.sort(key=lambda s: (s.rate, -t(s)))
    else:
        items.sort(key=lambda s: s.created_at, reverse=True)
    return views.skills(db, items[:limit])


@router.get("/skills/categories")
def categories():
    return list(CATEGORIES)


@router.get("/me/skills", response_model=list[SkillOut])
def my_skills(user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(Skill).where(Skill.user_id == user.id).order_by(Skill.created_at.desc())).all()
    return views.skills(db, list(items))


@router.post("/skills", response_model=SkillOut, status_code=201)
def add_skill(body: SkillIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    norm = normalize(body.name)
    clash = db.scalar(select(Skill).where(Skill.user_id == user.id, Skill.kind == body.kind, Skill.normalized == norm))
    if clash:
        raise HTTPException(409, f"You already list “{clash.name}”")
    skill = Skill(user_id=user.id, normalized=norm, **body.model_dump())
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return views.skills(db, [skill])[0]


def _own(db: Session, skill_id: int, user: User) -> Skill:
    skill = db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")
    if skill.user_id != user.id:
        raise HTTPException(403, "You can only change your own skills")
    return skill


@router.patch("/skills/{skill_id}", response_model=SkillOut)
def edit_skill(skill_id: int, body: SkillPatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    skill = _own(db, skill_id, user)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(skill, field, value)
    if body.name:
        skill.normalized = normalize(body.name)
    db.commit()
    return views.skills(db, [skill])[0]


@router.delete("/skills/{skill_id}", status_code=204)
def delete_skill(skill_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(_own(db, skill_id, user))
    db.commit()


@router.get("/matches")
def my_matches(user: User = Depends(current_user), db: Session = Depends(get_db)):
    trust = trust_stats(db)
    raw = matches_for(db, user, trust)
    to_out = lambda s: views.skills(db, [s])[0]  # noqa: E731
    return {
        "has_wants": raw["has_wants"],
        "has_offers": raw["has_offers"],
        "by_want": [
            {"want": to_out(g["want"]), "offers": [{"score": sc, "skill": to_out(o)} for sc, o in g["offers"]]}
            for g in raw["by_want"]
        ],
        "swaps": [
            {"score": s["score"], "you_get": to_out(s["you_get"]), "you_give": to_out(s["you_give"]),
             "their_request": to_out(s["their_request"])}
            for s in raw["swaps"]
        ],
    }
