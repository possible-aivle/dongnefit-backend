"""토지소유정보 프로세서 (AL_D401)."""

from typing import Any

from app.models.enums import PublicDataType
from app.pipeline.processors.vworld_csv import VworldCsvProcessor
from app.pipeline.registry import Registry


class LandOwnershipProcessor(VworldCsvProcessor):
    """토지소유정보 CSV 프로세서."""

    name = "land_ownership"
    description = "토지소유정보 (AL_D401)"
    data_type = PublicDataType.LAND_OWNERSHIP

    COLUMN_MAP: dict[str, str] = {
        "고유번호": "pnu",
        "기준연월": "base_year_month",
        "공유인일련번호": "co_owner_seq",
        "소유구분": "ownership_type",
        "소유권변동원인": "ownership_change_reason",
        "소유권변동일자": "ownership_change_date",
        "공유인수": "owner_count",
    }

    def transform_row(self, mapped: dict[str, Any], raw_row: dict) -> dict[str, Any] | None:
        pnu = self._extract_pnu(raw_row)
        if not pnu:
            return None

        mapped["pnu"] = pnu
        mapped["co_owner_seq"] = mapped.get("co_owner_seq") or "000001"
        mapped["owner_count"] = self._safe_int(mapped.get("owner_count"))

        return mapped

    def transform(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """1:N 레코드를 PNU별 JSONB 배열로 집계합니다."""
        records = super().transform(raw_data)
        return self._aggregate_jsonb(records, "ownerships")


Registry.register(LandOwnershipProcessor())
