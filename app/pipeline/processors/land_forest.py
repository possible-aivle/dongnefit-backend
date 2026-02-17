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
        "지목명": "jimok",
        "지목코드": "jimok_code",
        "면적": "area",
        "소유구분명": "ownership",
        "소유구분코드": "ownership_code",
        "소유(공유)인수": "owner_count",
    }

    def transform_row(self, mapped: dict[str, Any], raw_row: dict) -> dict[str, Any] | None:
        pnu = self._extract_pnu(raw_row)
        if not pnu:
            return None

        mapped["pnu"] = pnu
        mapped["area"] = self._safe_float(mapped.get("area"))
        mapped["owner_count"] = self._safe_int(mapped.get("owner_count"))
        mapped.pop("data_base_date", None)

        return mapped


Registry.register(LandForestProcessor())
