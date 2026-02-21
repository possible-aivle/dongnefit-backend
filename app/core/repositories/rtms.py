"""RTMS (국토교통부 실거래가) client (async, Settings-based)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import unquote

import httpx

from app.config import settings
from app.core.repositories.xml import parse_xml_to_dict, rtms_extract_items, rtms_raise_for_error

RtmsKind = Literal[
    "apt_trade",
    "apt_trade_dev",
    "apt_rent",
    "silv_trade",
    "rh_trade",
    "rh_rent",
    "sh_trade",
    "sh_rent",
    "offi_trade",
    "offi_rent",
    "land_trade",
    "nrg_trade",
    "ind_trade",
]


RTMS_ENDPOINTS: dict[RtmsKind, tuple[str, str]] = {
    # (SERVICE, OPERATION)
    "apt_trade": ("RTMSDataSvcAptTrade", "getRTMSDataSvcAptTrade"),
    "apt_trade_dev": ("RTMSDataSvcAptTradeDev", "getRTMSDataSvcAptTradeDev"),
    "apt_rent": ("RTMSDataSvcAptRent", "getRTMSDataSvcAptRent"),
    "silv_trade": ("RTMSDataSvcSilvTrade", "getRTMSDataSvcSilvTrade"),
    "rh_trade": ("RTMSDataSvcRHTrade", "getRTMSDataSvcRHTrade"),
    "rh_rent": ("RTMSDataSvcRHRent", "getRTMSDataSvcRHRent"),
    "sh_trade": ("RTMSDataSvcSHTrade", "getRTMSDataSvcSHTrade"),
    "sh_rent": ("RTMSDataSvcSHRent", "getRTMSDataSvcSHRent"),
    "offi_trade": ("RTMSDataSvcOffiTrade", "getRTMSDataSvcOffiTrade"),
    "offi_rent": ("RTMSDataSvcOffiRent", "getRTMSDataSvcOffiRent"),
    "land_trade": ("RTMSDataSvcLandTrade", "getRTMSDataSvcLandTrade"),
    "nrg_trade": ("RTMSDataSvcNrgTrade", "getRTMSDataSvcNrgTrade"),
    "ind_trade": ("RTMSDataSvcIndTrade", "getRTMSDataSvcIndTrade"),
}


@dataclass(frozen=True)
class RtmsResponse:
    """Parsed RTMS response."""

    raw: dict[str, Any]
    items: list[dict[str, Any]]


class RtmsClient:
    """Async RTMS client using `httpx`."""

    def __init__(
        self,
        *,
        base_url: str = "https://apis.data.go.kr/1613000",
        api_key: str | None = None,
        timeout_sec: float = 10.0,
        max_retries: int = 2,
        user_agent: str = "dongnefit-backend/rtms",
    ):
        key = api_key or settings.data_go_kr_api_decode_key or settings.data_go_kr_api_encode_key
        if not key:
            raise ValueError(
                "RTMS 호출을 위한 data.go.kr API 키가 없습니다. settings.data_go_kr_api_decode_key 를 설정하세요."
            )

        # data.go.kr 키는 percent-encoded로 들어오는 경우가 있어 decode 보정
        self.api_key = unquote(key) if "%" in key else key
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = float(timeout_sec)
        self.max_retries = max(0, int(max_retries))
        self.user_agent = user_agent

    async def fetch(
        self,
        kind: RtmsKind,
        *,
        lawd_cd: str,
        deal_ymd: str,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> RtmsResponse:
        if kind not in RTMS_ENDPOINTS:
            raise ValueError(f"Unknown RTMS kind: {kind}")
        service, operation = RTMS_ENDPOINTS[kind]

        url = f"{self.base_url}/{service}/{operation}"
        params = {
            "serviceKey": self.api_key,
            "LAWD_CD": str(lawd_cd),
            "DEAL_YMD": str(deal_ymd),
            "pageNo": str(int(page_no)),
            "numOfRows": str(int(num_of_rows)),
        }

        headers = {"user-agent": self.user_agent}
        last_err: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                    resp = await client.get(url, params=params, headers=headers)
                    resp.raise_for_status()
                parsed = parse_xml_to_dict(resp.content)
                rtms_raise_for_error(parsed)
                return RtmsResponse(raw=parsed, items=rtms_extract_items(parsed))
            except Exception as e:
                last_err = e
                if attempt >= self.max_retries:
                    raise

        raise last_err or RuntimeError("RTMS request failed")
