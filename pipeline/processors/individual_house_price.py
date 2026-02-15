"""개별주택가격정보 프로세서 (AL_D169)."""

from typing import Any

from app.models.enums import PublicDataType
from pipeline.processors.vworld_csv import VworldCsvProcessor
from pipeline.registry import Registry


class IndividualHousePriceProcessor(VworldCsvProcessor):
    """개별주택가격정보 CSV 프로세서."""

    name = "individual_house_price"
    description = "개별주택가격정보 (AL_D169)"
    data_type = PublicDataType.INDIVIDUAL_HOUSE_PRICE

    COLUMN_MAP: dict[str, str] = {
        "고유번호": "pnu",
        "법정동코드": "bjd_code",
        "지번": "jibun",
        "기준년도": "base_year",
        "기준월": "base_month",
        "건물산정연면적": "building_floor_area",
        "토지대장면적": "land_area",
        "건물전체연면적": "total_floor_area",
        "주택가격": "house_price",
        "표준지여부": "is_standard",
        "데이터기준일자": "data_base_date",
    }

    def transform_row(self, mapped: dict[str, Any], raw_row: dict) -> dict[str, Any] | None:
        pnu = self._extract_pnu(raw_row)
        if not pnu:
            return None

        mapped["pnu"] = pnu
        mapped["base_year"] = self._safe_int(mapped.get("base_year")) or 0
        mapped["base_month"] = self._safe_int(mapped.get("base_month"))
        mapped["building_floor_area"] = self._safe_float(mapped.get("building_floor_area"))
        mapped["land_area"] = self._safe_float(mapped.get("land_area"))
        mapped["total_floor_area"] = self._safe_float(mapped.get("total_floor_area"))
        mapped["house_price"] = self._safe_int(mapped.get("house_price"))

        mapped["raw_data"] = raw_row
        return mapped


Registry.register(IndividualHousePriceProcessor())
