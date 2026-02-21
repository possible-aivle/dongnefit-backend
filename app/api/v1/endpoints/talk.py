"""Talk endpoint (tool-calling agent)."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.agent.talk_agent import run_talk

router = APIRouter()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = Field(..., description="메시지 역할")
    content: str | None = Field(None, description="메시지 본문")


class TalkOptions(BaseModel):
    provider: Literal["gpt", "local_llm"] | None = Field(None, description="LLM 제공자: 'gpt' 또는 'local_llm' (기본값: 설정 파일의 llm_provider)")
    model: str | None = Field(None, description="LLM 모델명 (gpt: 기본값 'gpt-4o-mini', local_llm: 설정 파일의 ollama_model)")
    temperature: float = Field(0.0, ge=0.0, le=2.0)


class TalkRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., description="대화 히스토리")
    context: dict[str, Any] = Field(default_factory=dict, description="동적 프롬프트/툴 설정 컨텍스트")
    options: TalkOptions = Field(default_factory=TalkOptions)


class ToolTrace(BaseModel):
    name: str | None = None
    content: Any | None = None
    tool_call_id: str | None = None


class TalkResponse(BaseModel):
    answer: str
    messages: list[dict[str, Any]]
    trace: list[ToolTrace] = Field(default_factory=list)


@router.post(
    "/talk",
    response_model=TalkResponse,
    summary="Tool-calling talk",
    description="실거래가/법정동코드/좌표 변환 도구를 사용하는 대화형 API",
    tags=["talk"],
)
async def talk(req: TalkRequest) -> TalkResponse:
    try:
        in_messages: list[dict[str, Any]] = []
        for m in req.messages:
            d = m.model_dump()
            d["content"] = d.get("content") or ""
            in_messages.append(d)

        result = await run_talk(
            in_messages,
            context=req.context,
            provider=req.options.provider,
            model=req.options.model,
            temperature=req.options.temperature,
        )
        return TalkResponse(
            answer=result["answer"],
            messages=result.get("messages", []),
            trace=[ToolTrace(**t) for t in result.get("trace", [])],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


