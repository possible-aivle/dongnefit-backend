"""건축물대장 프로세서 (표제부, 총괄표제부, 층별개요, 전유공용면적, 부속지번).

공공데이터포털 대용량 txt 파일 기반 프로세서.
파이프(|) 구분자, 인덱스 기반 컬럼 매핑.
"""

from pathlib import Path
from typing import Any

from rich.console import Console

from app.models.enums import PublicDataType
from pipeline.parsing import safe_float, safe_int
from pipeline.processors.base import BaseProcessor, ProcessResult
from pipeline.registry import Registry

console = Console()


class BuildingRegisterTxtProcessor(BaseProcessor):
    """건축물대장 txt 파일 공통 베이스 프로세서.

    서브클래스에서 정의해야 하는 속성:
        - name, description, data_type
        - COLUMN_INDICES: dict[int, str] - txt 컬럼 인덱스 → DB 컬럼명 매핑
        - PNU_INDICES: tuple[int, int, int, int, int] - (시군구, 법정동, 대지구분, 번, 지) 인덱스

    선택적 오버라이드:
        - transform_row(mapped, fields) - 행별 추가 변환
    """

    COLUMN_INDICES: dict[int, str] = {}
    PNU_INDICES: tuple[int, int, int, int, int] = (0, 0, 0, 0, 0)

    # 시군구코드 필드 인덱스 (PNU_INDICES의 첫 번째: 시군구)
    SGG_FIELD_INDEX: int = 0

    async def collect(self, params: dict[str, Any]) -> list[dict]:
        """txt 파일을 읽어 raw 필드 리스트를 반환합니다.

        sgg_prefixes가 params에 포함되면 시군구코드로 필터링합니다.
        """
        file_path = Path(params["file_path"])
        if not file_path.exists():
            console.print(f"[red]파일을 찾을 수 없습니다: {file_path}[/]")
            return []

        sgg_prefixes: list[str] | None = params.get("sgg_prefixes")
        sgg_idx = self.PNU_INDICES[0]  # 시군구 코드 필드 인덱스

        rows: list[dict] = []
        for encoding in ("cp949", "utf-8", "utf-8-sig"):
            try:
                with file_path.open(encoding=encoding) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        fields = line.split("|")

                        # 시군구 필터링
                        if sgg_prefixes and sgg_idx < len(fields):
                            sgg_val = fields[sgg_idx].strip()
                            if not any(sgg_val.startswith(p) for p in sgg_prefixes):
                                continue

                        rows.append({"__fields__": fields})
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if not rows:
            console.print("[yellow]파일에서 데이터를 읽을 수 없습니다.[/]")
            return []

        console.print(f"  txt 읽기 완료: {len(rows)}행")
        return rows

    def transform(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """txt raw 데이터를 DB 컬럼에 맞게 변환합니다."""
        records: list[dict[str, Any]] = []
        errors = 0

        for row in raw_data:
            fields = row["__fields__"]
            try:
                mapped = self._map_fields(fields)
                if mapped is None:
                    errors += 1
                    continue

                result = self.transform_row(mapped, fields)
                if result is not None:
                    records.append(result)
            except (IndexError, ValueError):
                errors += 1
                continue

        console.print(f"  변환 완료: {len(records)}건 (에러: {errors}건)")
        return records

    def _map_fields(self, fields: list[str]) -> dict[str, Any] | None:
        """인덱스 기반으로 필드를 DB 컬럼에 매핑합니다."""
        mapped: dict[str, Any] = {}

        for idx, db_col in self.COLUMN_INDICES.items():
            if idx < len(fields):
                value = fields[idx].strip()
                mapped[db_col] = value if value else None
            else:
                mapped[db_col] = None

        return mapped

    def _build_pnu(self, fields: list[str]) -> str | None:
        """시군구+법정동+대지구분+번+지에서 PNU(19자리)를 생성합니다."""
        si, bj, dg, bon, bu = self.PNU_INDICES
        try:
            sigungu = (fields[si] if si < len(fields) else "").strip()
            bjdong = (fields[bj] if bj < len(fields) else "").strip()
            daeji = (fields[dg] if dg < len(fields) else "").strip()
            bon_val = (fields[bon] if bon < len(fields) else "").strip()
            bu_val = (fields[bu] if bu < len(fields) else "").strip()

            if not sigungu or not bjdong:
                return None

            pnu = (
                sigungu.zfill(5)
                + bjdong.zfill(5)
                + daeji.zfill(1)
                + bon_val.zfill(4)
                + bu_val.zfill(4)
            )
            return pnu if len(pnu) == 19 else None
        except (IndexError, ValueError):
            return None

    def transform_row(
        self, mapped: dict[str, Any], fields: list[str]
    ) -> dict[str, Any] | None:
        """행별 추가 변환 (서브클래스에서 오버라이드)."""
        return mapped

    def get_params_interactive(self) -> dict[str, Any]:
        """CLI에서 txt 파일 경로를 입력받습니다."""
        from InquirerPy import inquirer

        file_path = inquirer.filepath(
            message=f"{self.description} txt 파일 경로:",
            validate=lambda p: Path(p).exists() and Path(p).suffix == ".txt",
            invalid_message="유효한 txt 파일 경로를 입력하세요.",
        ).execute()

        return {"file_path": file_path}

    async def load(self, records: list[dict[str, Any]]) -> ProcessResult:
        """변환된 데이터를 DB에 적재합니다.

        대용량 txt 데이터는 배치 사이즈를 크게 설정합니다.
        """
        from app.database import async_session_maker
        from pipeline.loader import bulk_upsert

        async with async_session_maker() as session:
            result = await bulk_upsert(session, self.data_type, records, batch_size=2000)

        return result

    _safe_int = staticmethod(safe_int)
    _safe_float = staticmethod(safe_float)


# ── 표제부 프로세서 ──


class BuildingRegisterHeaderProcessor(BuildingRegisterTxtProcessor):
    """건축물대장 표제부 프로세서 (mart_djy_03.txt)."""

    name = "building_register_header"
    description = "건축물대장 표제부"
    data_type = PublicDataType.BUILDING_REGISTER_HEADER

    # PNU 구성 인덱스: (시군구=8, 법정동=9, 대지구분=10, 번=11, 지=12)
    PNU_INDICES = (8, 9, 10, 11, 12)

    # 핵심 컬럼만 매핑 (인덱스 → DB 컬럼)
    COLUMN_INDICES: dict[int, str] = {
        0: "mgm_bldrgst_pk",
        7: "building_name",        # 건물명
        25: "site_area",           # 대지면적
        26: "building_area",       # 건축면적
        27: "bcr",                 # 건폐율
        28: "total_floor_area",    # 연면적
        30: "far",                 # 용적률
        32: "structure_name",      # 구조코드명
        35: "main_use_name",       # 주용도코드명
        40: "household_count",     # 세대수
        42: "height",              # 높이
        43: "above_ground_floors", # 지상층수
        44: "underground_floors",  # 지하층수
        60: "approval_date",       # 사용승인일
    }

    def transform_row(
        self, mapped: dict[str, Any], fields: list[str]
    ) -> dict[str, Any] | None:
        pnu = self._build_pnu(fields)
        if not pnu:
            return None

        mapped["pnu"] = pnu
        mapped["site_area"] = self._safe_float(mapped.get("site_area"))
        mapped["building_area"] = self._safe_float(mapped.get("building_area"))
        mapped["bcr"] = self._safe_float(mapped.get("bcr"))
        mapped["total_floor_area"] = self._safe_float(mapped.get("total_floor_area"))
        mapped["far"] = self._safe_float(mapped.get("far"))
        mapped["height"] = self._safe_float(mapped.get("height"))
        mapped["household_count"] = self._safe_int(mapped.get("household_count"))
        mapped["above_ground_floors"] = self._safe_int(mapped.get("above_ground_floors"))
        mapped["underground_floors"] = self._safe_int(mapped.get("underground_floors"))

        return mapped


# ── 총괄표제부 프로세서 ──


class BuildingRegisterGeneralProcessor(BuildingRegisterTxtProcessor):
    """건축물대장 총괄표제부 프로세서 (mart_djy_02.txt)."""

    name = "building_register_general"
    description = "건축물대장 총괄표제부"
    data_type = PublicDataType.BUILDING_REGISTER_GENERAL

    # PNU 구성 인덱스: (시군구=10, 법정동=11, 대지구분=12, 번=13, 지=14)
    PNU_INDICES = (10, 11, 12, 13, 14)

    COLUMN_INDICES: dict[int, str] = {
        0: "mgm_bldrgst_pk",
        9: "building_name",        # 건물명
        24: "site_area",           # 대지면적
        25: "building_area",       # 건축면적
        26: "bcr",                 # 건폐율
        27: "total_floor_area",    # 연면적
        29: "far",                 # 용적률
        31: "main_use_name",       # 주용도코드명
        33: "household_count",     # 세대수
        38: "total_parking",       # 총주차수
        49: "approval_date",       # 사용승인일
    }

    def transform_row(
        self, mapped: dict[str, Any], fields: list[str]
    ) -> dict[str, Any] | None:
        pnu = self._build_pnu(fields)
        if not pnu:
            return None

        mapped["pnu"] = pnu
        mapped["site_area"] = self._safe_float(mapped.get("site_area"))
        mapped["building_area"] = self._safe_float(mapped.get("building_area"))
        mapped["bcr"] = self._safe_float(mapped.get("bcr"))
        mapped["total_floor_area"] = self._safe_float(mapped.get("total_floor_area"))
        mapped["far"] = self._safe_float(mapped.get("far"))
        mapped["household_count"] = self._safe_int(mapped.get("household_count"))
        mapped["total_parking"] = self._safe_int(mapped.get("total_parking"))

        return mapped


# ── 층별개요 프로세서 ──


class BuildingRegisterFloorDetailProcessor(BuildingRegisterTxtProcessor):
    """건축물대장 층별개요 프로세서 (mart_djy_04.txt)."""

    name = "building_register_floor_detail"
    description = "건축물대장 층별개요"
    data_type = PublicDataType.BUILDING_REGISTER_FLOOR_DETAIL

    # PNU 구성 인덱스: (시군구=4, 법정동=5, 대지구분=6, 번=7, 지=8)
    PNU_INDICES = (4, 5, 6, 7, 8)

    COLUMN_INDICES: dict[int, str] = {
        0: "mgm_bldrgst_pk",
        19: "floor_type_name",     # 층구분코드명
        20: "floor_no",            # 층번호
        26: "main_use_name",       # 주용도코드명
        28: "area",                # 면적
    }

    def transform_row(
        self, mapped: dict[str, Any], fields: list[str]
    ) -> dict[str, Any] | None:
        pnu = self._build_pnu(fields)
        if not pnu:
            return None

        mapped["pnu"] = pnu
        mapped["floor_no"] = self._safe_int(mapped.get("floor_no"))
        mapped["area"] = self._safe_float(mapped.get("area"))

        return mapped


# ── 전유공용면적 프로세서 ──


class BuildingRegisterAreaProcessor(BuildingRegisterTxtProcessor):
    """건축물대장 전유공용면적 프로세서 (mart_djy_06.txt).

    세대별 전유면적/공용면적을 관리하여 공급면적 도출에 사용합니다.
    공급면적 = 전유면적(주건축물) + 공용면적(주건축물)
    """

    name = "building_register_area"
    description = "건축물대장 전유공용면적"
    data_type = PublicDataType.BUILDING_REGISTER_AREA

    # PNU 구성 인덱스: (시군구=8, 법정동=9, 대지구분=10, 번=11, 지=12)
    PNU_INDICES = (8, 9, 10, 11, 12)

    COLUMN_INDICES: dict[int, str] = {
        0: "mgm_bldrgst_pk",
        21: "dong_name",           # 동명
        22: "ho_name",             # 호명
        25: "floor_no",            # 층번호
        26: "exclu_common_type",   # 전유공용구분코드 (1:전유, 2:공용)
        37: "area",                # 면적
    }

    def transform_row(
        self, mapped: dict[str, Any], fields: list[str]
    ) -> dict[str, Any] | None:
        pnu = self._build_pnu(fields)
        if not pnu:
            return None

        mapped["pnu"] = pnu
        mapped["floor_no"] = self._safe_int(mapped.get("floor_no"))
        mapped["area"] = self._safe_float(mapped.get("area"))

        return mapped


# ── 부속지번 프로세서 ──


class BuildingRegisterAncillaryLotProcessor(BuildingRegisterTxtProcessor):
    """건축물대장 부속지번 프로세서 (mart_djy_05.txt)."""

    name = "building_register_ancillary_lot"
    description = "건축물대장 부속지번"
    data_type = PublicDataType.BUILDING_REGISTER_ANCILLARY_LOT

    # PNU 구성 인덱스 (본 건물): (시군구=8, 법정동=9, 대지구분=10, 번=11, 지=12)
    PNU_INDICES = (8, 9, 10, 11, 12)
    # 부속지번 PNU 구성 인덱스
    ATCH_PNU_INDICES = (23, 24, 25, 26, 27)

    COLUMN_INDICES: dict[int, str] = {
        0: "mgm_bldrgst_pk",
        32: "created_date",        # 생성일자
    }

    def transform_row(
        self, mapped: dict[str, Any], fields: list[str]
    ) -> dict[str, Any] | None:
        pnu = self._build_pnu(fields)
        if not pnu:
            return None

        # 부속지번 PNU 생성
        atch_pnu = self._build_atch_pnu(fields)

        mapped["pnu"] = pnu
        mapped["atch_pnu"] = atch_pnu

        return mapped

    def _build_atch_pnu(self, fields: list[str]) -> str | None:
        """부속지번에서 PNU를 생성합니다."""
        si, bj, dg, bon, bu = self.ATCH_PNU_INDICES
        try:
            sigungu = (fields[si] if si < len(fields) else "").strip()
            bjdong = (fields[bj] if bj < len(fields) else "").strip()
            daeji = (fields[dg] if dg < len(fields) else "").strip()
            bon_val = (fields[bon] if bon < len(fields) else "").strip()
            bu_val = (fields[bu] if bu < len(fields) else "").strip()

            if not sigungu or not bjdong:
                return None

            pnu = (
                sigungu.zfill(5)
                + bjdong.zfill(5)
                + daeji.zfill(1)
                + bon_val.zfill(4)
                + bu_val.zfill(4)
            )
            return pnu if len(pnu) == 19 else None
        except (IndexError, ValueError):
            return None


# ── 레지스트리 등록 ──

Registry.register(BuildingRegisterHeaderProcessor())
Registry.register(BuildingRegisterGeneralProcessor())
Registry.register(BuildingRegisterFloorDetailProcessor())
Registry.register(BuildingRegisterAreaProcessor())
Registry.register(BuildingRegisterAncillaryLotProcessor())
