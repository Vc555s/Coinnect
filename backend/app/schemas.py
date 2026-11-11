from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator

from .models import ExchangeStatus, SkillKind

def as_utc(value: datetime) -> str:
    """SQLite drops tzinfo; every timestamp we store is UTC, so say so on the way out."""
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()


UTC = Annotated[datetime, PlainSerializer(as_utc)]

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

CATEGORIES = ("Tech", "Design", "Languages", "Music", "Business", "Science", "Craft", "Wellness", "Other")
LEVELS = ("beginner", "intermediate", "advanced", "expert")


class _In(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class RegisterIn(_In):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)
    headline: str = Field("", max_length=140)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        if not _EMAIL.match(v):
            raise ValueError("Enter a valid email address")
        return v.lower()


class LoginIn(_In):
    email: str
    password: str


class ProfileIn(_In):
    name: str | None = Field(None, min_length=2, max_length=80)
    headline: str | None = Field(None, max_length=140)
    bio: str | None = Field(None, max_length=2000)
    location: str | None = Field(None, max_length=80)


class SkillIn(_In):
    name: str = Field(min_length=2, max_length=80)
    kind: SkillKind
    category: Literal[CATEGORIES] = "Other"  # type: ignore[valid-type]
    level: Literal[LEVELS] = "intermediate"  # type: ignore[valid-type]
    description: str = Field("", max_length=1000)
    rate: int = Field(2, ge=1, le=50)
    availability: str = Field("Flexible", max_length=80)


class SkillPatch(_In):
    name: str | None = Field(None, min_length=2, max_length=80)
    category: Literal[CATEGORIES] | None = None  # type: ignore[valid-type]
    level: Literal[LEVELS] | None = None  # type: ignore[valid-type]
    description: str | None = Field(None, max_length=1000)
    rate: int | None = Field(None, ge=1, le=50)
    availability: str | None = Field(None, max_length=80)


class ExchangeIn(_In):
    skill_id: int
    message: str = Field("", max_length=1000)


class RatingIn(_In):
    score: int = Field(ge=1, le=5)
    comment: str = Field("", max_length=500)


# ---------------------------------------------------------------- outputs

class MemberOut(BaseModel):
    id: int
    name: str
    headline: str
    location: str
    trust: float
    ratings: int
    sessions_taught: int


class MeOut(MemberOut):
    email: str
    bio: str
    balance: int
    escrow: int
    created_at: UTC


class SkillOut(BaseModel):
    id: int
    name: str
    kind: SkillKind
    category: str
    level: str
    description: str
    rate: int
    availability: str
    created_at: UTC
    owner: MemberOut


class RatingOut(BaseModel):
    rater_id: int
    ratee_id: int
    score: int
    comment: str


class ExchangeOut(BaseModel):
    id: int
    skill_id: int | None
    skill_name: str
    amount: int
    message: str
    status: ExchangeStatus
    receipt_cid: str | None
    created_at: UTC
    updated_at: UTC
    completed_at: UTC | None
    provider: MemberOut
    learner: MemberOut
    role: Literal["provider", "learner", "observer"]
    ratings: list[RatingOut]


class AuthOut(BaseModel):
    token: str
    user: MeOut
