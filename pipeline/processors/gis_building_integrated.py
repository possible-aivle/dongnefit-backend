"""GIS건물통합정보 프로세서 (AL_D010).

SHP 파일 기반 건물 공간 + 속성 통합 데이터 프로세서.
"""

from pathlib import Path
from typing import Any

from InquirerPy import inquirer
from rich.console import Console

from app.models.enums import PublicDataType
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
        """SHP 파일을 읽어 raw dict 리스트를 반환합니다."""
        try:
            import fiona
        except ImportError:
            console.print("[red]fiona 패키지가 필요합니다: uv add fiona[/]")
            return []

        file_path = Path(params["file_path"])
        if not file_path.exists():
            console.print(f"[red]파일을 찾을 수 없습니다: {file_path}[/]")
            return []

        rows: list[dict] = []
        with fiona.open(file_path) as src:
            for feature in src:
                row: dict[str, Any] = dict(feature.get("properties", {}))
                geom = feature.get("geometry")
                if geom:
                    row["__geometry__"] = dict(geom)
                rows.append(row)

        console.print(f"  SHP 읽기 완료: {len(rows)}건")
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

            # geometry (GeoJSON)
            mapped["geometry"] = row.pop("__geometry__", None)

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
