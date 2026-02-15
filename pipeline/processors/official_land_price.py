"""개별공시지가정보 프로세서 (AL_D151)."""

from datetime import date
from typing import Any

from app.models.enums import PublicDataType
from pipeline.processors.vworld_csv import VworldCsvProcessor
from pipeline.registry import Registry


class OfficialLandPriceProcessor(VworldCsvProcessor):
    """개별공시지가정보 CSV 프로세서.

    CSV 컬럼 (13개):
        고유번호, 법정동코드, 법정동명, 특수지구분코드, 특수지구분명,
        지번, 기준연도, 기준월, 공시지가, 공시일자, 표준지여부,
        데이터기준일자, 원천시도시군구코드
    """

    name = "official_land_price"
    description = "개별공시지가정보 (AL_D151)"
    data_type = PublicDataType.OFFICIAL_LAND_PRICE

    COLUMN_MAP: dict[str, str] = {
        "고유번호": "pnu",
        "법정동코드": "bjd_code",
        "법정동명": "bjd_name",
        "특수지구분코드": "special_land_code",
        "특수지구분명": "special_land_name",
        "지번": "jibun",
        "기준연도": "base_year",
        "기준월": "base_month",
        "공시지가": "price_per_sqm",
        "공시일자": "announcement_date",
        "표준지여부": "is_standard",
        "데이터기준일자": "data_base_date",
        "원천시도시군구코드": "source_sigungu_code",
    }

    def transform_row(self, mapped: dict[str, Any], raw_row: dict) -> dict[str, Any] | None:
        pnu = self._extract_pnu(raw_row)
        if not pnu:
            return None

        mapped["pnu"] = pnu
        mapped["base_year"] = self._safe_int(mapped.get("base_year")) or 0
        mapped["base_month"] = self._safe_int(mapped.get("base_month"))
        mapped["price_per_sqm"] = self._safe_int(mapped.get("price_per_sqm"))

        # 공시일자 → date 변환 (예: "2025-04-30")
        ann_date = mapped.get("announcement_date")
        if ann_date and isinstance(ann_date, str):
            try:
                mapped["announcement_date"] = date.fromisoformat(ann_date)
            except ValueError:
                mapped["announcement_date"] = None

        # 표준지여부 변환 (Y/N → bool)
        is_std = mapped.get("is_standard", "")
        if is_std in ("Y", "1"):
            mapped["is_standard"] = True
        elif is_std in ("N", "0"):
            mapped["is_standard"] = False
        else:
            mapped["is_standard"] = None

        mapped["raw_data"] = raw_row
        return mapped


Registry.register(OfficialLandPriceProcessor())
