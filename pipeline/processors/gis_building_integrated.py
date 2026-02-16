"""GIS건물통합정보 프로세서 (AL_D010).

SHP 파일 기반 건물 공간 + 속성 통합 데이터 프로세서.
"""

from pathlib import Path
from typing import Any

from InquirerPy import inquirer
from rich.console import Console

from app.models.enums import PublicDataType
from pipeline.file_utils import _make_crs_transformer, _transform_geojson, geojson_to_wkt
from pipeline.processors.base import BaseProcessor
from pipeline.registry import Registry

console = Console()


class GisBuildingIntegratedProcessor(BaseProcessor):
    """GIS건물통합정보 SHP 프로세서.

    vworld AL_D010 (29개 SHP 컬럼 중 유지 필드만 매핑).
    """

    name = "gis_building_integrated"
    description = "GIS건물통합정보 (AL_D010, SHP)"
    data_type = PublicDataType.GIS_BUILDING_INTEGRATED

    # SHP 속성명(A0~A28) → DB 컬럼명 매핑 (유지 필드만)
    FIELD_MAP: dict[str, str] = {
        "A2": "pnu",
        "A9": "use_name",
        "A12": "building_area",
        "A13": "approval_date",
        "A14": "total_floor_area",
        "A15": "site_area",
        "A16": "height",
        "A19": "building_id",
        "A24": "building_name",
        "A26": "above_ground_floors",
        "A27": "underground_floors",
    }

    # 한글 속성명 fallback (일부 SHP에서 한글 필드명 사용)
    FIELD_MAP_KR: dict[str, str] = {
        "고유번호": "pnu",
        "건축물용도명": "use_name",
        "건축물면적": "building_area",
        "사용승인일자": "approval_date",
        "연면적": "total_floor_area",
        "대지면적": "site_area",
        "높이": "height",
        "건축물ID": "building_id",
        "건물명": "building_name",
        "지상층수": "above_ground_floors",
        "지하층수": "underground_floors",
    }

    async def collect(self, params: dict[str, Any]) -> list[dict]:
        """SHP 파일을 읽어 raw dict 리스트를 반환합니다.

        zip_files가 params에 있으면 ZIP 배치 처리,
        아니면 단일 file_path 처리.
        """
        try:
            import fiona  # noqa: F401
        except ImportError:
            console.print("[red]fiona 패키지가 필요합니다: uv add fiona[/]")
            return []

        sgg_prefixes: list[str] | None = params.get("sgg_prefixes")
        zip_files: list[Path] = params.get("zip_files", [])

        if zip_files:
            return self._collect_from_zips(zip_files, sgg_prefixes)

        file_path_str = params.get("file_path")
        if not file_path_str:
            return []

        file_path = Path(file_path_str)
        if not file_path.exists():
            console.print(f"[red]파일을 찾을 수 없습니다: {file_path}[/]")
            return []

        if file_path.suffix == ".zip":
            return self._collect_from_zips([file_path], sgg_prefixes)

        return self._read_shp(file_path, sgg_prefixes)

    def _collect_from_zips(
        self, zip_files: list[Path], sgg_prefixes: list[str] | None = None
    ) -> list[dict]:
        """ZIP 파일 목록에서 SHP를 추출하여 읽습니다."""
        from pipeline.file_utils import cleanup_temp_dir, extract_zip, find_shp_in_dir

        all_rows: list[dict] = []
        for zip_path in zip_files:
            console.print(f"  처리 중: {zip_path.name}")
            tmp_dir = extract_zip(zip_path)
            try:
                shp_path = find_shp_in_dir(tmp_dir)
                if not shp_path:
                    console.print("    [yellow]SHP 파일 없음[/]")
                    continue
                rows = self._read_shp(shp_path, sgg_prefixes)
                all_rows.extend(rows)
                console.print(f"    {len(rows)}건 읽기 완료")
            finally:
                cleanup_temp_dir(tmp_dir)

        console.print(f"  총 SHP 읽기 완료: {len(all_rows)}건")
        return all_rows

    def _read_shp(
        self, shp_path: Path, sgg_prefixes: list[str] | None = None
    ) -> list[dict]:
        """SHP 파일을 읽어 raw dict 리스트를 반환합니다."""
        import fiona

        rows: list[dict] = []
        with fiona.open(shp_path) as src:
            # CRS 자동 감지 및 WGS84 변환 준비
            transformer, needs_transform = _make_crs_transformer(src.crs)

            for feature in src:
                row: dict[str, Any] = dict(feature.get("properties", {}))

                # PNU 기반 필터링
                if sgg_prefixes:
                    pnu = str(row.get("A2", row.get("고유번호", ""))).strip()
                    if not any(pnu.startswith(p) for p in sgg_prefixes):
                        continue

                geom = feature.get("geometry")
                if geom:
                    geom_dict = dict(geom)
                    if needs_transform and transformer is not None:
                        geom_dict = _transform_geojson(geom_dict, transformer)
                    row["__geometry__"] = geom_dict
                rows.append(row)

        return rows

    def transform(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """SHP raw 데이터를 DB 컬럼에 맞게 변환합니다."""
        records: list[dict[str, Any]] = []

        for row in raw_data:
            mapped = self._map_fields(row)
            if mapped is None:
                continue

            # PNU 추출 (19자리)
            pnu = mapped.get("pnu", "")
            if pnu and len(str(pnu)) >= 19:
                mapped["pnu"] = str(pnu)[:19]
            else:
                continue

            # 숫자 타입 변환
            mapped["building_area"] = self._safe_float(mapped.get("building_area"))
            mapped["total_floor_area"] = self._safe_float(mapped.get("total_floor_area"))
            mapped["site_area"] = self._safe_float(mapped.get("site_area"))
            mapped["height"] = self._safe_float(mapped.get("height"))
            mapped["above_ground_floors"] = self._safe_int(mapped.get("above_ground_floors"))
            mapped["underground_floors"] = self._safe_int(mapped.get("underground_floors"))

            # geometry (GeoJSON → WKT)
            mapped["geometry"] = geojson_to_wkt(row.pop("__geometry__", None))

            # raw_data 보존 (geometry 제외)
            mapped["raw_data"] = {k: v for k, v in row.items() if k != "__geometry__"}

            records.append(mapped)

        console.print(f"  변환 완료: {len(records)}건")
        return records

    def _map_fields(self, row: dict) -> dict[str, Any] | None:
        """SHP 속성명을 DB 컬럼으로 매핑합니다."""
        mapped: dict[str, Any] = {}

        # A0~A28 형식 필드명 우선 시도
        for shp_field, db_col in self.FIELD_MAP.items():
            value = row.get(shp_field, "")
            if isinstance(value, str):
                value = value.strip()
            mapped[db_col] = value if value else None

        # 한글 필드명 fallback
        if not mapped.get("pnu"):
            for kr_field, db_col in self.FIELD_MAP_KR.items():
                value = row.get(kr_field, "")
                if isinstance(value, str):
                    value = value.strip()
                if value:
                    mapped[db_col] = value

        return mapped if mapped.get("pnu") else None

    def get_params_interactive(self) -> dict[str, Any]:
        """CLI에서 SHP 파일 경로를 입력받습니다."""
        file_path = inquirer.filepath(
            message="GIS건물통합정보 SHP 파일 경로:",
            validate=lambda p: Path(p).exists() and Path(p).suffix == ".shp",
            invalid_message="유효한 SHP 파일 경로를 입력하세요.",
        ).execute()

        return {"file_path": file_path}

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(float(str(value).replace(",", "")))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(str(value).replace(",", ""))
        except (ValueError, TypeError):
            return None


Registry.register(GisBuildingIntegratedProcessor())
