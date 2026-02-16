"""부동산 실거래가 엑셀 데이터 프로세서.

매매와 전월세를 별도 프로세서로 분리하여 처리합니다.
- RealEstateSaleProcessor: pipeline/public_data/실거래가_매매/ → real_estate_sales
- RealEstateRentalProcessor: pipeline/public_data/실거래가_전월세/ → real_estate_rentals

파일명 규칙:
  매매: {부동산유형}_매매_{YYYYMM}.xlsx
  전월세: {부동산유형}_전월세_{YYYYMM}.xlsx

Usage:
    # CLI
    uv run python -m pipeline.cli

    # 직접 실행 (전체 적재, TRUNCATE 후)
    uv run python -m pipeline.processors.real_estate_transaction
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from rich.console import Console

from app.models.enums import PropertyType, PublicDataType, TransactionType
from pipeline.processors.base import BaseProcessor, ProcessResult
from pipeline.registry import Registry

console = Console()

SALE_EXCEL_DIR = Path(__file__).parent.parent / "public_data" / "실거래가_매매"
RENTAL_EXCEL_DIR = Path(__file__).parent.parent / "public_data" / "실거래가_전월세"
HEADER_ROW = 12  # 0-based index; Excel row 13이 컬럼 헤더

# ── 파일명 → PropertyType 매핑 ──

PROPERTY_TYPE_MAP: dict[str, PropertyType] = {
    "아파트": PropertyType.APARTMENT,
    "연립다세대": PropertyType.ROW_HOUSE,
    "단독다가구": PropertyType.DETACHED_HOUSE,
    "오피스텔": PropertyType.OFFICETEL,
}

# ── 매매 전용 컬럼 매핑 ──

SALE_COLUMN_MAP: dict[str, str] = {
    "시군구": "sigungu",
    "단지명": "building_name",
    "건물명": "building_name",
    "전용면적(㎡)": "exclusive_area",
    "대지면적(㎡)": "land_area",
    "대지권면적(㎡)": "land_area",
    "연면적(㎡)": "floor_area",
    "계약면적(㎡)": "contract_area",
    "층": "floor",
    "건축년도": "build_year",
    "거래금액(만원)": "transaction_amount",
    "거래유형": "deal_type",
    # 토지 전용
    "지목": "land_category",
    "용도지역": "use_area",
}

# ── 전월세 전용 컬럼 매핑 ──

RENTAL_COLUMN_MAP: dict[str, str] = {
    "시군구": "sigungu",
    "단지명": "building_name",
    "건물명": "building_name",
    "전용면적(㎡)": "exclusive_area",
    "대지면적(㎡)": "land_area",
    "대지권면적(㎡)": "land_area",
    "연면적(㎡)": "floor_area",
    "층": "floor",
    "건축년도": "build_year",
    "보증금(만원)": "deposit",
    "월세금(만원)": "monthly_rent_amount",
    "계약기간": "contract_period",
    "계약구분": "contract_type",
    "거래유형": "deal_type",
}

# 금액 필드 (쉼표 제거 + int 변환)
SALE_AMOUNT_FIELDS = {"transaction_amount"}
RENTAL_AMOUNT_FIELDS = {"deposit", "monthly_rent_amount"}

# float 필드
FLOAT_FIELDS = {"exclusive_area", "land_area", "floor_area", "contract_area"}


# ── 유틸리티 함수 ──


def _clean(val: Any) -> str | None:
    """값 정리: '-', '', NaN → None."""
    if val is None:
        return None
    if isinstance(val, float) and pd.isna(val):
        return None
    s = str(val).strip()
    return None if s in ("-", "", "nan") else s


def _parse_amount(val: Any) -> int | None:
    """금액 파싱: '15,500' → 15500."""
    cleaned = _clean(val)
    if cleaned is None:
        return None
    try:
        return int(cleaned.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def _parse_float(val: Any) -> float | None:
    cleaned = _clean(val)
    if cleaned is None:
        return None
    try:
        return float(cleaned)
    except (ValueError, AttributeError):
        return None


def _parse_int(val: Any) -> int | None:
    cleaned = _clean(val)
    if cleaned is None:
        return None
    try:
        return int(float(cleaned))
    except (ValueError, AttributeError):
        return None


def _parse_date(year_month: Any, day: Any) -> date | None:
    """계약년월(YYYYMM) + 계약일(DD) → date."""
    ym = _clean(year_month)
    d = _clean(day)
    if not ym or not d:
        return None
    try:
        ym_str = str(int(float(ym)))
        d_int = int(float(d))
        return date(int(ym_str[:4]), int(ym_str[4:6]), d_int)
    except (ValueError, IndexError):
        return None


def _utc_now() -> datetime:
    """현재 UTC 시각 (naive)."""
    from datetime import UTC

    return datetime.now(UTC).replace(tzinfo=None)


def parse_filename(filename: str) -> PropertyType | None:
    """파일명에서 PropertyType 파싱.

    예: '아파트_매매_202503.xlsx' → PropertyType.APARTMENT
        '단독다가구_전월세_202601.xlsx' → PropertyType.DETACHED_HOUSE
    """
    stem = Path(filename).stem
    parts = stem.rsplit("_", 2)
    if len(parts) != 3:
        return None
    prop_name = parts[0]
    return PROPERTY_TYPE_MAP.get(prop_name)


def _build_raw_data(row: dict[str, Any], columns: list[str]) -> str:
    """원본 행을 JSON string으로 변환."""
    raw: dict[str, str] = {}
    for col in columns:
        v = row.get(col)
        if v is not None and not (isinstance(v, float) and pd.isna(v)):
            raw[col] = str(v)
    return json.dumps(raw, ensure_ascii=False)


def transform_sale_row(
    row: dict[str, Any],
    columns: list[str],
    property_type: PropertyType,
    now: datetime,
) -> dict[str, Any]:
    """매매 엑셀 행 하나를 DB 레코드 dict로 변환."""
    record: dict[str, Any] = {
        "property_type": property_type.name,
        "created_at": now,
        "updated_at": now,
    }

    for col in columns:
        if col in ("NO", "계약년월", "계약일"):
            continue
        db_field = SALE_COLUMN_MAP.get(col)
        if db_field is None:
            continue
        val = row.get(col)
        if db_field in SALE_AMOUNT_FIELDS:
            record[db_field] = _parse_amount(val)
        elif db_field in FLOAT_FIELDS:
            record[db_field] = _parse_float(val)
        elif db_field == "build_year":
            record[db_field] = _parse_int(val)
        else:
            record[db_field] = _clean(val)

    record["transaction_date"] = _parse_date(row.get("계약년월"), row.get("계약일"))

    if "floor" in record and record["floor"] is not None:
        record["floor"] = str(record["floor"])

    record["raw_data"] = _build_raw_data(row, columns)
    return record


def transform_rental_row(
    row: dict[str, Any],
    columns: list[str],
    property_type: PropertyType,
    now: datetime,
) -> dict[str, Any]:
    """전월세 엑셀 행 하나를 DB 레코드 dict로 변환."""
    record: dict[str, Any] = {
        "property_type": property_type.name,
        "created_at": now,
        "updated_at": now,
    }

    for col in columns:
        if col in ("NO", "계약년월", "계약일"):
            continue
        db_field = RENTAL_COLUMN_MAP.get(col)
        if db_field is None:
            continue
        val = row.get(col)
        if db_field in RENTAL_AMOUNT_FIELDS:
            record[db_field] = _parse_amount(val)
        elif db_field in FLOAT_FIELDS:
            record[db_field] = _parse_float(val)
        elif db_field == "build_year":
            record[db_field] = _parse_int(val)
        else:
            record[db_field] = _clean(val)

    record["transaction_date"] = _parse_date(row.get("계약년월"), row.get("계약일"))

    # 거래유형 결정 (전세/월세)
    rent_type = _clean(row.get("전월세구분"))
    if rent_type == "월세":
        record["transaction_type"] = TransactionType.MONTHLY_RENT.name
    else:
        record["transaction_type"] = TransactionType.JEONSE.name

    if "floor" in record and record["floor"] is not None:
        record["floor"] = str(record["floor"])

    record["raw_data"] = _build_raw_data(row, columns)
    return record


class RealEstateSaleProcessor(BaseProcessor):
    """부동산 매매 실거래가 엑셀 프로세서.

    pipeline/public_data/실거래가_매매/ 의 엑셀 파일을 읽어
    real_estate_sales 테이블에 bulk insert합니다.
    """

    name = "real_estate_sale"
    description = "부동산 매매 실거래가 (엑셀)"
    data_type = PublicDataType.REAL_ESTATE_SALE

    async def collect(self, params: dict[str, Any]) -> list[dict]:
        """사용하지 않음 (run에서 파일별 직접 처리)."""
        return []

    def transform(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """사용하지 않음 (run에서 파일별 직접 처리)."""
        return []

    def get_params_interactive(self) -> dict[str, Any]:
        """CLI에서 파라미터를 입력받습니다."""
        from InquirerPy import inquirer

        prop_choices = [
            {"name": f"{kr} ({pt.value})", "value": kr}
            for kr, pt in PROPERTY_TYPE_MAP.items()
        ]
        selected_props = inquirer.checkbox(
            message="부동산 유형 선택 (Space 선택, Enter 확인, 미선택시 전체):",
            choices=prop_choices,
        ).execute()
        if not selected_props:
            selected_props = list(PROPERTY_TYPE_MAP.keys())

        truncate = inquirer.confirm(
            message="기존 매매 데이터 삭제 후 적재? (TRUNCATE)",
            default=False,
        ).execute()

        return {
            "property_types": selected_props,
            "truncate": truncate,
        }

    async def run(self, params: dict[str, Any] | None = None) -> ProcessResult:
        """매매 엑셀 파일을 읽어 DB에 적재합니다."""
        if params is None:
            params = self.get_params_interactive()

        excel_dir = Path(params.get("excel_dir", str(SALE_EXCEL_DIR)))
        target_props = set(params.get("property_types", list(PROPERTY_TYPE_MAP.keys())))
        truncate = params.get("truncate", False)

        # 대상 파일 수집
        files = sorted(excel_dir.glob("*.xlsx"))
        target_files: list[tuple[Path, PropertyType]] = []
        for f in files:
            prop_type = parse_filename(f.name)
            if prop_type is None:
                continue
            prop_kr = f.stem.rsplit("_", 2)[0]
            if prop_kr in target_props:
                target_files.append((f, prop_type))

        if not target_files:
            console.print("[yellow]대상 매매 엑셀 파일이 없습니다.[/]")
            return ProcessResult()

        console.print("\n[bold]━━━ 매매 실거래가 데이터 적재 ━━━[/]")
        console.print(f"  디렉토리: {excel_dir}")
        console.print(f"  대상 파일: {len(target_files)}개")
        console.print(f"  부동산 유형: {', '.join(target_props)}")

        from app.database import async_session_maker
        from pipeline.loader import bulk_insert

        if truncate:
            async with async_session_maker() as session:
                from sqlalchemy import text

                await session.execute(text("TRUNCATE TABLE real_estate_sales CASCADE"))
                await session.commit()
            console.print("  [yellow]기존 매매 데이터 삭제 완료[/]")

        total_result = ProcessResult()
        now = _utc_now()

        console.print()
        for i, (filepath, prop_type) in enumerate(target_files, 1):
            label = f"  [{i}/{len(target_files)}] {filepath.name}"
            try:
                df = pd.read_excel(
                    filepath, header=HEADER_ROW, engine="openpyxl", dtype=str
                )
                if df.empty:
                    console.print(f"{label} [dim]빈 파일[/]")
                    continue

                columns = list(df.columns)
                rows = df.to_dict("records")
                records = [
                    transform_sale_row(r, columns, prop_type, now) for r in rows
                ]

                if records:
                    async with async_session_maker() as session:
                        count = await bulk_insert(
                            session,
                            "real_estate_sales",
                            records,
                            batch_size=1000,
                        )
                        total_result.inserted += count

                total_result.collected += len(df)
                console.print(f"{label} [green]{len(records):,}건 완료[/]")

            except Exception as e:
                console.print(f"{label} [red]에러: {e}[/]")
                total_result.errors += 1

        console.print("\n[bold]━━━ 매매 적재 완료 ━━━[/]")
        console.print(f"  {total_result.summary()}")
        return total_result


class RealEstateRentalProcessor(BaseProcessor):
    """부동산 전월세 실거래가 엑셀 프로세서.

    pipeline/public_data/실거래가_전월세/ 의 엑셀 파일을 읽어
    real_estate_rentals 테이블에 bulk insert합니다.
    """

    name = "real_estate_rental"
    description = "부동산 전월세 실거래가 (엑셀)"
    data_type = PublicDataType.REAL_ESTATE_RENTAL

    async def collect(self, params: dict[str, Any]) -> list[dict]:
        """사용하지 않음 (run에서 파일별 직접 처리)."""
        return []

    def transform(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """사용하지 않음 (run에서 파일별 직접 처리)."""
        return []

    def get_params_interactive(self) -> dict[str, Any]:
        """CLI에서 파라미터를 입력받습니다."""
        from InquirerPy import inquirer

        prop_choices = [
            {"name": f"{kr} ({pt.value})", "value": kr}
            for kr, pt in PROPERTY_TYPE_MAP.items()
        ]
        selected_props = inquirer.checkbox(
            message="부동산 유형 선택 (Space 선택, Enter 확인, 미선택시 전체):",
            choices=prop_choices,
        ).execute()
        if not selected_props:
            selected_props = list(PROPERTY_TYPE_MAP.keys())

        truncate = inquirer.confirm(
            message="기존 전월세 데이터 삭제 후 적재? (TRUNCATE)",
            default=False,
        ).execute()

        return {
            "property_types": selected_props,
            "truncate": truncate,
        }

    async def run(self, params: dict[str, Any] | None = None) -> ProcessResult:
        """전월세 엑셀 파일을 읽어 DB에 적재합니다."""
        if params is None:
            params = self.get_params_interactive()

        excel_dir = Path(params.get("excel_dir", str(RENTAL_EXCEL_DIR)))
        target_props = set(params.get("property_types", list(PROPERTY_TYPE_MAP.keys())))
        truncate = params.get("truncate", False)

        # 대상 파일 수집
        files = sorted(excel_dir.glob("*.xlsx"))
        target_files: list[tuple[Path, PropertyType]] = []
        for f in files:
            prop_type = parse_filename(f.name)
            if prop_type is None:
                continue
            prop_kr = f.stem.rsplit("_", 2)[0]
            if prop_kr in target_props:
                target_files.append((f, prop_type))

        if not target_files:
            console.print("[yellow]대상 전월세 엑셀 파일이 없습니다.[/]")
            return ProcessResult()

        console.print("\n[bold]━━━ 전월세 실거래가 데이터 적재 ━━━[/]")
        console.print(f"  디렉토리: {excel_dir}")
        console.print(f"  대상 파일: {len(target_files)}개")
        console.print(f"  부동산 유형: {', '.join(target_props)}")

        from app.database import async_session_maker
        from pipeline.loader import bulk_insert

        if truncate:
            async with async_session_maker() as session:
                from sqlalchemy import text

                await session.execute(text("TRUNCATE TABLE real_estate_rentals CASCADE"))
                await session.commit()
            console.print("  [yellow]기존 전월세 데이터 삭제 완료[/]")

        total_result = ProcessResult()
        now = _utc_now()

        console.print()
        for i, (filepath, prop_type) in enumerate(target_files, 1):
            label = f"  [{i}/{len(target_files)}] {filepath.name}"
            try:
                df = pd.read_excel(
                    filepath, header=HEADER_ROW, engine="openpyxl", dtype=str
                )
                if df.empty:
                    console.print(f"{label} [dim]빈 파일[/]")
                    continue

                columns = list(df.columns)
                rows = df.to_dict("records")
                records = [
                    transform_rental_row(r, columns, prop_type, now) for r in rows
                ]

                if records:
                    async with async_session_maker() as session:
                        count = await bulk_insert(
                            session,
                            "real_estate_rentals",
                            records,
                            batch_size=1000,
                        )
                        total_result.inserted += count

                total_result.collected += len(df)
                console.print(f"{label} [green]{len(records):,}건 완료[/]")

            except Exception as e:
                console.print(f"{label} [red]에러: {e}[/]")
                total_result.errors += 1

        console.print("\n[bold]━━━ 전월세 적재 완료 ━━━[/]")
        console.print(f"  {total_result.summary()}")
        return total_result


Registry.register(RealEstateSaleProcessor())
Registry.register(RealEstateRentalProcessor())


if __name__ == "__main__":
    import asyncio

    async def main() -> None:
        all_props = list(PROPERTY_TYPE_MAP.keys())

        # 매매 적재
        sale_processor = RealEstateSaleProcessor()
        sale_result = await sale_processor.run(
            {"property_types": all_props, "truncate": True}
        )
        console.print(f"\n매매: {sale_result.summary()}")

        # 전월세 적재
        rental_processor = RealEstateRentalProcessor()
        rental_result = await rental_processor.run(
            {"property_types": all_props, "truncate": True}
        )
        console.print(f"전월세: {rental_result.summary()}")

    asyncio.run(main())
