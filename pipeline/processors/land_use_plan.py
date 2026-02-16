"""토지이용계획정보 프로세서 (AL_D155)."""

from typing import Any

from app.models.enums import PublicDataType
from pipeline.processors.vworld_csv import VworldCsvProcessor
from pipeline.registry import Registry


class LandUsePlanProcessor(VworldCsvProcessor):
    """토지이용계획정보 CSV 프로세서."""

    name = "land_use_plan"
    description = "토지이용계획정보 (AL_D155)"
    data_type = PublicDataType.LAND_USE_PLAN

    COLUMN_MAP: dict[str, str] = {
        "고유번호": "pnu",
        "용도지역지구명": "use_district_name",
        "데이터기준일자": "data_base_date",
    }

    def transform_row(self, mapped: dict[str, Any], raw_row: dict) -> dict[str, Any] | None:
        pnu = self._extract_pnu(raw_row)
        if not pnu:
            return None

        mapped["pnu"] = pnu

        # data_year 추출
        data_base_date = mapped.pop("data_base_date", "") or ""
        mapped["data_year"] = self._safe_int(data_base_date[:4]) or 0

        mapped["raw_data"] = raw_row
        return mapped


Registry.register(LandUsePlanProcessor())
