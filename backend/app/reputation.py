"""Trust scores and integrity signals."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Exchange, ExchangeStatus, Rating, Skill, SkillKind, User, utcnow

# Bayesian average: every member starts as if they had PRIOR_WEIGHT ratings of PRIOR_MEAN.
# A newcomer with one 5-star rating does not outrank someone with forty 4.8s.
PRIOR_MEAN = 4.0
PRIOR_WEIGHT = 3


def trust_stats(db: Session, user_ids: list[int] | None = None) -> dict[int, dict]:
    q = select(Rating.ratee_id, func.count(Rating.id), func.coalesce(func.sum(Rating.score), 0)).group_by(
        Rating.ratee_id
    )
    if user_ids is not None:
        q = q.where(Rating.ratee_id.in_(user_ids))
    ratings = {uid: (n, total) for uid, n, total in db.execute(q)}

    cq = (
        select(Exchange.provider_id, func.count(Exchange.id))
        .where(Exchange.status == ExchangeStatus.completed)
        .group_by(Exchange.provider_id)
    )
    if user_ids is not None:
        cq = cq.where(Exchange.provider_id.in_(user_ids))
    taught = dict(db.execute(cq).all())

    ids = user_ids if user_ids is not None else list(set(ratings) | set(taught))
    out = {}
    for uid in ids:
        n, total = ratings.get(uid, (0, 0))
        score = (PRIOR_MEAN * PRIOR_WEIGHT + total) / (PRIOR_WEIGHT + n)
        out[uid] = {"trust": round(score, 2), "ratings": n, "sessions_taught": taught.get(uid, 0)}
    return out


def integrity_signals(db: Session) -> list[dict]:
    """Heuristic flags for a moderator to review. They are prompts, not verdicts."""
    signals: list[dict] = []
    users = {u.id: u for u in db.scalars(select(User))}
    stats = trust_stats(db, list(users))

    offers = Counter(db.scalars(select(Skill.user_id).where(Skill.kind == SkillKind.offer)))
    for uid, n in offers.items():
        if n >= 6 and stats[uid]["sessions_taught"] == 0:
            signals.append({
                "user_id": uid, "name": users[uid].name, "severity": "medium",
                "signal": "Unproven breadth",
                "detail": f"Offers {n} skills but has not completed a single session.",
            })

    recent = utcnow() - timedelta(hours=1)
    burst = Counter(
        db.scalars(select(Skill.user_id).where(Skill.created_at >= recent, Skill.kind == SkillKind.offer))
    )
    for uid, n in burst.items():
        if n >= 5:
            signals.append({
                "user_id": uid, "name": users[uid].name, "severity": "low",
                "signal": "Listing burst", "detail": f"Added {n} offers within the last hour.",
            })

    for uid, s in stats.items():
        if s["ratings"] >= 3 and s["trust"] < 3.0:
            signals.append({
                "user_id": uid, "name": users[uid].name, "severity": "high",
                "signal": "Low trust", "detail": f"Trust {s['trust']} across {s['ratings']} ratings.",
            })

    # Pairs that keep rating each other 5/5 and rarely anyone else: possible collusion.
    pair_fives: dict[tuple[int, int], int] = defaultdict(int)
    for rater, ratee, score in db.execute(select(Rating.rater_id, Rating.ratee_id, Rating.score)):
        if score == 5:
            pair_fives[tuple(sorted((rater, ratee)))] += 1
    for (a, b), n in pair_fives.items():
        if n >= 4:
            signals.append({
                "user_id": a, "name": f"{users[a].name} ↔ {users[b].name}", "severity": "medium",
                "signal": "Reciprocal 5-star loop",
                "detail": f"{n} perfect ratings exchanged only between these two members.",
            })
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(signals, key=lambda s: order[s["severity"]])
