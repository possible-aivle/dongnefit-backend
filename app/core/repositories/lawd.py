"""LAWD (법정동코드) resolver backed by local CSV."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from app.config import settings


@dataclass(frozen=True)
class LawdCandidate:
    lawd_cd: str | None
    full_name: str
    sido: str | None = None
    sigungu: str | None = None
    emd: str | None = None


def _get_default_data_dir() -> Path:
    """Return default data directory: app/core/api_data/"""
    this_file = Path(__file__)
    return this_file.parent.parent / "api_data"


class LawdRepository:
    """Lazy-loading repository for 법정동 코드 CSV."""

    def __init__(self, *, data_dir: str | Path | None = None, filename: str | None = None):
        name = filename or settings.lawd_code_csv_filename

        # 우선순위: 1) 명시적 data_dir, 2) api_data (기본값), 3) settings.data_dir
        if data_dir is not None:
            base = Path(data_dir)
        else:
            api_data_path = _get_default_data_dir()
            # api_data에 파일이 있으면 사용, 없으면 settings.data_dir 시도
            if (api_data_path / name).exists():
                base = api_data_path
            elif settings.data_dir and Path(settings.data_dir).exists():
                base = Path(settings.data_dir)
            else:
                base = api_data_path  # fallback to api_data

        self.path = base / name
        self._rows: list[dict[str, str]] | None = None

    def _load(self) -> list[dict[str, str]]:
        if self._rows is not None:
            return self._rows

        if not self.path.exists():
            raise FileNotFoundError(
                f"LAWD CSV 파일을 찾을 수 없습니다: {self.path} "
                f"(settings.data_dir={settings.data_dir}, settings.lawd_code_csv_filename={settings.lawd_code_csv_filename})"
            )

        rows: list[dict[str, str]] = []
        last_err: Exception | None = None
        for enc in ("utf-8-sig", "utf-8", "cp949"):
            try:
                with self.path.open("r", encoding=enc, newline="") as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        # Normalize keys: strip BOM and whitespace
                        rr: dict[str, str] = {}
                        for k, v in (r or {}).items():
                            if k is None:
                                continue
                            key = str(k).lstrip("\ufeff").strip()
                            rr[key] = str(v) if v is not None else ""
                        # Filter out deleted regions when '삭제일자' exists and is populated
                        deleted_at = (rr.get("삭제일자") or "").strip()
                        if deleted_at:
                            continue
                        rows.append(rr)
                last_err = None
                break
            except UnicodeDecodeError as e:
                last_err = e
                rows = []
                continue

        if last_err is not None:
            raise last_err

        self._rows = rows
        return rows

    def resolve_code5(self, region_name: str) -> str | None:
        """Return 5-digit LAWD_CD for region_name like '용인시 기흥구'."""
        keywords = [k for k in str(region_name or "").split() if k]
        if not keywords:
            return None

        rows = self._load()
        for r in rows:
            sido = (r.get("시도명") or "").strip()
            sigungu = (r.get("시군구명") or "").strip()
            emd = (r.get("읍면동명") or "").strip()
            if all((kw in sido) or (kw in sigungu) or (kw in emd) for kw in keywords):
                full_code = (r.get("법정동코드") or "").strip()
                return full_code[:5] if full_code else None
        return None

    def search(self, query: str, *, limit: int = 20) -> list[LawdCandidate]:
        """Search candidates by keyword AND match across 시도명/시군구명/읍면동명."""
        q = str(query or "").strip()
        if not q:
            return []

        rows = self._load()
        kws = [x for x in q.split() if x]

        matched: list[dict[str, str]] = []
        for r in rows:
            sido = (r.get("시도명") or "").strip()
            sigungu = (r.get("시군구명") or "").strip()
            emd = (r.get("읍면동명") or "").strip()
            if all((kw in sido) or (kw in sigungu) or (kw in emd) for kw in kws):
                matched.append(r)

        if not matched:
            return []

        # prefer rows with 읍면동명 populated (more specific)
        matched.sort(key=lambda r: 0 if (r.get("읍면동명") or "").strip() else 1)

        out: list[LawdCandidate] = []
        for r in matched[: max(1, int(limit))]:
            full_code = (r.get("법정동코드") or "").strip()
            code5 = full_code[:5] if full_code else None
            sido = (r.get("시도명") or "").strip() or None
            sigungu = (r.get("시군구명") or "").strip() or None
            emd = (r.get("읍면동명") or "").strip() or None
            full_name = " ".join([x for x in (sido, sigungu, emd) if x]).strip()
            out.append(LawdCandidate(lawd_cd=code5, full_name=full_name, sido=sido, sigungu=sigungu, emd=emd))
        return out


