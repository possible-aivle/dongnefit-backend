"""Talk agent runner using RTMS/LAWD/VWorld tools.

This is a lightweight, tool-calling agent meant for API usage.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.config import settings
from app.core.agent.tools import LawdToolService, RtmsToolService, SchoolToolService
from app.core.public_data.vworld import VWorldClient


OpenAIRole = Literal["user", "assistant", "system"]


def _to_langchain_messages(messages: list[dict[str, Any]]) -> list[Any]:
    out: list[Any] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content") or ""
        if role == "system":
            out.append(SystemMessage(content=str(content)))
        elif role == "assistant":
            out.append(AIMessage(content=str(content)))
        else:
            out.append(HumanMessage(content=str(content)))
    return out


_PROMPT_FILE = Path(__file__).parents[3] / "prompts" / "talk" / "system_prompt.txt"

_DEFAULT_STYLE = "답변은 한국어로, 짧게 요약 후 근거를 bullet로 제시하세요."
_DEFAULT_TOOL_POLICY = "질문 해결에 필요한 경우에만 도구를 호출하세요. 도구 결과는 그대로 길게 붙여넣지 말고 핵심만 요약하세요."


def _build_system_prompt(context: dict[str, Any] | None, tool_names: list[str]) -> str:
    ctx = context or {}
    style = str(ctx.get("style") or _DEFAULT_STYLE)
    tool_policy = str(ctx.get("tool_policy") or _DEFAULT_TOOL_POLICY)

    if _PROMPT_FILE.exists():
        template = _PROMPT_FILE.read_text(encoding="utf-8")
        return template.format(
            now=datetime.now().strftime("%Y-%m-%d %H:%M"),
            style=style,
            tool_policy=tool_policy,
            tool_names=", ".join(tool_names),
        )

    # Fallback if file is missing
    return "\n".join(
        [
            "당신은 한국 부동산 데이터 도우미입니다.",
            f"- {style}",
            f"- {tool_policy}",
        ]
    )


def build_tools() -> list[Any]:
    lawd = LawdToolService()
    rtms = RtmsToolService()
    school = SchoolToolService()

    @tool("lawd_resolve_code")
    def lawd_resolve_code(region_name: str) -> dict[str, Any]:
        """지역명으로 5자리 법정동코드(LAWD_CD)를 찾습니다."""
        code = lawd.resolve_code5(region_name)
        return {"query": region_name, "lawd_cd": code, "found": bool(code)}

    @tool("lawd_search")
    def lawd_search(query: str, limit: int = 20) -> dict[str, Any]:
        """키워드로 법정동코드 후보를 검색합니다."""
        results = lawd.search(query, limit=limit)
        return {"query": query, "count": len(results), "results": results}

    @tool("rtms_apt_trade_detail")
    async def rtms_apt_trade_detail(region_name: str, deal_ymd: str, num_of_rows: int = 100) -> dict[str, Any]:
        """지역명+월(YYYYMM)로 아파트 매매 상세(AptTradeDev) 실거래가를 조회합니다."""
        return await rtms.apt_trade_dev_by_region(region_name=region_name, deal_ymd=deal_ymd, num_of_rows=num_of_rows)

    @tool("vworld_get_coord")
    async def vworld_get_coord(address: str, address_type: str = "ROAD") -> dict[str, Any]:
        """VWorld로 주소를 좌표(위도/경도)로 변환합니다."""
        client = VWorldClient()
        res = await client.get_coord(address=address, address_type=address_type)  # type: ignore[arg-type]
        return {
            "ok": res.ok,
            "address": res.address,
            "address_type": res.address_type,
            "lat": res.lat,
            "lng": res.lng,
            "status": res.status,
            "error": res.error,
            "refined_text": res.refined_text,
        }

    @tool("school_search")
    def school_search(region_keyword: str, school_type: str | None = None, limit: int = 20) -> dict[str, Any]:
        """지역명으로 학교를 검색합니다(로컬 데이터). school_type: '초등학교'|'중학교'|'고등학교' 등"""
        return school.search(region_keyword, school_type=school_type, limit=limit)

    @tool("school_near")
    def school_near(lat: float, lng: float, radius_km: float = 1.0, school_type: str | None = None, limit: int = 20) -> dict[str, Any]:
        """좌표(lat,lng) 기준 반경(radius_km) 내 학교를 찾습니다. 학교명/유형/위도경도/거리 포함. 거리/도보시간은 직선거리 기반 추정치입니다."""
        return school.near(lat, lng, radius_km=radius_km, school_type=school_type, limit=limit)

    @tool("school_near_grouped")
    def school_near_grouped(lat: float, lng: float, radius_km: float = 2.0, limit_per_type: int = 5) -> dict[str, Any]:
        """좌표(lat,lng) 기준 반경 내 학교를 초등학교/중학교/고등학교로 구분해서 각 5개씩 거리순으로 조회합니다. 학교명/유형/위도경도/거리 포함."""
        return school.near_grouped(lat, lng, radius_km=radius_km, limit_per_type=limit_per_type)

    @tool("school_zone_search")
    def school_zone_search(level: str, query: str, limit: int = 20) -> dict[str, Any]:
        """학교 학구/학교군/교육행정구역(로컬 JSON)에서 문자열로 검색합니다. level: elem|middle|high|high_unequal|edu_admin"""
        return school.zone_search(level, query, limit=limit)

    @tool("school_zone_by_school")
    def school_zone_by_school(school_name: str, school_type: str | None = None, limit: int = 20) -> dict[str, Any]:
        """학교명으로 학구ID를 찾고(학교학구도연계정보), 초/중/고 학구/학교군 정보를 같이 반환합니다(좌표 없음)."""
        return school.zone_by_school(school_name, school_type=school_type, limit=limit)

    return [lawd_resolve_code, lawd_search, rtms_apt_trade_detail, vworld_get_coord, school_search, school_near, school_near_grouped, school_zone_search, school_zone_by_school]


def _parse_tool_content(content: Any) -> Any:
    """Tool message content가 JSON 문자열이면 파싱, 아니면 그대로 반환."""
    if isinstance(content, str):
        try:
            return json.loads(content)
        except Exception:
            return content
    return content


def _extract_school_json(trace: list[dict[str, Any]]) -> dict[str, Any] | None:
    """
    trace에서 school_near_grouped 결과를 찾아 구조화된 JSON으로 변환.
    vworld_get_coord 결과가 있으면 매물 위도/경도도 포함.
    school_near_grouped가 호출되지 않았으면 None 반환.
    """
    vworld: dict[str, Any] | None = None
    school_grouped: dict[str, Any] | None = None

    for item in trace:
        name = item.get("name")
        content = _parse_tool_content(item.get("content"))
        if name == "vworld_get_coord" and isinstance(content, dict):
            vworld = content
        elif name == "school_near_grouped" and isinstance(content, dict):
            school_grouped = content

    if school_grouped is None:
        return None

    schools = school_grouped.get("schools", {})
    center = school_grouped.get("center", {})

    property_lat = (vworld or {}).get("lat") or center.get("lat")
    property_lng = (vworld or {}).get("lng") or center.get("lng")
    property_name = (vworld or {}).get("refined_text") or (vworld or {}).get("address") or ""

    return {
        "property_name": property_name,
        "property_lat": property_lat,
        "property_lng": property_lng,
        "elementary_schools": [
            {"name": s["name"], "lat": s["lat"], "lng": s["lng"]}
            for s in schools.get("초등학교", [])
        ],
        "middle_schools": [
            {"name": s["name"], "lat": s["lat"], "lng": s["lng"]}
            for s in schools.get("중학교", [])
        ],
        "high_schools": [
            {"name": s["name"], "lat": s["lat"], "lng": s["lng"]}
            for s in schools.get("고등학교", [])
        ],
    }


async def run_talk(
    messages: list[dict[str, Any]],
    *,
    context: dict[str, Any] | None = None,
    model: str = "gpt-4o-mini",
    temperature: float = 0.0,
) -> dict[str, Any]:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY가 설정되어 있지 않습니다 (settings.openai_api_key).")

    tools = build_tools()
    tool_names = [t.name for t in tools]
    system = _build_system_prompt(context, tool_names)

    llm = ChatOpenAI(model=model, temperature=temperature, api_key=settings.openai_api_key)

    # LangGraph prebuilt agent (tool-calling)
    from langgraph.prebuilt import create_react_agent

    agent = create_react_agent(llm, tools, prompt=system)

    in_msgs = _to_langchain_messages(messages)
    state = await agent.ainvoke({"messages": in_msgs})
    out_msgs = state.get("messages", [])

    # Extract final assistant text (best-effort)
    answer = ""
    for m in reversed(out_msgs):
        if isinstance(m, AIMessage):
            answer = str(m.content or "").strip()
            if answer:
                break

    trace: list[dict[str, Any]] = []
    for m in out_msgs:
        m_type = getattr(m, "type", None)
        if m_type == "tool":
            trace.append(
                {
                    "name": getattr(m, "name", None),
                    "content": getattr(m, "content", None),
                    "tool_call_id": getattr(m, "tool_call_id", None),
                }
            )

    # school_near_grouped가 호출된 경우 tool 결과에서 직접 JSON 조립
    school_json = _extract_school_json(trace)
    if school_json is not None:
        answer = json.dumps(school_json, ensure_ascii=False, indent=2)

    return {
        "answer": answer or "응답을 생성하지 못했습니다. 질문을 조금 더 구체적으로 입력해 주세요.",
        "messages": [getattr(m, "model_dump", lambda: {"type": getattr(m, "type", None), "content": getattr(m, "content", None)})() for m in out_msgs],  # best-effort
        "trace": trace,
    }


