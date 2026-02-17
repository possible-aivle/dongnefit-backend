"""행정경계 프로세서 (시도, 시군구, 읍면동).

행정경계 SHP → administrative_sidos, administrative_sggs, administrative_emds 테이블.
"""

from pathlib import Path
from typing import Any

from rich.console import Console

from app.models.enums import PublicDataType
from app.pipeline.file_utils import (
    cleanup_temp_dir,
    extract_zip,
    find_shp_in_dir,
    geojson_to_wkt,
    read_shp_features,
)
from app.pipeline.processors.base import BaseProcessor
from app.pipeline.registry import Registry

console = Console()

PUBLIC_DATA_DIR = Path(__file__).parent.parent / "public_data"


class AdministrativeSidoProcessor(BaseProcessor):
    """행정경계 시도 프로세서.

    행정경계_시도 SHP → administrative_sidos.
    """

    name = "admin_boundary_sido"
    description = "행정경계 시도"
    data_type = PublicDataType.ADMINISTRATIVE_SIDO
    simplify_tolerance = 0.001

    async def collect(self, params: dict[str, Any]) -> list[dict]:
        data_dir = PUBLIC_DATA_DIR / "행정경계_시도"
        if not data_dir.exists():
            console.print(f"[red]디렉토리 없음: {data_dir}[/]")
            return []

        rows: list[dict] = []
        for zip_path in data_dir.glob("*.zip"):
            tmp_dir = extract_zip(zip_path)
            try:
                shp_path = find_shp_in_dir(tmp_dir)
                if not shp_path:
                    continue
                features = read_shp_features(shp_path)
                rows.extend(features)
                console.print(f"  {zip_path.name}: {len(features)}건")
            finally:
                cleanup_temp_dir(tmp_dir)

        console.print(f"  시도 SHP 읽기 완료: {len(rows)}건")
        return rows

    def transform(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for row in raw_data:
            bjcd = str(row.get("BJCD", row.get("ADM_CD", row.get("CTPRVN_CD", ""))))
            name = str(row.get("NAME", row.get("CTP_KOR_NM", row.get("CTPRVN_NM", ""))))
            if not bjcd or not name:
                continue

            records.append({
                "sido_code": bjcd[:2],
                "name": name.strip(),
                "geometry": geojson_to_wkt(row.pop("__geometry__", None)),
            })

        console.print(f"  변환 완료: {len(records)}건")
        return records

    def get_params_interactive(self) -> dict[str, Any]:
        return {}


class AdministrativeSigunguProcessor(BaseProcessor):
    """행정경계 시군구 프로세서.

    행정경계_시군구 SHP → administrative_sggs.
    """

    name = "admin_boundary_sigungu"
    description = "행정경계 시군구"
    data_type = PublicDataType.ADMINISTRATIVE_SGG
    simplify_tolerance = 0.001

    async def collect(self, params: dict[str, Any]) -> list[dict]:
        sgg_prefixes = params.get("sgg_prefixes")

        data_dir = PUBLIC_DATA_DIR / "행정경계_시군구"
        if not data_dir.exists():
            console.print(f"[red]디렉토리 없음: {data_dir}[/]")
            return []

        rows: list[dict] = []
        for zip_path in data_dir.glob("*.zip"):
            tmp_dir = extract_zip(zip_path)
            try:
                shp_path = find_shp_in_dir(tmp_dir)
                if not shp_path:
                    continue

                # 시군구 필터 적용
                code_field = "BJCD"
                # 필드명 자동 감지
                import fiona
                with fiona.open(shp_path) as src:
                    if src.schema and src.schema.get("properties"):
                        props = src.schema["properties"]
                        if "SIG_CD" in props:
                            code_field = "SIG_CD"
                        elif "ADM_CD" in props:
                            code_field = "ADM_CD"

                features = read_shp_features(shp_path, sgg_prefixes, code_field)
                rows.extend(features)
                console.print(f"  {zip_path.name}: {len(features)}건")
            finally:
                cleanup_temp_dir(tmp_dir)

        console.print(f"  시군구 SHP 읽기 완료: {len(rows)}건")
        return rows

    def transform(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for row in raw_data:
            bjcd = str(
                row.get("BJCD", row.get("ADM_CD", row.get("SIG_CD", "")))
            )
            name = str(
                row.get("NAME", row.get("SIG_KOR_NM", row.get("SIGUNGU_NM", "")))
            )
            if not bjcd or not name or len(bjcd) < 5:
                continue

            records.append({
                "sgg_code": bjcd[:5],
                "name": name.strip(),
                "sido_code": bjcd[:2],
                "geometry": geojson_to_wkt(row.pop("__geometry__", None)),
            })

        console.print(f"  변환 완료: {len(records)}건")
        return records

    def get_params_interactive(self) -> dict[str, Any]:
        return {}


class AdministrativeEmdProcessor(BaseProcessor):
    """행정경계 읍면동 프로세서.

    행정경계_읍면동 SHP → administrative_emds.
    """

    name = "admin_boundary_emd"
    description = "행정경계 읍면동"
    data_type = PublicDataType.ADMINISTRATIVE_EMD
    simplify_tolerance = 0.001

    async def collect(self, params: dict[str, Any]) -> list[dict]:
        sgg_prefixes = params.get("sgg_prefixes")

        data_dir = PUBLIC_DATA_DIR / "행정경계_읍면동"
        if not data_dir.exists():
            console.print(f"[red]디렉토리 없음: {data_dir}[/]")
            return []

        rows: list[dict] = []
        for zip_path in data_dir.glob("*.zip"):
            tmp_dir = extract_zip(zip_path)
            try:
                shp_path = find_shp_in_dir(tmp_dir)
                if not shp_path:
                    continue

                # 필드명 자동 감지
                code_field = "BJCD"
                import fiona
                with fiona.open(shp_path) as src:
                    if src.schema and src.schema.get("properties"):
                        props = src.schema["properties"]
                        if "EMD_CD" in props:
                            code_field = "EMD_CD"
                        elif "ADM_CD" in props:
                            code_field = "ADM_CD"

                features = read_shp_features(shp_path, sgg_prefixes, code_field)
                rows.extend(features)
                console.print(f"  {zip_path.name}: {len(features)}건")
            finally:
                cleanup_temp_dir(tmp_dir)

        console.print(f"  읍면동 SHP 읽기 완료: {len(rows)}건")
        return rows

    def transform(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for row in raw_data:
            bjcd = str(
                row.get("BJCD", row.get("ADM_CD", row.get("EMD_CD", "")))
            )
            name = str(
                row.get("NAME", row.get("EMD_KOR_NM", row.get("EMD_NM", "")))
            )
            if not bjcd or not name or len(bjcd) < 5:
                continue

            records.append({
                "emd_code": bjcd,
                "name": name.strip(),
                "sgg_code": bjcd[:5],
                "geometry": geojson_to_wkt(row.pop("__geometry__", None)),
            })

        console.print(f"  변환 완료: {len(records)}건")
        return records

    def get_params_interactive(self) -> dict[str, Any]:
        return {}


Registry.register(AdministrativeSidoProcessor())
Registry.register(AdministrativeSigunguProcessor())
Registry.register(AdministrativeEmdProcessor())
