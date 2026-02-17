"""토지임야정보 프로세서 (AL_D003)."""

from typing import Any

from app.models.enums import PublicDataType
from app.pipeline.processors.vworld_csv import VworldCsvProcessor
from app.pipeline.registry import Registry


class LandForestProcessor(VworldCsvProcessor):
    """토지임야정보 CSV 프로세서."""

    name = "land_forest"
    description = "토지임야정보 (AL_D003)"
    data_type = PublicDataType.LAND_AND_FOREST_INFO

    COLUMN_MAP: dict[str, str] = {
        "고유번호": "pnu",
        "지목명": "jimok_name",
        "면적": "area",
        "소유구분명": "ownership_name",
        "소유(공유)인수": "owner_count",
        "데이터기준일자": "data_base_date",
    }

    def transform_row(self, mapped: dict[str, Any], raw_row: dict) -> dict[str, Any] | None:
        pnu = self._extract_pnu(raw_row)
        if not pnu:
            return None

        mapped["pnu"] = pnu
        mapped["area"] = self._safe_float(mapped.get("area"))
        mapped["owner_count"] = self._safe_int(mapped.get("owner_count"))

        # data_year 추출
        data_base_date = mapped.pop("data_base_date", "") or ""
        mapped["data_year"] = self._safe_int(data_base_date[:4]) or 0

        return mapped


Registry.register(LandForestProcessor())
