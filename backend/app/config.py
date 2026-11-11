"""Runtime settings, read once from the environment (and backend/.env if present)."""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("COINNECT_DATA_DIR", BACKEND_DIR / "data"))


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BACKEND_DIR / ".env")


def _secret_key() -> str:
    """Use SECRET_KEY if set; otherwise generate one and keep it in the data dir so
    sessions survive restarts."""
    if os.getenv("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    key_file = DATA_DIR / ".secret_key"
    if not key_file.exists():
        key_file.write_text(secrets.token_hex(32))
        key_file.chmod(0o600)
    return key_file.read_text().strip()


def _flag(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'coinnect.db'}")
    secret_key: str = field(default_factory=_secret_key)
    token_ttl_hours: int = int(os.getenv("TOKEN_TTL_HOURS", "168"))
    starting_balance: int = int(os.getenv("STARTING_BALANCE", "10"))
    seed_demo: bool = _flag("SEED_DEMO", True)
    cors_origins: tuple[str, ...] = tuple(
        o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()
    )
    # Optional IPFS pinning. Any Kubo-compatible RPC endpoint works: a local `ipfs daemon`
    # (http://127.0.0.1:5001) or a hosted pinning service's RPC API.
    ipfs_rpc_url: str = os.getenv("IPFS_RPC_URL", "").rstrip("/")
    ipfs_rpc_token: str = os.getenv("IPFS_RPC_TOKEN", "")
    ipfs_gateway: str = os.getenv("IPFS_GATEWAY", "https://ipfs.io/ipfs/")


settings = Settings()
