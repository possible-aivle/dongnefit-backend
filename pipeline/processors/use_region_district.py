"""용도지역지구 프로세서.

용도지역지구정보 SHP → use_region_districts 테이블.
파일: AL_D131_00_*.zip, AL_D067_00_*.zip 등 (여러 유형).
"""

from pathlib import Path
from typing import Any

from rich.console import Console

from app.models.enums import PublicDataType
from pipeline.file_utils import (
    cleanup_temp_dir,
    extract_zip,
    find_shp_in_dir,
    geojson_to_wkt,
    read_shp_features,
)
from pipeline.processors.base import BaseProcessor, ProcessResult
from pipeline.registry import Registry

console = Console()

PUBLIC_DATA_DIR = Path(__file__).parent.parent / "public_data"


class UseRegionDistrictProcessor(BaseProcessor):
    """용도지역지구 SHP 프로세서.

    A1 → source_id, A2 → district_name, A5 → district_code,
    A4 → admin_code, geometry → geometry.
    """

    name = "use_region_district"
    description = "용도지역지구정보 (SHP)"
    data_type = PublicDataType.USE_REGION_DISTRICT

    # SHP 필드명 매핑 (속성명이 A0~A5 형태)
    FIELD_MAP: dict[str, str] = {
        "A1": "source_id",
        "A2": "district_name",
        "A4": "admin_code",
        "A5": "district_code",
    }

    # 한글 필드명 fallback
    FIELD_MAP_KR: dict[str, str] = {
        "관리번호": "source_id",
        "용도지역지구명": "district_name",
        "행정구역코드": "admin_code",
        "용도코드": "district_code",
    }

    async def collect(self, params: dict[str, Any]) -> list[dict]:
        data_dir = PUBLIC_DATA_DIR / "용도지역지구정보"
        if not data_dir.exists():
            console.print(f"[red]디렉토리 없음: {data_dir}[/]")
            return []

        sgg_prefixes = params.get("sgg_prefixes")
        zip_files = sorted(data_dir.glob("*.zip"))

        if not zip_files:
            console.print("[yellow]대상 용도지역지구 ZIP 파일이 없습니다.[/]")
            return []

        rows: list[dict] = []
        for zip_path in zip_files:
            console.print(f"  처리 중: {zip_path.name}")
            tmp_dir = extract_zip(zip_path)
            try:
                shp_path = find_shp_in_dir(tmp_dir)
                if not shp_path:
                    console.print("    [yellow]SHP 파일 없음[/]")
                    continue

                # admin_code(A4) 필드로 필터링
                features = read_shp_features(shp_path, sgg_prefixes, code_field="A4")
                rows.extend(features)
                console.print(f"    {len(features)}건 읽기 완료")
            finally:
                cleanup_temp_dir(tmp_dir)

        console.print(f"  용도지역지구 총 읽기 완료: {len(rows)}건")
        return rows

    def transform(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for row in raw_data:
            mapped = self._map_fields(row)
            if not mapped.get("source_id"):
                continue

            geojson = row.pop("__geometry__", None)

            # cp949 디코딩이 필요한 경우 처리
            district_name = mapped.get("district_name")
            if district_name and isinstance(district_name, bytes):
                try:
                    district_name = district_name.decode("cp949")
                except (UnicodeDecodeError, AttributeError):
                    pass
            if isinstance(district_name, str):
                district_name = district_name.strip()

            records.append({
                "source_id": str(mapped["source_id"])[:200],
                "district_name": district_name[:200] if district_name else None,
                "district_code": str(mapped.get("district_code", ""))[:50] or None,
                "admin_code": str(mapped.get("admin_code", ""))[:10] or None,
                "geometry": geojson_to_wkt(geojson),
                "raw_data": {k: v for k, v in row.items() if k != "__geometry__"},
            })

        console.print(f"  변환 완료: {len(records)}건")
        return records

    def _map_fields(self, row: dict) -> dict[str, Any]:
        """SHP 속성명을 DB 컬럼으로 매핑합니다."""
        mapped: dict[str, Any] = {}

        # A0~A5 형식 우선
        for shp_field, db_col in self.FIELD_MAP.items():
            value = row.get(shp_field, "")
            if isinstance(value, str):
                value = value.strip()
            if value:
                mapped[db_col] = value

        # 한글 필드명 fallback
        if not mapped.get("source_id"):
            for kr_field, db_col in self.FIELD_MAP_KR.items():
                value = row.get(kr_field, "")
                if isinstance(value, str):
                    value = value.strip()
                if value:
                    mapped[db_col] = value

        return mapped

    def get_params_interactive(self) -> dict[str, Any]:
        return {}

    async def load(self, records: list[dict[str, Any]]) -> ProcessResult:
        """용도지역지구는 중복키 없이 INSERT."""
        from app.database import async_session_maker
        from pipeline.loader import bulk_insert

        async with async_session_maker() as session:
            count = await bulk_insert(
                session, "use_region_districts", records, batch_size=2000
            )

        return ProcessResult(inserted=count)


Registry.register(UseRegionDistrictProcessor())
