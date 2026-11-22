"""Local index of NHTSA's investigations flat file.

The zip is a few megabytes. The text inside is hundreds of megabytes, mostly
repeated summary prose. The index keeps the short columns and loads a clipped
summary only when one investigation id is requested.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from glovebox_nhtsa.backend import ALLOWED_HOSTS, USER_AGENT, UpstreamError

INV_URL = "https://static.nhtsa.gov/odi/ffdd/inv/FLAT_INV.zip"
INDEX_NAME = "inv_index.json"


@dataclass(frozen=True)
class InvestigationRow:
    action: str
    make: str
    model: str
    year: str
    component: str
    opened: str
    closed: str
    campaign: str
    subject: str


def _split_row(line: str) -> InvestigationRow | None:
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 10:
        return None
    action = parts[0].strip()
    if action == "" or " " in action and not action[:1].isalpha():
        return None
    if action.upper().startswith("NHTSA ACTION"):
        return None
    while len(parts) < 11:
        parts.append("")
    return InvestigationRow(
        action=action,
        make=parts[1].strip(),
        model=parts[2].strip(),
        year=parts[3].strip(),
        component=parts[4].strip(),
        opened=parts[6].strip(),
        closed=parts[7].strip(),
        campaign=parts[8].strip(),
        subject=parts[9].strip(),
    )


def parse_lines(lines: list[str]) -> list[InvestigationRow]:
    rows = []
    for line in lines:
        if "\t" not in line:
            continue
        row = _split_row(line)
        if row is not None:
            rows.append(row)
    return rows


def _iter_text_lines(path: Path):
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = [info.filename for info in archive.infolist() if info.filename.lower().endswith(".txt")]
            if not names:
                raise UpstreamError("upstream_unavailable", "Investigations zip has no text file.", True)
            with archive.open(names[0]) as handle:
                for raw in handle:
                    yield raw.decode("utf-8", "replace")
        return
    with path.open("rb") as handle:
        for raw in handle:
            yield raw.decode("utf-8", "replace")


def load_index(path: Path) -> list[InvestigationRow]:
    rows: list[InvestigationRow] = []
    for line in _iter_text_lines(path):
        if "\t" not in line:
            continue
        row = _split_row(line)
        if row is not None:
            rows.append(row)
    return rows


def _row_dict(row: InvestigationRow, *, summary: str | None = None) -> dict[str, Any]:
    year: str | None
    if row.year in {"", "9999"}:
        year = None
    else:
        year = row.year
    item: dict[str, Any] = {
        "nhtsa_id": row.action,
        "make": row.make,
        "model": row.model,
        "model_year": year,
        "component": row.component,
        "opened": row.opened or None,
        "closed": row.closed or None,
        "campaign_number": row.campaign or None,
        "subject": row.subject,
    }
    if summary is not None:
        item["summary"] = summary
    return item


def _matches(row: InvestigationRow, *, make: str, model: str, model_year: str, component: str, query: str, nhtsa_id: str) -> bool:
    if nhtsa_id and row.action.upper() != nhtsa_id.upper():
        return False
    if make and make.upper() not in row.make.upper():
        return False
    if model and model.upper() not in row.model.upper():
        return False
    if model_year and row.year != model_year:
        return False
    if component and component.upper() not in row.component.upper():
        return False
    if query:
        haystack = f"{row.action} {row.subject}".upper()
        if query.upper() not in haystack:
            return False
    return True


def search_rows(
    rows: list[InvestigationRow],
    *,
    make: str = "",
    model: str = "",
    model_year: str = "",
    component: str = "",
    query: str = "",
    nhtsa_id: str = "",
) -> list[InvestigationRow]:
    matched = [
        row
        for row in rows
        if _matches(
            row,
            make=make,
            model=model,
            model_year=model_year,
            component=component,
            query=query,
            nhtsa_id=nhtsa_id,
        )
    ]
    matched.sort(key=lambda row: row.opened or "", reverse=True)
    return matched


def clipped_summary(path: Path, nhtsa_id: str, limit: int = 1000) -> str | None:
    target = nhtsa_id.upper()
    for line in _iter_text_lines(path):
        if not line.upper().startswith(target + "\t"):
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 11:
            return None
        text = parts[10].strip()
        if len(text) <= limit:
            return text
        return text[: limit - 1].rstrip() + "..."
    return None


class InvestigationIndex:
    def __init__(self, settings_file: Path | None, data_dir: Path, offline: bool) -> None:
        self._file = settings_file
        self._data_dir = data_dir
        self._offline = offline
        self._rows: list[InvestigationRow] | None = None
        self._source: Path | None = None
        self._modified: str | None = None

    async def ensure(self) -> None:
        if self._rows is not None:
            return
        path, modified = await self._resolve_source()
        index_path = self._index_path(path)
        if index_path.is_file() and index_path.stat().st_mtime >= path.stat().st_mtime:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            self._rows = [InvestigationRow(**item) for item in payload["rows"]]
            self._modified = payload.get("modified") or modified
        else:
            self._rows = load_index(path)
            self._modified = modified
            if path.suffix.lower() == ".zip":
                index_path.write_text(
                    json.dumps(
                        {
                            "modified": modified,
                            "rows": [row.__dict__ for row in self._rows],
                        }
                    ),
                    encoding="utf-8",
                )
        self._source = path

    def _index_path(self, source: Path) -> Path:
        return source.with_name(INDEX_NAME) if source.suffix.lower() == ".zip" else source.with_suffix(".index.json")

    async def _resolve_source(self) -> tuple[Path, str | None]:
        if self._file is not None:
            if not self._file.is_file():
                raise UpstreamError("upstream_unavailable", "Investigations file was not found.", True, "investigations")
            return self._file, None
        if self._offline:
            raise UpstreamError(
                "upstream_unavailable",
                "Offline mode needs GLOVEBOX_INVESTIGATIONS_FILE or a previously downloaded zip.",
                False,
                "investigations",
            )
        self._data_dir.mkdir(parents=True, exist_ok=True)
        destination = self._data_dir / "FLAT_INV.zip"
        modified = await _download_inv(destination)
        return destination, modified

    async def search(self, **kwargs: Any) -> dict[str, Any]:
        try:
            await self.ensure()
        except UpstreamError as exc:
            return exc.to_dict()
        assert self._rows is not None and self._source is not None
        nhtsa_id = str(kwargs.get("nhtsa_id") or "")
        limit = int(kwargs.pop("limit", 20))
        matched = search_rows(self._rows, **kwargs)
        summary = None
        if nhtsa_id and matched:
            summary = clipped_summary(self._source, nhtsa_id)
        window = matched[:limit]
        rows = []
        for index, row in enumerate(window):
            item = _row_dict(row, summary=summary if index == 0 and nhtsa_id else None)
            rows.append(item)
        return {
            "count": len(matched),
            "returned": len(rows),
            "truncated": len(matched) > limit,
            "file_modified": self._modified,
            "rows": rows,
            "note": "Loaded from NHTSA's investigations flat file. There is no public investigations REST API.",
        }


async def _download_inv(destination: Path) -> str | None:
    host = "static.nhtsa.gov"
    if host not in ALLOWED_HOSTS:
        raise UpstreamError("not_found", "Refused investigations download.", False, "glovebox")
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=False) as client:
        response = await client.get(INV_URL, headers={"User-Agent": USER_AGENT})
    if response.status_code != 200:
        raise UpstreamError("upstream_unavailable", f"Investigations download returned HTTP {response.status_code}.", True)
    temporary = destination.with_suffix(".zip.part")
    temporary.write_bytes(response.content)
    temporary.replace(destination)
    return response.headers.get("last-modified")
