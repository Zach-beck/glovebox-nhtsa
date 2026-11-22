"""Process settings. Read at startup, not at import."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _path(name: str) -> Path | None:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    return Path(raw).expanduser()


@dataclass(frozen=True)
class Settings:
    transport: str = "stdio"
    http_host: str = "127.0.0.1"
    http_port: int = 8741
    http_token: str | None = None
    cache_dir: Path | None = None
    data_dir: Path | None = None
    offline: bool = False
    fixtures_dir: Path | None = None
    investigations_file: Path | None = None
    request_gap_seconds: float = 0.25
    request_timeout_seconds: float = 20.0

    @classmethod
    def from_env(cls) -> Settings:
        port_raw = os.environ.get("GLOVEBOX_HTTP_PORT", "8741")
        try:
            port = int(port_raw)
        except ValueError:
            port = 8741
        token = os.environ.get("GLOVEBOX_HTTP_TOKEN") or None
        if token is not None and token.strip() == "":
            token = None
        return cls(
            transport=os.environ.get("GLOVEBOX_TRANSPORT", "stdio").strip().lower() or "stdio",
            http_host=os.environ.get("GLOVEBOX_HTTP_HOST", "127.0.0.1").strip() or "127.0.0.1",
            http_port=port,
            http_token=token,
            cache_dir=_path("GLOVEBOX_CACHE_DIR"),
            data_dir=_path("GLOVEBOX_DATA_DIR"),
            offline=_flag("GLOVEBOX_OFFLINE"),
            fixtures_dir=_path("GLOVEBOX_FIXTURES"),
            investigations_file=_path("GLOVEBOX_INVESTIGATIONS_FILE"),
            request_gap_seconds=float(os.environ.get("GLOVEBOX_REQUEST_GAP_SECONDS", "0.25")),
        )

    def resolved_cache_dir(self) -> Path:
        if self.cache_dir is not None:
            return self.cache_dir
        return Path.home() / ".cache" / "glovebox-mcp"

    def resolved_data_dir(self) -> Path:
        if self.data_dir is not None:
            return self.data_dir
        return self.resolved_cache_dir() / "data"
