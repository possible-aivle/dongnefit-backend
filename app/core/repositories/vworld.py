"""VWorld geocoding client (async)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from app.config import settings


AddressType = Literal["ROAD", "PARCEL"]


@dataclass(frozen=True)
class GeoCoordResult:
    ok: bool
    status: str | None = None
    address: str | None = None
    address_type: AddressType | None = None
    lat: float | None = None
    lng: float | None = None
    refined_text: str | None = None
    raw: Any | None = None
    error: str | None = None


class VWorldClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.vworld.kr",
        address_path: str = "/req/address",
        timeout_sec: float = 10.0,
    ):
        self.api_key = api_key or settings.vworld_api_key
        if not self.api_key:
            raise ValueError("VWorld API 키가 없습니다. settings.vworld_api_key 를 설정하세요.")
        self.base_url = base_url.rstrip("/")
        self.address_path = address_path
        self.timeout_sec = float(timeout_sec)

    async def get_coord(
        self,
        *,
        address: str,
        address_type: AddressType = "ROAD",
        crs: str = "epsg:4326",
        refine: bool = True,
        simple: bool = False,
        fmt: str = "json",
        version: str = "2.0",
    ) -> GeoCoordResult:
        addr = str(address or "").strip()
        if not addr:
            return GeoCoordResult(ok=False, error="address is empty")

        at = str(address_type or "").strip().upper()
        if at not in ("ROAD", "PARCEL"):
            return GeoCoordResult(ok=False, error=f"address_type must be ROAD or PARCEL (got {address_type})")

        url = f"{self.base_url}{self.address_path}"
        params = {
            "service": "address",
            "request": "getcoord",
            "version": version,
            "crs": crs,
            "address": addr,
            "refine": "true" if refine else "false",
            "simple": "true" if simple else "false",
            "format": fmt,
            "type": at.lower(),
            "key": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
        except Exception as e:
            return GeoCoordResult(ok=False, error=f"HTTP error: {e}")

        if fmt.lower() != "json":
            return GeoCoordResult(ok=False, error="Only json format is supported in this client.")

        try:
            data = resp.json()
        except Exception as e:
            return GeoCoordResult(ok=False, error=f"JSON parse error: {e}", raw=resp.text)

        root: dict[str, Any] | None = None
        if isinstance(data, dict):
            resp_obj = data.get("response")
            root = resp_obj if isinstance(resp_obj, dict) else data

        status = root.get("status") if isinstance(root, dict) else None
        if status != "OK":
            err = None
            if isinstance(root, dict):
                err_obj = root.get("error") or {}
                if isinstance(err_obj, dict):
                    err = err_obj.get("text") or err_obj.get("code")
            return GeoCoordResult(ok=False, status=status or None, address=addr, address_type=at, raw=data, error=err or "NOT_OK")

        try:
            result = root.get("result", {}) if isinstance(root, dict) else {}
            point = result.get("point", {}) if isinstance(result, dict) else {}
            lng = float(point.get("x")) if point.get("x") is not None else None
            lat = float(point.get("y")) if point.get("y") is not None else None
        except Exception:
            lng = None
            lat = None

        refined_text = None
        if isinstance(root, dict):
            refined = root.get("refined")
            if isinstance(refined, dict):
                refined_text = refined.get("text")

        if lat is None or lng is None:
            return GeoCoordResult(ok=False, status=status or None, address=addr, address_type=at, raw=data, error="Missing point.x/point.y")

        return GeoCoordResult(
            ok=True,
            status=status,
            address=addr,
            address_type=at,
            lat=lat,
            lng=lng,
            refined_text=refined_text,
            raw=data,
        )

    async def get_rivers_near(
        self,
        lat: float,
        lng: float,
        radius_km: float = 3.0,
        size: int = 100,
        crs: str = "EPSG:4326",
    ) -> list[dict[str, Any]]:
        """VWorld 하천망(LT_C_WKMSTRM) API로 반경 내 하천 Feature 목록을 조회합니다."""
        deg_lat = radius_km / 111.0
        deg_lng = radius_km / (111.0 * math.cos(math.radians(lat)))
        geom_filter = (
            f"BOX({lng - deg_lng:.6f},{lat - deg_lat:.6f},"
            f"{lng + deg_lng:.6f},{lat + deg_lat:.6f})"
        )

        url = f"{self.base_url}/req/data"
        params = {
            "service": "data",
            "request": "GetFeature",
            "data": "LT_C_WKMSTRM",
            "key": self.api_key,
            "geomFilter": geom_filter,
            "format": "json",
            "crs": crs,
            "size": size,
            "page": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        response = data.get("response", data)
        if response.get("status") != "OK":
            return []

        result = response.get("result", {})
        feature_collection = result.get("featureCollection", {})
        return feature_collection.get("features", []) or []


