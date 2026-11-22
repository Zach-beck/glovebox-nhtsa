"""TTL cache of shaped tool results. Raw complaint bodies are never written."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Protocol


class ResponseCache(Protocol):
    def get(self, key: str) -> dict[str, Any] | None: ...

    def put(self, key: str, value: dict[str, Any], ttl_seconds: float) -> None: ...


class NullCache:
    def get(self, key: str) -> dict[str, Any] | None:
        del key
        return None

    def put(self, key: str, value: dict[str, Any], ttl_seconds: float) -> None:
        del key, value, ttl_seconds


class MemoryCache:
    def __init__(self) -> None:
        self._entries: dict[str, tuple[float, dict[str, Any]]] = {}

    @property
    def directory(self) -> Path | None:
        return None

    def get(self, key: str) -> dict[str, Any] | None:
        row = self._entries.get(key)
        if row is None:
            return None
        expires_at, value = row
        if expires_at < time.time():
            self._entries.pop(key, None)
            return None
        return value

    def put(self, key: str, value: dict[str, Any], ttl_seconds: float) -> None:
        if value.get("error"):
            return
        self._entries[key] = (time.time() + ttl_seconds, value)


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
        if value.get("error"):
            return
        path = self._path(key)
        body = {"expires_at": time.time() + ttl_seconds, "value": value}
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(body), encoding="utf-8")
        temporary.replace(path)


def cache_mode_from_env() -> str:
    raw = os.environ.get("GLOVEBOX_CACHE", "memory").strip().lower()
    if raw in {"off", "false", "0", "no"}:
        return "off"
    if raw in {"disk", "on", "true", "1"}:
        return "disk"
    return "memory"


def build_response_cache(cache_dir: Path | None, default_disk_dir: Path) -> ResponseCache:
    mode = cache_mode_from_env()
    if mode == "off":
        return NullCache()
    if cache_dir is not None or mode == "disk":
        directory = cache_dir if cache_dir is not None else default_disk_dir
        return DiskCache(directory)
    return MemoryCache()