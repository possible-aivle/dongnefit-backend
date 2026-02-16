"""Intent Analyzer Agent."""

from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

from app.config import settings
from app.core.agent.models import IntentAnalysisResult


class IntentAnalyzer:
    """사용자 의도 및 개체 추출 에이전트."""

    def __init__(self, llm_provider: str = "openai"):
        """Initialize Intent Analyzer."""
        self.llm_provider = llm_provider
        self.llm = self._initialize_llm()
        self.parser = PydanticOutputParser(pydantic_object=IntentAnalysisResult)

    def _initialize_llm(self):
        """LLM 초기화."""
        if self.llm_provider == "anthropic" and settings.anthropic_api_key:
            return ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                api_key=settings.anthropic_api_key,
                temperature=0,
            )
        else:
            return ChatOpenAI(
                model="gpt-4o",  # 정확한 추출을 위해 고성능 모델 사용 권장
                api_key=settings.openai_api_key,
                temperature=0,
            )

    async def analyze_intent(self, user_query: str) -> IntentAnalysisResult:
        """
        사용자 쿼리를 분석하여 의도와 개체(지역, 부동산 유형)를 추출합니다.

        Args:
            user_query: 사용자 입력 쿼리

        Returns:
            IntentAnalysisResult: 분석 결과
        """
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
You are an expert in Natural Language Understanding (NLU) for Real Estate domains.
Your task is to analyze the user's input and extract structured information.

# Output Format
You must return the result in the following JSON structure:
{{
    "intent": "INFO_RETRIEVAL" | "CONTENT_CREATION" | "MARKET_ANALYSIS",
    "region": "Extracted region name (e.g., Gangnam Station, Yeoksam-dong)",
    "real_estate_type": "Extracted real estate type (e.g., Officetel, Apartment) or null",
    "original_query": "The original user input"
}}

# Extraction Rules
1. **Intent Classification**:
    - `INFO_RETRIEVAL`: Simple queries asking for information (e.g., "Gangnam Station officetel prices", "living environment").
    - `CONTENT_CREATION`: Requests to write, draft, or create content (e.g., "Write a blog post", "Draft a article", "Create a listing", "I want to write about...").
    - `MARKET_ANALYSIS`: Requests for deep analysis, reports, or investment value (e.g., "Analyze the market trends", "Investment value of...").
    - If unsure, default to `INFO_RETRIEVAL`.

2. **Entity Extraction**:
    - `region`: Extract the most specific location mentioned. If multiple are mentioned, include them all (e.g., "Gangnam Station Yeoksam-dong"). This is MANDATORY. If no region is found, try to infer it from the context or return an empty string (but the system might fail later).
    - `real_estate_type`: Extract specific property types like "Officetel", "Apartment", "Villa", "Studio". If not specified, return `null`.

3. **Handling Ambiguity**:
    - If the input is complex sentences, focus on the *core* request.
    - Ignore polite phrases like "Please", "I want to know".

# Examples
Input: "강남역 역삼동 오피스텔"
Output: {{ "intent": "INFO_RETRIEVAL", "region": "강남역 역삼동", "real_estate_type": "오피스텔", ... }}

Input: "역삼동 오피스텔에 대해 글을 작성해보고 싶어"
Output: {{ "intent": "CONTENT_CREATION", "region": "역삼동", "real_estate_type": "오피스텔", ... }}

Input: "송파구 아파트 투자 가치 어때?"
Output: {{ "intent": "MARKET_ANALYSIS", "region": "송파구", "real_estate_type": "아파트", ... }}

Input: "강남역 맛집 추천해줘"
Output: {{ "intent": "INFO_RETRIEVAL", "region": "강남역", "real_estate_type": null, ... }} (Note: unrelated to real estate, but extract what you can)
""",
                ),
                ("human", "{query}"),
            ]
        )

        chain = prompt | self.llm.with_structured_output(IntentAnalysisResult)

        try:
            result = await chain.ainvoke({"query": user_query})
            # with_structured_output은 Pydantic 객체를 직접 반환할 수 있음
            # 만약 dict로 반환된다면 parse_obj 사용
            if isinstance(result, dict):
                result = IntentAnalysisResult(**result)

            # original_query가 모델에 의해 채워지지 않았을 경우를 대비해 수동 할당
            if not result.original_query:
                result.original_query = user_query

            return result

        except Exception as e:
            print(f"[IntentAnalyzer] Error parsing intent: {e}")
            # Fallback: 기본값 반환
            return IntentAnalysisResult(
                intent="INFO_RETRIEVAL",
                region=user_query, # 전체를 지역으로 가정 (위험하지만 에러보다는 나음)
                real_estate_type=None,
                original_query=user_query
            )
