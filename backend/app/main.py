"""Coinnect API.

Run:  uvicorn app.main:app --reload        (from backend/)
Docs: http://localhost:8000/docs

If frontend/dist exists (after `npm run build`), the same server also serves the web app,
so a production deployment is a single process.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import ipfs, ledger
from .config import BACKEND_DIR, settings
from .db import Base, SessionLocal, engine
from .routers import accounts, exchanges, skills
from .routers import ledger as ledger_routes
from .seed import seed

FRONTEND_DIST = BACKEND_DIR.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ledger.ensure_genesis(db)
        if settings.seed_demo:
            seed(db)
    yield


app = FastAPI(
    title="Coinnect API",
    version="2.0.0",
    description="Peer-to-peer skill exchange with SkillCoin escrow and content-addressed receipts.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (accounts.router, skills.router, exchanges.router, ledger_routes.router):
    app.include_router(r)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok", "version": app.version, "ipfs_pinning": ipfs.enabled()}


if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        candidate = (FRONTEND_DIST / path).resolve()
        if path and candidate.is_file() and FRONTEND_DIST in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
