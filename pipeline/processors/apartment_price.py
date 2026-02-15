"""공동주택가격정보 프로세서 (AL_D167)."""

from typing import Any

from app.models.enums import PublicDataType
from pipeline.processors.vworld_csv import VworldCsvProcessor
from pipeline.registry import Registry


class ApartmentPriceProcessor(VworldCsvProcessor):
    """공동주택가격정보 CSV 프로세서."""

    name = "apartment_price"
    description = "공동주택가격정보 (AL_D167)"
    data_type = PublicDataType.APARTMENT_PRICE

    COLUMN_MAP: dict[str, str] = {
        "고유번호": "pnu",
        "기준년도": "base_year",
        "공동주택구분명": "apt_type_name",
        "공동주택명": "apt_name",
        "동명": "dong_name",
        "호명": "ho_name",
        "전용면적": "exclusive_area",
        "공시가격": "official_price",
    }

    def transform_row(self, mapped: dict[str, Any], raw_row: dict) -> dict[str, Any] | None:
        pnu = self._extract_pnu(raw_row)
        if not pnu:
            return None

        mapped["pnu"] = pnu
        mapped["base_year"] = self._safe_int(mapped.get("base_year")) or 0
        mapped["exclusive_area"] = self._safe_float(mapped.get("exclusive_area"))
        mapped["official_price"] = self._safe_int(mapped.get("official_price"))

        mapped["raw_data"] = raw_row
        return mapped


Registry.register(ApartmentPriceProcessor())
