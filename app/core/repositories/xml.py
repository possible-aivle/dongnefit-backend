"""XML helpers for public data APIs."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any


def xml_element_to_obj(element: ET.Element) -> Any:
    """Convert an XML element into nested dict/list/str."""
    if len(element) == 0:
        return element.text.strip() if element.text else ""

    result: dict[str, Any] = {}
    for child in list(element):
        child_data = xml_element_to_obj(child)
        if child.tag in result:
            if isinstance(result[child.tag], list):
                result[child.tag].append(child_data)
            else:
                result[child.tag] = [result[child.tag], child_data]
        else:
            result[child.tag] = child_data
    return result


def parse_xml_to_dict(xml_bytes: bytes | str) -> dict[str, Any]:
    """Parse RTMS-style XML into a dict with root tag as the top key."""
    if isinstance(xml_bytes, str):
        data = xml_bytes.encode("utf-8", errors="ignore")
    else:
        data = xml_bytes

    root = ET.fromstring(data)
    return {root.tag: xml_element_to_obj(root)}


def rtms_extract_items(rtms_dict: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract RTMS `response.body.items.item` into a list[dict]."""
    if not isinstance(rtms_dict, dict):
        return []

    response = rtms_dict.get("response")
    if not isinstance(response, dict):
        return []

    body = response.get("body")
    if not isinstance(body, dict):
        return []

    items_obj = body.get("items")
    if not isinstance(items_obj, dict):
        return []

    items = items_obj.get("item", [])
    if isinstance(items, list):
        return [it for it in items if isinstance(it, dict)]
    if isinstance(items, dict):
        return [items]
    return []


def rtms_raise_for_error(rtms_dict: dict[str, Any]) -> None:
    """Raise ValueError if RTMS response contains an error code/message."""
    response = rtms_dict.get("response")
    if not isinstance(response, dict):
        return
    header = response.get("header")
    if not isinstance(header, dict):
        return

    code = str(header.get("resultCode") or "").strip()
    msg = str(header.get("resultMsg") or "").strip()
    if code and code not in {"00", "000"}:
        raise ValueError(f"RTMS API 오류 ({code}): {msg or 'Unknown Error'}")


