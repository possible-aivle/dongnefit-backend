"""Agent-facing helpers for RTMS (실거래가)."""

from __future__ import annotations

from typing import Any

from app.core.public_data.lawd import LawdRepository
from app.core.public_data.rtms import RtmsClient


def _normalize_deal_ymd(deal_ymd: str) -> str:
    s = "".join(ch for ch in str(deal_ymd or "").strip() if ch.isdigit())
    if len(s) != 6:
        raise ValueError(f"DEAL_YMD는 YYYYMM 형식이어야 합니다 (got: {deal_ymd})")
    return s


class RtmsToolService:
    """Thin wrapper around `RtmsClient` for agent/services usage."""

    def __init__(self, *, client: RtmsClient | None = None, lawd_repo: LawdRepository | None = None):
        self.client = client or RtmsClient()
        self.lawd_repo = lawd_repo or LawdRepository()

    async def apt_trade_dev_by_region(
        self,
        *,
        region_name: str,
        deal_ymd: str,
        num_of_rows: int = 100,
    ) -> dict[str, Any]:
        """Fetch apt trade detail (AptTradeDev) items by region name."""
        lawd_cd = self.lawd_repo.resolve_code5(region_name)
        if not lawd_cd:
            return {"ok": False, "error": f"LAWD_CD를 찾을 수 없습니다: {region_name}", "region_name": region_name}

        ymd = _normalize_deal_ymd(deal_ymd)
        res = await self.client.fetch("apt_trade_dev", lawd_cd=lawd_cd, deal_ymd=ymd, num_of_rows=num_of_rows)
        return {
            "ok": True,
            "region_name": region_name,
            "lawd_cd": lawd_cd,
            "deal_ymd": ymd,
            "count": len(res.items),
            "items": res.items,
        }


