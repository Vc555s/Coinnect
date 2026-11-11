from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SkillKind(str, enum.Enum):
    offer = "offer"      # "I can teach this"
    request = "request"  # "I want to learn this"


class ExchangeStatus(str, enum.Enum):
    pending = "pending"      # learner asked, coins held in escrow
    accepted = "accepted"    # provider agreed to run the session
    completed = "completed"  # learner confirmed, coins released to provider
    declined = "declined"    # provider said no, coins refunded
    cancelled = "cancelled"  # learner withdrew, coins refunded


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    headline: Mapped[str] = mapped_column(String(140), default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(80), default="")
    balance: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    skills: Mapped[list[Skill]] = relationship(back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (CheckConstraint("balance >= 0", name="balance_non_negative"),)


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    normalized: Mapped[str] = mapped_column(String(80), index=True)
    kind: Mapped[SkillKind] = mapped_column(Enum(SkillKind), index=True)
    category: Mapped[str] = mapped_column(String(40), default="Other")
    level: Mapped[str] = mapped_column(String(20), default="intermediate")
    description: Mapped[str] = mapped_column(Text, default="")
    rate: Mapped[int] = mapped_column(Integer, default=2)  # coins per session (offers only)
    availability: Mapped[str] = mapped_column(String(80), default="Flexible")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="skills")


class Exchange(Base):
    __tablename__ = "exchanges"

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id", ondelete="SET NULL"))
    skill_name: Mapped[str] = mapped_column(String(80))  # snapshot, survives skill deletion
    provider_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    learner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[ExchangeStatus] = mapped_column(
        Enum(ExchangeStatus), default=ExchangeStatus.pending, index=True
    )
    receipt_cid: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    provider: Mapped[User] = relationship(foreign_keys=[provider_id])
    learner: Mapped[User] = relationship(foreign_keys=[learner_id])
    ratings: Mapped[list[Rating]] = relationship(back_populates="exchange")

    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)


class Rating(Base):
    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(primary_key=True)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id"), index=True)
    rater_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    ratee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    score: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    exchange: Mapped[Exchange] = relationship(back_populates="ratings")

    __table_args__ = (
        UniqueConstraint("exchange_id", "rater_id", name="one_rating_per_party"),
        CheckConstraint("score BETWEEN 1 AND 5", name="score_range"),
    )


class LedgerEntry(Base):
    """One block of the append-only receipt chain. `cid` is the IPFS CIDv1 of `raw`."""

    __tablename__ = "ledger"

    seq: Mapped[int] = mapped_column(primary_key=True)
    cid: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    prev_cid: Mapped[str | None] = mapped_column(String(80), nullable=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    raw: Mapped[str] = mapped_column(Text)  # canonical JSON exactly as hashed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    pinned: Mapped[bool] = mapped_column(default=False)
    pin_error: Mapped[str] = mapped_column(Text, default="")
