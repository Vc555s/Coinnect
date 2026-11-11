import os
import sys
import tempfile
from pathlib import Path

import pytest

# Isolated database per test session; configure before the app is imported.
_tmp = tempfile.mkdtemp(prefix="coinnect-test-")
os.environ["COINNECT_DATA_DIR"] = _tmp
os.environ["SEED_DEMO"] = "true"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def login(client, email, password="demo1234"):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture
def auth(client):
    return lambda email, password="demo1234": login(client, email, password)
