import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "Subscription",
    "SubscriptionCreate",
    "SubscriptionStore",
    "InvalidSubscriptionError",
]

REPO_RE = re.compile(r"^[\w.-]+/[\w.-]+$")

DEFAULT_SUBS_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "subscriptions.json"
)


class InvalidSubscriptionError(ValueError):
    pass


class SubscriptionCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    bot_token: str = Field(min_length=10)
    chat_id: str = Field(min_length=1)
    repo: str
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59)
    timezone: str = Field(default="UTC")

    @field_validator("repo")
    @classmethod
    def _valid_repo(cls, v: str) -> str:
        if not REPO_RE.match(v):
            raise InvalidSubscriptionError(
                f"repo must be owner/name (got {v!r})"
            )
        return v

    @field_validator("timezone")
    @classmethod
    def _valid_tz(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except ZoneInfoNotFoundError as exc:
            raise InvalidSubscriptionError(f"unknown IANA timezone: {v}") from exc
        return v


class Subscription(SubscriptionCreate):
    id: str
    created_at: str


def _mask(token: str) -> str:
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}…{token[-4:]}"


class SubscriptionStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or DEFAULT_SUBS_PATH
        self._lock = asyncio.Lock()

    @property
    def path(self) -> Path:
        return self._path

    async def list_all(self) -> list[Subscription]:
        async with self._lock:
            return self._read()

    async def add(self, sub: SubscriptionCreate) -> Subscription:
        async with self._lock:
            current = self._read()
            new = Subscription(
                **sub.model_dump(),
                id=uuid.uuid4().hex,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            current.append(new)
            self._write(current)
            return new

    async def get(self, sub_id: str) -> Subscription | None:
        async with self._lock:
            for s in self._read():
                if s.id == sub_id:
                    return s
            return None

    async def delete(self, sub_id: str) -> bool:
        async with self._lock:
            current = self._read()
            filtered = [s for s in current if s.id != sub_id]
            if len(filtered) == len(current):
                return False
            self._write(filtered)
            return True

    def _read(self) -> list[Subscription]:
        if not self._path.exists():
            return []
        try:
            raw = json.loads(self._path.read_text())
        except json.JSONDecodeError:
            return []
        out: list[Subscription] = []
        for item in raw:
            try:
                out.append(Subscription.model_validate(item))
            except Exception:
                continue
        return out

    def _write(self, subs: list[Subscription]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [s.model_dump() for s in subs]
        self._path.write_text(json.dumps(payload, indent=2))


def to_public(sub: Subscription) -> dict:
    return {
        "id": sub.id,
        "chat_id": sub.chat_id,
        "repo": sub.repo,
        "hour": sub.hour,
        "minute": sub.minute,
        "timezone": sub.timezone,
        "bot_token_masked": _mask(sub.bot_token),
        "created_at": sub.created_at,
    }
