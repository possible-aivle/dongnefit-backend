"""도로중심선 프로세서.

(연속수치지형도)도로중심선 SHP → road_center_lines 테이블.
"""

from pathlib import Path
from typing import Any

from rich.console import Console

from app.models.enums import PublicDataType
from app.pipeline.file_utils import (
    cleanup_temp_dir,
    extract_zip,
    find_shp_in_dir,
    find_zip_files_by_province_name,
    geojson_to_wkt,
    read_shp_features,
)
from app.pipeline.processors.base import BaseProcessor, ProcessResult
from app.pipeline.regions import PROVINCE_FILE_NAME_MAP
from app.pipeline.registry import Registry

console = Console()

PUBLIC_DATA_DIR = Path(__file__).parent.parent / "public_data"


class RoadCenterLineProcessor(BaseProcessor):
    """도로중심선 SHP 프로세서.

    UFID → source_id, NAME/RDNM → road_name, geometry → geometry.
    """

    name = "road_center_line"
    description = "도로중심선 (연속수치지형도)"
    data_type = PublicDataType.ROAD_CENTER_LINE

    async def collect(self, params: dict[str, Any]) -> list[dict]:
        data_dir = PUBLIC_DATA_DIR / "도로중심선"
        if not data_dir.exists():
            console.print(f"[red]디렉토리 없음: {data_dir}[/]")
            return []

        province_names = params.get("province_names")

        if province_names:
            zip_files = find_zip_files_by_province_name(
                data_dir, set(province_names)
            )
        else:
            zip_files = sorted(data_dir.glob("*.zip"))

        if not zip_files:
            console.print("[yellow]대상 도로중심선 ZIP 파일이 없습니다.[/]")
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

                # 도로중심선은 행정경계 코드 필터가 어려움 (PNU 없음)
                # sgg_prefixes가 있으면 전체 읽고 후처리에서 필터링
                features = read_shp_features(shp_path)
                rows.extend(features)
                console.print(f"    {len(features)}건 읽기 완료")
            finally:
                cleanup_temp_dir(tmp_dir)

        console.print(f"  도로중심선 총 읽기 완료: {len(rows)}건")
        return rows

    def transform(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for row in raw_data:
            source_id = str(
                row.get("UFID", row.get("A0", row.get("ID", "")))
            ).strip()
            road_name = str(
                row.get("NAME", row.get("RDNM", row.get("RN", row.get("A1", ""))))
            ).strip() or None

            if not source_id:
                continue

            records.append({
                "source_id": source_id[:200],
                "road_name": road_name[:200] if road_name else None,
                "geometry": geojson_to_wkt(row.pop("__geometry__", None)),
            })

        console.print(f"  변환 완료: {len(records)}건")
        return records

    def get_params_interactive(self) -> dict[str, Any]:
        from InquirerPy import inquirer

        data_dir = PUBLIC_DATA_DIR / "도로중심선"
        files = sorted(data_dir.glob("*.zip"))
        choices = [{"name": f.name, "value": f.name} for f in files]

        if not choices:
            console.print("[yellow]도로중심선 ZIP 파일이 없습니다.[/]")
            return {}

        selected = inquirer.checkbox(
            message="처리할 파일 선택 (Space 선택, Enter 확인, 미선택시 전체):",
            choices=choices,
        ).execute()

        if selected:
            province_names = set()
            for fname in selected:
                for pname in PROVINCE_FILE_NAME_MAP:
                    if pname in fname:
                        province_names.add(pname)
                        break
            return {"province_names": list(province_names)}

        return {}

    async def load(self, records: list[dict[str, Any]]) -> ProcessResult:
        """도로중심선은 중복키 없이 INSERT."""
        from app.database import async_session_maker
        from app.pipeline.loader import bulk_insert

        async with async_session_maker() as session:
            count = await bulk_insert(
                session, "road_center_lines", records, batch_size=2000
            )

        return ProcessResult(inserted=count)


Registry.register(RoadCenterLineProcessor())
