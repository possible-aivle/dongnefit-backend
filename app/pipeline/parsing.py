"""공통 파싱 유틸리티 함수."""

from typing import Any


def safe_int(value: Any) -> int | None:
    """안전한 int 변환."""
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (ValueError, TypeError):
        return None


def safe_float(value: Any) -> float | None:
    """안전한 float 변환."""
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return None
