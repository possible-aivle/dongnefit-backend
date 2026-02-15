"""표준지공시지가정보 프로세서 (AL_D153)."""

from typing import Any

from app.models.enums import PublicDataType
from pipeline.processors.vworld_csv import VworldCsvProcessor
from pipeline.registry import Registry


class StandardLandPriceProcessor(VworldCsvProcessor):
    """표준지공시지가정보 CSV 프로세서."""

    name = "standard_land_price"
    description = "표준지공시지가정보 (AL_D153)"
    data_type = PublicDataType.STANDARD_LAND_PRICE

    COLUMN_MAP: dict[str, str] = {
        "고유번호": "pnu",
        "법정동코드": "bjd_code",
        "지번": "jibun",
        "기준년도": "base_year",
        "지목코드": "jimok_code",
        "지목명": "jimok_name",
        "토지면적": "land_area",
        "용도지역코드1": "use_zone_code",
        "용도지역명1": "use_zone_name",
        "토지이용상황코드": "land_use_code",
        "토지이용상황": "land_use_name",
        "공시지가": "official_price",
        "데이터기준일자": "data_base_date",
    }

    def transform_row(self, mapped: dict[str, Any], raw_row: dict) -> dict[str, Any] | None:
        pnu = self._extract_pnu(raw_row)
        if not pnu:
            return None

        mapped["pnu"] = pnu
        mapped["base_year"] = self._safe_int(mapped.get("base_year")) or 0
        mapped["land_area"] = self._safe_float(mapped.get("land_area"))
        mapped["official_price"] = self._safe_int(mapped.get("official_price"))

        mapped["raw_data"] = raw_row
        return mapped


Registry.register(StandardLandPriceProcessor())
