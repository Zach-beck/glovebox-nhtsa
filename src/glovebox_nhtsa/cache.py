"""Disk cache of shaped tool results. Raw complaint bodies are never written."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class DiskCache:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.directory / f"{digest}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        expires = payload.get("expires_at")
        if not isinstance(expires, (int, float)) or expires < time.time():
            path.unlink(missing_ok=True)
            return None
        value = payload.get("value")
        if isinstance(value, dict):
            return value
        return None

    def put(self, key: str, value: dict[str, Any], ttl_seconds: float) -> None:
        path = self._path(key)
        body = {"expires_at": time.time() + ttl_seconds, "value": value}
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(body), encoding="utf-8")
        temporary.replace(path)
