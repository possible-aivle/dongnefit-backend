"""개별공시지가정보 프로세서 (AL_D151)."""

from typing import Any

from app.models.enums import PublicDataType
from app.pipeline.processors.vworld_csv import VworldCsvProcessor
from app.pipeline.registry import Registry


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
        "기준연도": "base_year",
        "공시지가": "price_per_sqm",
    }

    def transform_row(self, mapped: dict[str, Any], raw_row: dict) -> dict[str, Any] | None:
        pnu = self._extract_pnu(raw_row)
        if not pnu:
            return None

        mapped["pnu"] = pnu
        mapped["base_year"] = self._safe_int(mapped.get("base_year")) or 0
        mapped["price_per_sqm"] = self._safe_int(mapped.get("price_per_sqm"))

        return mapped

    def transform(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """1:N 레코드를 PNU별 JSONB 배열로 집계합니다."""
        records = super().transform(raw_data)
        return self._aggregate_jsonb(records, "official_prices")


Registry.register(OfficialLandPriceProcessor())
