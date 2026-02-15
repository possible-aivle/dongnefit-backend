"""Talk agent runner using RTMS/LAWD/VWorld tools.

This is a lightweight, tool-calling agent meant for API usage.
"""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.config import settings
from app.core.agent.tools import LawdToolService, RtmsToolService
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


def _build_system_prompt(context: dict[str, Any] | None) -> str:
    ctx = context or {}
    style = str(ctx.get("style") or "답변은 한국어로, 짧게 요약 후 근거를 bullet로 제시하세요.")
    tool_policy = str(
        ctx.get("tool_policy")
        or "질문 해결에 필요한 경우에만 도구를 호출하세요. 도구 결과는 그대로 길게 붙여넣지 말고 핵심만 요약하세요."
    )
    return "\n".join(
        [
            "당신은 한국 부동산 데이터(실거래가/법정동코드/좌표변환) 도우미입니다.",
            f"- {style}",
            f"- {tool_policy}",
        ]
    )


def build_tools() -> list[Any]:
    lawd = LawdToolService()
    rtms = RtmsToolService()

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

    return [lawd_resolve_code, lawd_search, rtms_apt_trade_detail, vworld_get_coord]


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
    system = _build_system_prompt(context)

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

    return {
        "answer": answer or "응답을 생성하지 못했습니다. 질문을 조금 더 구체적으로 입력해 주세요.",
        "messages": [getattr(m, "model_dump", lambda: {"type": getattr(m, "type", None), "content": getattr(m, "content", None)})() for m in out_msgs],  # best-effort
        "trace": trace,
    }


