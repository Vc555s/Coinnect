"""Skill matching: fuzzy name similarity plus reciprocal ("swap") matches."""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import Skill, SkillKind, User

_STOP = {"and", "the", "of", "for", "to", "a", "an", "in", "with", "basics", "intro", "introduction"}
_ALIASES = {
    "js": "javascript", "ts": "typescript", "ml": "machine learning", "ai": "artificial intelligence",
    "ui": "user interface", "ux": "user experience", "py": "python", "dsa": "data structures algorithms",
}


def normalize(name: str) -> str:
    text = re.sub(r"[^a-z0-9+#]+", " ", name.lower()).strip()
    return " ".join(_ALIASES.get(t, t) for t in text.split())


def _tokens(norm: str) -> set[str]:
    return {t for t in norm.split() if t not in _STOP}


def similarity(a: str, b: str) -> float:
    """0..1. Token overlap catches 'Python' vs 'Python programming'; sequence ratio catches
    small spelling differences ('photoshop' vs 'photo shop')."""
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ta, tb = _tokens(na), _tokens(nb)
    overlap = len(ta & tb) / min(len(ta), len(tb)) if ta and tb else 0.0
    seq = SequenceMatcher(None, na, nb).ratio()
    return round(max(overlap * 0.9, seq), 3)


MATCH_THRESHOLD = 0.6


def matches_for(db: Session, user: User, trust: dict[int, dict]) -> dict:
    mine = db.scalars(select(Skill).where(Skill.user_id == user.id)).all()
    wants = [s for s in mine if s.kind == SkillKind.request]
    gives = [s for s in mine if s.kind == SkillKind.offer]

    others = db.scalars(
        select(Skill).where(Skill.user_id != user.id).options(selectinload(Skill.user))
    ).all()
    offers = [s for s in others if s.kind == SkillKind.offer]
    requests = [s for s in others if s.kind == SkillKind.request]

    by_want = []
    for want in wants:
        hits = []
        for offer in offers:
            score = similarity(want.name, offer.name)
            if score >= MATCH_THRESHOLD:
                hits.append((score, offer))
        hits.sort(key=lambda h: (h[0], trust.get(h[1].user_id, {}).get("trust", 0)), reverse=True)
        by_want.append({"want": want, "offers": [(round(s, 2), o) for s, o in hits[:6]]})

    # Reciprocal: they offer something I want AND want something I offer.
    swaps = []
    seen = set()
    for want in wants:
        for offer in offers:
            s1 = similarity(want.name, offer.name)
            if s1 < MATCH_THRESHOLD:
                continue
            for theirs in requests:
                if theirs.user_id != offer.user_id:
                    continue
                for give in gives:
                    s2 = similarity(theirs.name, give.name)
                    key = (offer.id, give.id)
                    if s2 >= MATCH_THRESHOLD and key not in seen:
                        seen.add(key)
                        swaps.append({"score": round((s1 + s2) / 2, 2), "you_get": offer, "you_give": give,
                                      "their_request": theirs})
    swaps.sort(key=lambda s: s["score"], reverse=True)
    return {"by_want": by_want, "swaps": swaps[:12], "has_wants": bool(wants), "has_offers": bool(gives)}
