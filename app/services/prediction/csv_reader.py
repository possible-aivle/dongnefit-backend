"""개별공시지가 CSV/ZIP 파일 리더.

로컬 파일에서 직접 PNU별 가격 이력을 읽어 학습 데이터로 사용.
기존 pipeline의 file_utils, parsing 유틸을 재사용.
"""

from __future__ import annotations

import csv
import logging
import zipfile
from collections import defaultdict
from pathlib import Path

from app.pipeline.parsing import safe_int

logger = logging.getLogger(__name__)

# 기본 데이터 디렉토리
_DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "pipeline" / "public_data" / "개별공시지가"


def _extract_pnu(row: dict) -> str | None:
    """고유번호에서 PNU(19자리) 추출."""
    for key in ("고유번호", "필지고유번호", "pnu"):
        value = row.get(key, "").strip()
        if value and len(value) >= 19:
            return value[:19]
    return None


def _read_csv_from_path(
    csv_path: Path,
    sgg_code: str | None = None,
) -> list[dict[str, int]]:
    """단일 CSV 파일에서 {pnu, base_year, price_per_sqm} 레코드 추출."""
    records: list[dict[str, int]] = []

    for encoding in ("cp949", "utf-8", "utf-8-sig"):
        try:
            with csv_path.open(encoding=encoding, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pnu = _extract_pnu(row)
                    if not pnu:
                        continue
                    if sgg_code and not pnu.startswith(sgg_code):
                        continue

                    base_year = safe_int(row.get("기준연도"))
                    price = safe_int(row.get("공시지가"))
                    if base_year is None or price is None or price <= 0:
                        continue

                    records.append({
                        "pnu": pnu,
                        "base_year": base_year,
                        "price_per_sqm": price,
                    })
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    return records


def read_official_land_prices(
    data_dir: Path | None = None,
    sgg_code: str | None = None,
) -> dict[str, list[dict[str, int]]]:
    """AL_D151 ZIP/CSV 파일들에서 PNU별 가격 이력을 읽어 반환.

    Args:
        data_dir: 개별공시지가 데이터 디렉토리 (기본: pipeline/public_data/개별공시지가/)
        sgg_code: 5자리 시군구코드 필터 (None이면 전체)

    Returns:
        {pnu: [{"base_year": int, "price_per_sqm": int}, ...]}
        각 PNU의 가격 이력은 base_year 오름차순 정렬.
    """
    if data_dir is None:
        data_dir = _DEFAULT_DATA_DIR

    if not data_dir.exists():
        logger.warning("데이터 디렉토리 없음: %s", data_dir)
        return {}

    # sgg_code에서 시도코드(2자리) 추출 → 파일 필터링
    sido_code = sgg_code[:2] if sgg_code else None

    pnu_prices: dict[str, list[dict[str, int]]] = defaultdict(list)
    total_records = 0

    # ZIP 파일 처리
    for zip_path in sorted(data_dir.glob("AL_D151_*.zip")):
        # 시도코드 필터: 파일명에서 시도코드 추출
        if sido_code:
            parts = zip_path.stem.split("_")
            file_sido = parts[2] if len(parts) >= 3 else ""
            if file_sido != sido_code:
                continue

        logger.info("Reading %s ...", zip_path.name)

        try:
            with zipfile.ZipFile(zip_path) as zf:
                for name in zf.namelist():
                    if not name.endswith(".csv"):
                        continue
                    with zf.open(name) as raw:
                        # ZIP 내 CSV → 임시로 메모리에서 읽기
                        for encoding in ("cp949", "utf-8", "utf-8-sig"):
                            try:
                                raw.seek(0)
                                import io
                                text = io.TextIOWrapper(raw, encoding=encoding, newline="")
                                reader = csv.DictReader(text)
                                for row in reader:
                                    pnu = _extract_pnu(row)
                                    if not pnu:
                                        continue
                                    if sgg_code and not pnu.startswith(sgg_code):
                                        continue

                                    base_year = safe_int(row.get("기준연도"))
                                    price = safe_int(row.get("공시지가"))
                                    if base_year is None or price is None or price <= 0:
                                        continue

                                    pnu_prices[pnu].append({
                                        "base_year": base_year,
                                        "price_per_sqm": price,
                                    })
                                    total_records += 1
                                break
                            except (UnicodeDecodeError, UnicodeError):
                                continue
        except zipfile.BadZipFile:
            logger.warning("잘못된 ZIP 파일: %s", zip_path)
            continue

    # 단독 CSV 파일 처리 (ZIP 외)
    for csv_path in sorted(data_dir.glob("AL_D151_*.csv")):
        if sido_code:
            parts = csv_path.stem.split("_")
            file_sido = parts[2] if len(parts) >= 3 else ""
            if file_sido != sido_code:
                continue

        logger.info("Reading %s ...", csv_path.name)
        records = _read_csv_from_path(csv_path, sgg_code)
        for rec in records:
            pnu_prices[rec["pnu"]].append({
                "base_year": rec["base_year"],
                "price_per_sqm": rec["price_per_sqm"],
            })
            total_records += 1

    # PNU별 중복 제거 및 정렬
    result: dict[str, list[dict[str, int]]] = {}
    for pnu, prices in pnu_prices.items():
        # 같은 (base_year) 중복 제거 — 최신 값 유지
        seen: dict[int, dict[str, int]] = {}
        for p in prices:
            seen[p["base_year"]] = p
        result[pnu] = sorted(seen.values(), key=lambda x: x["base_year"])

    logger.info(
        "CSV 데이터 로드 완료: %d PNU, %d 레코드",
        len(result), total_records,
    )
    return result
