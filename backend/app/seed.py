"""Demo community. Runs once on an empty database when SEED_DEMO=true.

Every demo account uses the password `demo1234`. History is created through the same
exchange workflow the API uses, so balances, escrow and the receipt chain are consistent.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import ledger
from .config import settings
from .matching import normalize
from .models import Exchange, Rating, Skill, SkillKind, User
from .routers.exchanges import _transition, rating_record
from .security import hash_password

DEMO_PASSWORD = "demo1234"

# name, email, headline, location, bio, offers[(skill, category, level, rate, availability, description)], wants
MEMBERS = [
    ("Asha Rao", "asha@coinnect.dev", "Backend engineer who loves teaching Python", "Pune",
     "Six years building data pipelines. I teach the way I wish I'd been taught: small programs first.",
     [("Python programming", "Tech", "expert", 3, "Weekday evenings", "From first script to packaging a CLI."),
      ("SQL for analysts", "Tech", "advanced", 2, "Weekends", "Joins, window functions, reading query plans.")],
     ["Watercolour painting", "Spanish"]),
    ("Kabir Mehta", "kabir@coinnect.dev", "Product designer, Figma nerd", "Bengaluru",
     "Designing fintech apps by day. Happy to review your portfolio.",
     [("UI design in Figma", "Design", "expert", 3, "Weekday mornings", "Auto layout, components, handoff."),
      ("Portfolio reviews", "Design", "advanced", 2, "Flexible", "Honest 45-minute critiques.")],
     ["Python", "Public speaking"]),
    ("Lucía Fernández", "lucia@coinnect.dev", "Native Spanish speaker, language tutor", "Madrid",
     "I teach conversational Spanish with real-world topics, not textbook dialogues.",
     [("Spanish conversation", "Languages", "expert", 2, "Evenings CET", "Talk from minute one."),
      ("Flamenco guitar", "Music", "intermediate", 3, "Weekends", "Rumba and alegrías rhythms.")],
     ["Machine learning", "UI design"]),
    ("Daniel Okafor", "daniel@coinnect.dev", "ML engineer · ex-research", "Lagos",
     "I explain models with pen and paper before code.",
     [("Machine learning fundamentals", "Tech", "expert", 4, "Saturdays", "Regression to transformers, intuitively."),
      ("Statistics refresher", "Science", "advanced", 2, "Flexible", "Distributions, tests, confidence intervals.")],
     ["Flamenco guitar", "Cooking"]),
    ("Meera Iyer", "meera@coinnect.dev", "Watercolour artist and illustrator", "Chennai",
     "Loose botanical watercolours. Bring any paper, I'll bring the patience.",
     [("Watercolour painting", "Craft", "expert", 2, "Sunday afternoons", "Washes, wet-on-wet, botanical studies."),
      ("Hand lettering", "Design", "advanced", 2, "Flexible", "Brush pens and layout.")],
     ["SQL", "Yoga"]),
    ("Tomás Silva", "tomas@coinnect.dev", "Chef turned food writer", "Lisbon",
     "Home cooking that respects the ingredient.",
     [("Home cooking", "Wellness", "expert", 2, "Weekends", "Knife skills, stocks, weeknight dinners."),
      ("Sourdough baking", "Craft", "advanced", 2, "Mornings", "Starter care to open crumb.")],
     ["Statistics", "Portfolio review"]),
    ("Priya Nair", "priya@coinnect.dev", "Yoga instructor & physio student", "Kochi",
     "Gentle, alignment-focused practice for desk workers.",
     [("Yoga for desk workers", "Wellness", "advanced", 1, "Early mornings", "Mobility and breathing."),
      ("Public speaking", "Business", "intermediate", 2, "Flexible", "Structure a talk, calm the nerves.")],
     ["Hand lettering", "Sourdough"]),
    ("Arjun Kulkarni", "arjun@coinnect.dev", "Full-stack dev, React and TypeScript", "Mumbai",
     "Ship small, ship often. I pair-program rather than lecture.",
     [("React and TypeScript", "Tech", "expert", 3, "Weeknights", "Hooks, data fetching, testing."),
      ("Git workflows", "Tech", "advanced", 1, "Flexible", "Rebase without fear.")],
     ["Machine learning", "Home cooking"]),
]

# (provider email, learner email, skill, provider rating of learner, learner rating of provider, comment)
HISTORY = [
    ("asha@coinnect.dev", "kabir@coinnect.dev", "Python programming", 5, 5, "Clear, patient and practical."),
    ("kabir@coinnect.dev", "lucia@coinnect.dev", "UI design in Figma", 5, 5, "My first real prototype!"),
    ("lucia@coinnect.dev", "asha@coinnect.dev", "Spanish conversation", 4, 5, "Felt natural from the first call."),
    ("daniel@coinnect.dev", "arjun@coinnect.dev", "Machine learning fundamentals", 5, 5, "Finally understood backprop."),
    ("meera@coinnect.dev", "asha@coinnect.dev", "Watercolour painting", 5, 4, "Lovely session, very calm."),
    ("tomas@coinnect.dev", "daniel@coinnect.dev", "Home cooking", 4, 5, "Best risotto I've made."),
    ("priya@coinnect.dev", "kabir@coinnect.dev", "Public speaking", 5, 4, "Concrete tips I used the next day."),
    ("arjun@coinnect.dev", "meera@coinnect.dev", "Git workflows", 5, 5, "Rebasing no longer scares me."),
    ("daniel@coinnect.dev", "lucia@coinnect.dev", "Statistics refresher", 4, 4, "Good pace, good examples."),
]


def seed(db: Session) -> None:
    if db.scalar(select(func.count(User.id))):
        return
    ledger.ensure_genesis(db)
    pw = hash_password(DEMO_PASSWORD)
    users: dict[str, User] = {}
    skills: dict[str, Skill] = {}
    for name, email, headline, location, bio, offers, wants in MEMBERS:
        u = User(name=name, email=email, password_hash=pw, headline=headline, location=location, bio=bio,
                 balance=settings.starting_balance)
        db.add(u)
        users[email] = u
        db.flush()
        for skill, cat, level, rate, avail, desc in offers:
            s = Skill(user_id=u.id, name=skill, normalized=normalize(skill), kind=SkillKind.offer,
                      category=cat, level=level, rate=rate, availability=avail, description=desc)
            db.add(s)
            skills[skill] = s
        for want in wants:
            db.add(Skill(user_id=u.id, name=want, normalized=normalize(want), kind=SkillKind.request))
    db.commit()

    for prov, learn, skill_name, p_score, l_score, comment in HISTORY:
        provider, learner, skill = users[prov], users[learn], skills[skill_name]
        learner.balance -= skill.rate
        ex = Exchange(skill_id=skill.id, skill_name=skill.name, provider_id=provider.id, learner_id=learner.id,
                      amount=skill.rate, message="Looking forward to it!")
        db.add(ex)
        db.commit()
        _transition(db, ex, provider, "accept")
        _transition(db, ex, learner, "complete")
        for rater, ratee, score, text in ((learner, provider, l_score, comment), (provider, learner, p_score, "")):
            db.add(Rating(exchange_id=ex.id, rater_id=rater.id, ratee_id=ratee.id, score=score, comment=text))
            ledger.append(db, "rating", rating_record(ex, rater.id, score))
        db.commit()

    # One request still waiting, so the demo inbox isn't empty.
    lucia, asha = users["lucia@coinnect.dev"], users["asha@coinnect.dev"]
    skill = skills["Python programming"]
    lucia.balance -= skill.rate
    db.add(Exchange(skill_id=skill.id, skill_name=skill.name, provider_id=asha.id, learner_id=lucia.id,
                    amount=skill.rate, message="Could we start with pandas? I need it for a project."))
    db.commit()
