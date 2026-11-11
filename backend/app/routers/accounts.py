from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import views
from ..config import settings
from ..db import get_db
from ..models import Exchange, ExchangeStatus, Skill, User
from ..reputation import trust_stats
from ..schemas import as_utc, AuthOut, LoginIn, MeOut, ProfileIn, RegisterIn
from ..security import create_token, current_user, hash_password, verify_password

router = APIRouter(prefix="/api", tags=["accounts"])


@router.post("/auth/register", response_model=AuthOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(name=body.name, email=body.email, password_hash=hash_password(body.password),
                headline=body.headline, balance=settings.starting_balance)
    db.add(user)
    db.commit()
    return AuthOut(token=create_token(user.id), user=views.me(db, user))


@router.post("/auth/login", response_model=AuthOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")
    return AuthOut(token=create_token(user.id), user=views.me(db, user))


@router.get("/me", response_model=MeOut)
def read_me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return views.me(db, user)


@router.patch("/me", response_model=MeOut)
def update_me(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    return views.me(db, user)


@router.get("/members")
def list_members(db: Session = Depends(get_db)):
    users = db.scalars(select(User)).all()
    trust = trust_stats(db, [u.id for u in users])
    ranked = sorted((views.member(u, trust) for u in users), key=lambda m: (m.trust, m.sessions_taught), reverse=True)
    return ranked


@router.get("/members/{user_id}")
def member_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Member not found")
    trust = trust_stats(db, [user.id])
    skills = db.scalars(
        select(Skill).where(Skill.user_id == user.id).options(selectinload(Skill.user)).order_by(Skill.created_at)
    ).all()
    done = db.scalars(
        select(Exchange)
        .where(Exchange.status == ExchangeStatus.completed,
               (Exchange.provider_id == user.id) | (Exchange.learner_id == user.id))
        .options(selectinload(Exchange.ratings), selectinload(Exchange.provider), selectinload(Exchange.learner))
        .order_by(Exchange.completed_at.desc())
        .limit(20)
    ).all()
    reviews = [
        {"score": r.score, "comment": r.comment, "skill": e.skill_name,
         "from": (e.learner if r.rater_id == e.learner_id else e.provider).name, "date": as_utc(r.created_at)}
        for e in done for r in e.ratings if r.ratee_id == user.id
    ]
    return {
        "member": views.member(user, trust),
        "bio": user.bio,
        "joined": as_utc(user.created_at),
        "skills": views.skills(db, list(skills)),
        "reviews": reviews,
        "history": views.exchanges(db, list(done), None),
    }
