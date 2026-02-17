"""토지특성정보 프로세서 (AL_D195)."""

from typing import Any

from app.models.enums import PublicDataType
from app.pipeline.processors.vworld_csv import VworldCsvProcessor
from app.pipeline.registry import Registry


class LandCharacteristicProcessor(VworldCsvProcessor):
    """토지특성정보 CSV 프로세서."""

    name = "land_characteristic"
    description = "토지특성정보 (AL_D195)"
    data_type = PublicDataType.LAND_CHARACTERISTIC

    COLUMN_MAP: dict[str, str] = {
        "고유번호": "pnu",
        "지목명": "jimok",
        "토지면적": "land_area",
        "용도지역명1": "use_zone",
        "토지이용상황": "land_use",
        "공시지가": "official_price",
    }

    def transform_row(self, mapped: dict[str, Any], raw_row: dict) -> dict[str, Any] | None:
        pnu = self._extract_pnu(raw_row)
        if not pnu:
            return None

        mapped["pnu"] = pnu
        mapped["land_area"] = self._safe_float(mapped.get("land_area"))
        mapped["official_price"] = self._safe_int(mapped.get("official_price"))
        mapped.pop("data_base_date", None)

        return mapped


Registry.register(LandCharacteristicProcessor())
