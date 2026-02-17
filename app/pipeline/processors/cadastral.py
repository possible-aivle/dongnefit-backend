"""연속지적도 프로세서.

연속지적도 SHP → lots 테이블.
파일: LSMD_CONT_LDREG_{province_name}.zip (시도 이름 기반 파일명).
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


class CadastralProcessor(BaseProcessor):
    """연속지적도 SHP 프로세서.

    PNU → pnu, geometry → geometry.
    """

    name = "cadastral"
    description = "연속지적도 (LSMD_CONT_LDREG)"
    data_type = PublicDataType.CONTINUOUS_CADASTRAL

    async def collect(self, params: dict[str, Any]) -> list[dict]:
        data_dir = PUBLIC_DATA_DIR / "연속지적도"
        if not data_dir.exists():
            console.print(f"[red]디렉토리 없음: {data_dir}[/]")
            return []

        sgg_prefixes = params.get("sgg_prefixes")
        province_names = params.get("province_names")

        # 대상 ZIP 파일 선정
        if province_names:
            zip_files = find_zip_files_by_province_name(
                data_dir, set(province_names)
            )
        else:
            zip_files = sorted(data_dir.glob("*.zip"))

        if not zip_files:
            console.print("[yellow]대상 연속지적도 ZIP 파일이 없습니다.[/]")
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

                features = read_shp_features(shp_path, sgg_prefixes, code_field="PNU")
                rows.extend(features)
                console.print(f"    {len(features)}건 읽기 완료")
            finally:
                cleanup_temp_dir(tmp_dir)

        console.print(f"  연속지적도 총 읽기 완료: {len(rows)}건")
        return rows

    def transform(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for row in raw_data:
            pnu = str(row.get("PNU", "")).strip()
            if not pnu or len(pnu) < 19:
                continue

            pnu = pnu[:19]

            records.append({
                "pnu": pnu,
                "geometry": geojson_to_wkt(row.pop("__geometry__", None)),
            })

        console.print(f"  변환 완료: {len(records)}건")
        return records

    def get_params_interactive(self) -> dict[str, Any]:
        from InquirerPy import inquirer

        # 파일 목록에서 시도 선택
        data_dir = PUBLIC_DATA_DIR / "연속지적도"
        files = sorted(data_dir.glob("*.zip"))
        choices = [{"name": f.name, "value": f.name} for f in files]

        if not choices:
            console.print("[yellow]연속지적도 ZIP 파일이 없습니다.[/]")
            return {}

        selected = inquirer.checkbox(
            message="처리할 파일 선택 (Space 선택, Enter 확인, 미선택시 전체):",
            choices=choices,
        ).execute()

        if selected:
            # 파일명에서 시도 이름 추출
            province_names = set()
            for fname in selected:
                for pname in PROVINCE_FILE_NAME_MAP:
                    if pname in fname:
                        province_names.add(pname)
                        break
            return {"province_names": list(province_names)}

        return {}

    async def load(self, records: list[dict[str, Any]]) -> ProcessResult:
        """연속지적도 대용량 데이터 적재 (배치 사이즈 증가)."""
        from app.database import async_session_maker
        from app.pipeline.loader import bulk_upsert

        async with async_session_maker() as session:
            result = await bulk_upsert(session, self.data_type, records, batch_size=2000)

        return result


Registry.register(CadastralProcessor())
