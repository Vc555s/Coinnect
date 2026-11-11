from app import ledger
from app.db import SessionLocal
from app.models import LedgerEntry


def test_health_and_seed(client):
    assert client.get("/api/health").json()["status"] == "ok"
    stats = client.get("/api/stats").json()
    assert stats["members"] == 8 and stats["sessions"] == 9
    assert client.get("/api/ledger/verify").json()["valid"] is True


def test_register_login_and_duplicate(client):
    body = {"name": "Test User", "email": "Test@Example.com", "password": "longenough"}
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 201
    assert r.json()["user"]["balance"] == 10 and r.json()["user"]["email"] == "test@example.com"
    assert client.post("/api/auth/register", json=body).status_code == 409
    assert client.post("/api/auth/login", json={"email": "test@example.com", "password": "wrong"}).status_code == 401
    assert client.get("/api/me").status_code == 401


def test_full_exchange_lifecycle_with_escrow(client, auth):
    learner = auth("priya@coinnect.dev")
    teacher = auth("arjun@coinnect.dev")
    offer = next(s for s in client.get("/api/skills?q=react").json() if s["owner"]["name"] == "Arjun Kulkarni")
    before_l = client.get("/api/me", headers=learner).json()
    before_t = client.get("/api/me", headers=teacher).json()

    ex = client.post("/api/exchanges", json={"skill_id": offer["id"], "message": "hi"}, headers=learner).json()
    assert ex["status"] == "pending" and ex["role"] == "learner"
    mid = client.get("/api/me", headers=learner).json()
    assert mid["balance"] == before_l["balance"] - offer["rate"] and mid["escrow"] == before_l["escrow"] + offer["rate"]

    # only the teacher may accept, only the learner may complete
    assert client.post(f"/api/exchanges/{ex['id']}/accept", headers=learner).status_code == 403
    assert client.post(f"/api/exchanges/{ex['id']}/complete", headers=learner).status_code == 409
    assert client.post(f"/api/exchanges/{ex['id']}/accept", headers=teacher).json()["status"] == "accepted"
    done = client.post(f"/api/exchanges/{ex['id']}/complete", headers=learner).json()
    assert done["status"] == "completed" and done["receipt_cid"].startswith("bafkrei")
    assert client.get("/api/me", headers=teacher).json()["balance"] == before_t["balance"] + offer["rate"]

    receipt = client.get(f"/api/ledger/{done['receipt_cid']}").json()
    assert receipt["verification"]["valid"] and receipt["record"]["data"]["exchange_id"] == ex["id"]

    rated = client.post(f"/api/exchanges/{ex['id']}/rate", json={"score": 5, "comment": "great"}, headers=learner)
    assert rated.status_code == 200
    assert client.post(f"/api/exchanges/{ex['id']}/rate", json={"score": 5}, headers=learner).status_code == 409
    assert client.get("/api/ledger/verify").json()["valid"] is True


def test_cancel_refunds_escrow(client, auth):
    learner = auth("tomas@coinnect.dev")
    offer = client.get("/api/skills?q=git").json()[0]
    start = client.get("/api/me", headers=learner).json()["balance"]
    ex = client.post("/api/exchanges", json={"skill_id": offer["id"]}, headers=learner).json()
    assert client.post("/api/exchanges", json={"skill_id": offer["id"]}, headers=learner).status_code == 409
    client.post(f"/api/exchanges/{ex['id']}/cancel", headers=learner)
    me = client.get("/api/me", headers=learner).json()
    assert me["balance"] == start and me["escrow"] == 0


def test_insufficient_balance(client, auth):
    h = client.post("/api/auth/register", json={"name": "Broke", "email": "broke@x.io", "password": "password1"})
    headers = {"Authorization": f"Bearer {h.json()['token']}"}
    pricey = client.get("/api/skills?q=machine learning").json()[0]  # 4 coins
    for _ in range(2):
        client.post("/api/exchanges", json={"skill_id": pricey["id"]}, headers=headers)
    others = [s for s in client.get("/api/skills?sort=rate").json() if s["rate"] >= 3]
    statuses = {client.post("/api/exchanges", json={"skill_id": s["id"]}, headers=headers).status_code for s in others}
    assert 402 in statuses


def test_skill_crud_and_ownership(client, auth):
    me = auth("meera@coinnect.dev")
    other = auth("asha@coinnect.dev")
    s = client.post("/api/skills", json={"name": "Gouache basics", "kind": "offer", "category": "Craft", "rate": 2},
                    headers=me).json()
    assert client.post("/api/skills", json={"name": "gouache  basics", "kind": "offer"}, headers=me).status_code == 409
    assert client.patch(f"/api/skills/{s['id']}", json={"rate": 3}, headers=other).status_code == 403
    assert client.patch(f"/api/skills/{s['id']}", json={"rate": 3}, headers=me).json()["rate"] == 3
    assert client.delete(f"/api/skills/{s['id']}", headers=me).status_code == 204


def test_matches_find_fuzzy_and_swaps(client, auth):
    m = client.get("/api/matches", headers=auth("lucia@coinnect.dev")).json()
    wanted = {g["want"]["name"]: [o["skill"]["name"] for o in g["offers"]] for g in m["by_want"]}
    assert "Machine learning fundamentals" in wanted["Machine learning"]
    assert any(s["you_get"]["owner"]["name"] == "Daniel Okafor" for s in m["swaps"])


def test_tampering_is_detected(client):
    with SessionLocal() as db:
        entry = db.query(LedgerEntry).filter(LedgerEntry.kind == "exchange").first()
        original = entry.raw
        entry.raw = original.replace('"amount":', '"amount":1', 1)
        db.commit()
        try:
            result = ledger.verify_chain(db)
            assert result["valid"] is False and result["broken_at"] == entry.cid
        finally:
            entry.raw = original
            db.commit()
    assert client.get("/api/ledger/verify").json()["valid"] is True
