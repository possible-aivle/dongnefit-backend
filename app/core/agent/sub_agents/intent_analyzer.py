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
from app.core.agent.models import IntentAnalysisResult, ContentIntentAnalysisResult
from app.core.agent.resources.region_prompts import (
    SEOUL_GU_PROMPTS,
    GYEONGGI_CITY_PROMPTS,
    BUILDING_TYPE_PROMPTS,
)


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
    "search_keywords": ["keyword1", "keyword2", "keyword3"],
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

3. **Search Keywords Expansion (CRITICAL)**:
    - Generate 3-5 diverse search keywords to gather comprehensive information from various perspectives.
    - Include combinations of region + type + specific aspects (e.g., "price", "prospect", "transportation", "school district").
    - If the user asks for "reviews" or "living experience", include keywords like "living environment", "drawbacks", "noise".
    - If the user intent is `MARKET_ANALYSIS`, include "market trend", "transaction volume", "future value".
    - Example: "Gangnam Apartment" -> ["Gangnam Apartment Price Trend", "Gangnam Reconstruction News", "Gangnam School District Analysis", "Gangnam Apartment Transportation"]

4. **Handling Ambiguity**:
    - If the input is complex sentences, focus on the *core* request.
    - Ignore polite phrases like "Please", "I want to know".

# Examples
Input: "강남역 역삼동 오피스텔"
Output: {{ "intent": "INFO_RETRIEVAL", "region": "강남역 역삼동", "real_estate_type": "오피스텔", "search_keywords": ["강남역 역삼동 오피스텔 시세", "역삼동 오피스텔 월세", "강남역 오피스텔 공실률", "역삼동 치안"], ... }}

Input: "역삼동 오피스텔에 대해 글을 작성해보고 싶어"
Output: {{ "intent": "CONTENT_CREATION", "region": "역삼동", "real_estate_type": "오피스텔", "search_keywords": ["역삼동 오피스텔 장단점", "역삼동 1인 가구 생활", "역삼동 교통 편의성", "역삼동 상권 분석"], ... }}
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

    async def analyze_content_intent(
        self, city: str, building_type: str, content: str
    ) -> ContentIntentAnalysisResult:
        """
        부동산 임장 콘텐츠의 의도를 분석합니다.

        Args:
            city: 시 단위 지역명 (예: 서울시, 수원시, 세종시)
            building_type: 건축물 용도명 (예: 아파트, 상가, 공장, 토지)
            content: 콘텐츠 원문 또는 요약문

        Returns:
            ContentIntentAnalysisResult: 의도 분석 결과
        """
        # 지역 유형 판별
        region_guide = self._get_region_guide(city)
        # 건축물 용도 유형 판별
        building_guide = self._get_building_guide(building_type)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
너는 부동산 임장 콘텐츠의 의도를 분석하는 AI 분석기다.
입력으로는 시 단위 지역명과 건축물 용도명, 그리고 콘텐츠 텍스트가 함께 주어진다.
너의 역할은 텍스트의 중심 의도를 파악하고, 그 의도에 따라 핵심 목적, 타깃 독자, 콘텐츠 방향성,
필요한 데이터 포인트, 그리고 추천 임장 요소(현장 체크리스트)를 설계하는 것이다.

# 분석 목표
아래 요소를 JSON 형태로 출력하라.

- intent_main: 콘텐츠의 핵심 의도 (예: 투자 가치 분석 / 임장 루트 소개 / 교통 입지 평가 / 생활편의시설 리뷰)
- intent_detail: 텍스트에 내포된 보조 의도나 감정적 방향 (예: 기대감, 우려, 비교분석 등)
- target_audience: 예상 독자 (예: 실거주자, 투자자, 프리미엄 분양 관심자, 임대사업자)
- data_needed: 이 콘텐츠의 목적을 달성하기 위해 필요한 주요 데이터 목록
  (예: 호가 변동, 입주 물량, 유동인구, 교통망 예정 노선, 상권 변화)
- recommended_field_checklist: 실제 임장 시 체크해야 할 핵심 포인트 목록
  (예: 주차 공간, 주변 학군, 접근 도로 폭, 공원 거리, 공실 상태 등)
- tone: 콘텐츠 전반의 어조 (중립 / 홍보성 / 비판적 / 리뷰형 / 분석적 등)

# 지역별 분석 가이드
{region_guide}

# 건축물 용도별 분석 가이드
{building_guide}

# 출력 형식
반드시 위 6개 필드를 모두 포함한 JSON 형태로 출력하라.
data_needed와 recommended_field_checklist는 각각 3~6개 항목을 포함하는 배열이어야 한다.
""",
                ),
                (
                    "human",
                    """city: {city}
building_type: {building_type}
content: {content}""",
                ),
            ]
        )

        chain = prompt | self.llm.with_structured_output(ContentIntentAnalysisResult)

        try:
            result = await chain.ainvoke(
                {
                    "city": city,
                    "building_type": building_type,
                    "content": content,
                    "region_guide": region_guide,
                    "building_guide": building_guide,
                }
            )

            if isinstance(result, dict):
                result = ContentIntentAnalysisResult(**result)

            return result

        except Exception as e:
            print(f"[IntentAnalyzer] Error parsing content intent: {e}")
            # Fallback: 기본값 반환
            return ContentIntentAnalysisResult(
                intent_main="분석 실패",
                intent_detail=str(e),
                target_audience="일반",
                data_needed=[],
                recommended_field_checklist=[],
                tone="중립",
            )

    def _get_region_guide(self, city: str) -> str:
        """시 단위 지역명에 따른 분석 가이드를 반환합니다."""
        city_lower = city.strip()

        # 1. 맞춤형 프롬프트 검색 (서울 구 / 경기 시)
        # 서울 구 검색
        for gu, prompt_data in SEOUL_GU_PROMPTS.items():
            if gu in city_lower:
                return self._format_custom_prompt(f"서울시 {gu}", prompt_data)

        # 경기 시 검색
        for city_name, prompt_data in GYEONGGI_CITY_PROMPTS.items():
            if city_name in city_lower: # "수원" in "수원시"
                return self._format_custom_prompt(city_name, prompt_data)

        # 2. 일반 가이드 (Fallback)
        # 서울/수도권 판별
        metro_keywords = [
            "서울", "인천", "경기", "성남", "분당", "용인", "화성", "고양",
            "파주", "김포", "광명", "하남", "과천", "안양", "부천", "의왕",
            "군포", "시흥", "안산", "수원", "평택", "의정부", "구리", "남양주",
        ]
        # 신도시/택지지구 판별
        newtown_keywords = [
            "세종", "동탄", "위례", "미사", "광교", "판교", "운정", "검단",
            "마곡", "송도", "청라", "영종", "양주", "별내", "다산", "교산",
            "왕숙", "창릉", "대장",
        ]

        is_newtown = any(kw in city_lower for kw in newtown_keywords)
        is_metro = any(kw in city_lower for kw in metro_keywords)

        if is_newtown:
            return (
                "[신도시·택지지구 분석 가이드]\n"
                "- 향후 가치 상승 가능성과 교통개통 일정, 인프라 완성도 등 미래지향적 의도 중심으로 분석하라.\n"
                "- 입주 시기, 학교 개교 예정, 상업시설 오픈 일정 등 타임라인이 핵심이다.\n"
                "- 기반시설 진척도(도로, 공원, 상하수도)와 주변 개발 속도를 함께 고려하라."
            )
        elif is_metro:
            return (
                "[서울/수도권 분석 가이드]\n"
                "- 디테일한 상권 변화, 재개발·재건축 계획, 직주근접성이 중요한 변수이다.\n"
                "- 교통(지하철·버스·GTX)과 프라임 입지 중심으로 분석하라.\n"
                "- 규제 변화(투기과열지구, 조정대상지역 등)와 정비사업 단계도 고려하라."
            )
        else:
            return (
                "[지방 중소도시 분석 가이드]\n"
                "- 대단지 신축 중심의 수요·공급 균형 여부를 파악하라.\n"
                "- 산업단지, 혁신도시, 기업 이전 등에 의한 인구 유입과 생활권 흐름 위주로 intent를 판단하라.\n"
                "- 미분양 동향, 전세가율, 지역 고유의 수급 특성을 반영하라."
            )

    def _get_building_guide(self, building_type: str) -> str:
        """건축물 용도명에 따른 분석 가이드를 반환합니다."""
        bt = building_type.strip()

        # 1. 맞춤형 건축물 프롬프트 검색
        for type_name, prompt_data in BUILDING_TYPE_PROMPTS.items():
            # "아파트", "오피스텔" 등 정확히 포함되거나, "상가" in "근린상가" 등
            if type_name in bt:
                return self._format_custom_prompt(type_name, prompt_data)

        # 2. 일반 가이드 (Fallback)
        # 주거형
        residential_keywords = ["아파트", "오피스텔", "주거", "빌라", "다세대", "다가구", "원룸", "투룸"]
        # 상가/근린
        commercial_keywords = ["상가", "근린", "상업", "매장", "점포", "사무실", "오피스"]
        # 공장/물류
        industrial_keywords = ["공장", "물류", "창고", "제조", "산업"]
        # 토지/개발
        land_keywords = ["토지", "개발", "나대지", "임야", "농지", "대지"]

        if any(kw in bt for kw in residential_keywords):
            return (
                "[아파트/주거형 오피스텔 분석 가이드]\n"
                "- 실거주 여건, 생활편의시설(마트, 병원, 공원), 학군, 커뮤니티 관련 언급을 파악하라.\n"
                "- 단지 규모, 세대수, 주차대수, 평면구조 등 실거주 관점을 중시하라.\n"
                "- 전세가율, 갭투자 가능성, 입주 물량 등 투자 관점도 함께 분석하라."
            )
        elif any(kw in bt for kw in commercial_keywords):
            return (
                "[상가/근린시설 분석 가이드]\n"
                "- 유동인구, 업종 믹스, 공실률, 배후 수요 중심으로 intent를 분석하라.\n"
                "- 임대료 수준, 권리금, 수익률, 주변 상권 SWOT를 함께 고려하라.\n"
                "- 점포 가시성, 접근성(주차·대중교통), 층별 용도 등 현장 요소를 중시하라."
            )
        elif any(kw in bt for kw in industrial_keywords):
            return (
                "[공장/물류시설 분석 가이드]\n"
                "- 접근성(고속도로·IC 거리), 평면 효율, 물류 편의성, 전력 용량 등 실무 중심 의도를 판별하라.\n"
                "- 산업단지 지정 여부, 인허가 용이성, 환경 규제를 함께 분석하라.\n"
                "- 천장 높이, 화물차 진입로, 야적장 여부 등 현장 스펙을 확인하라."
            )
        elif any(kw in bt for kw in land_keywords):
            return (
                "[토지/개발지 분석 가이드]\n"
                "- 용도지역(관리·농림·자연녹지 등), 인허가 진행상황, 인프라 진척도를 분석하라.\n"
                "- 투자 포인트(도로 접합, 대지 형상, 경사도, 향)를 중심으로 분석하라.\n"
                "- 개발행위허가 가능 여부, 건폐율·용적률, 주변 개발 호재를 파악하라."
            )
        else:
            return (
                "[일반 건축물 분석 가이드]\n"
                "- 해당 건축물 용도에 적합한 입지 요건과 시장 수급을 분석하라.\n"
                "- 교통 접근성, 주변 환경, 규제 요소를 종합적으로 고려하라.\n"
                "- 임장 시 건물 상태, 관리 수준, 주변 시세 비교를 체크하라."
            )

    def _format_custom_prompt(self, title: str, data: Dict[str, Any]) -> str:
        """맞춤형 프롬프트 데이터를 문자열로 포맷팅합니다."""
        description = data.get("description", "")
        focus_points_list = data.get("focus_points", [])
        focus_points = "\n".join([f"- {point}" for point in focus_points_list])
        target_audience = data.get("target_audience", "")

        # 사용자 요청에 따른 터미널 출력 (실시간 진행 상황 표시)
        print(f"\n[IntentAnalyzer] 맞춤형 프롬프트 발견: {title}")
        print("-" * 50)
        if description:
            print(f"■ 지역/대상 특징: {description}")
        if focus_points_list:
            print(f"■ 핵심 분석 포인트:")
            for point in focus_points_list:
                print(f"  - {point}")
        if target_audience:
            print(f"■ 주요 타깃 독자: {target_audience}")

        # 데이터가 있으면 추가 (건축물 용도 등)
        if "data_needed" in data:
             data_needed_str = ", ".join(data["data_needed"])
             print(f"■ 추천 데이터 포인트: {data_needed_str}")
        print("-" * 50)


        prompt = f"[{title} 맞춤 분석 가이드]\n"
        if description:
            prompt += f"■ 지역/대상 특징: {description}\n"
        if focus_points:
            prompt += f"■ 핵심 분석 포인트:\n{focus_points}\n"
        if target_audience:
            prompt += f"■ 주요 타깃 독자: {target_audience}\n"

        # 데이터가 있으면 추가 (건축물 용도 등)
        if "data_needed" in data:
             data_needed = ", ".join(data["data_needed"])
             prompt += f"■ 추천 데이터 포인트: {data_needed}\n"

        return prompt
