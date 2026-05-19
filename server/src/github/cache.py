import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

DEFAULT_CACHE_DIR = "server/data/cache"
DEFAULT_TTL_S = 3600


class DiskCache:
    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR) -> None:
        self._dir = Path(cache_dir)

    def get(self, key: str) -> dict[str, Any] | None:
        path = self._path_for(key)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                envelope = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
        if envelope.get("expires_at", 0) < time.time():
            return None
        return envelope.get("value")

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int = DEFAULT_TTL_S) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        envelope = {
            "expires_at": time.time() + ttl_seconds,
            "value": value,
        }
        path = self._path_for(key)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(envelope, f, default=str)
        os.replace(tmp, path)

    def _path_for(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in key)[:64]
        return self._dir / f"{safe}_{digest}.json"
