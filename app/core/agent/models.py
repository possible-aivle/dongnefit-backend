"""Data models for Regional Policy Analysis Agent."""

from datetime import datetime
from typing import Annotated, Any, Literal, Optional, TypedDict

from pydantic import BaseModel, Field


class AddressInput(BaseModel):
    """사용자 입력 주소 모델."""

    address: str = Field(..., description="분석할 주소 (예: 서울시 강남구 역삼동)")
    region_type: Literal["residence", "visit"] = Field(
        "residence", description="지역 유형 (거주지/임장)"
    )


class AdminRegion(BaseModel):
    """행정구역 정보."""

    sido: str = Field(..., description="시/도 (예: 서울특별시)")
    sigungu: str = Field(..., description="시/군/구 (예: 강남구)")
    dong: Optional[str] = Field(None, description="읍/면/동 (예: 역삼동)")
    full_address: str = Field(..., description="전체 행정구역명")


class IntentAnalysisResult(BaseModel):
    """사용자 의도 및 개체 추출 결과."""

    intent: Literal["INFO_RETRIEVAL", "CONTENT_CREATION", "MARKET_ANALYSIS"] = Field(
        "INFO_RETRIEVAL", description="분석된 사용자 의도"
    )
    region: str = Field(..., description="추출된 지역명 (예: 강남역, 역삼동)")
    real_estate_type: Optional[str] = Field(None, description="부동산 유형 (예: 오피스텔, 아파트)")
    search_keywords: list[str] = Field(
        default_factory=list, description="검색 확장을 위한 관련 키워드 목록"
    )
    original_query: str = Field(..., description="원래 사용자 쿼리")


class ContentIntentAnalysisResult(BaseModel):
    """부동산 임장 콘텐츠 의도 분석 결과."""

    intent_main: str = Field(
        ..., description="콘텐츠의 핵심 의도 (예: 투자 가치 분석, 임장 루트 소개, 교통 입지 평가)"
    )
    intent_detail: str = Field(
        ..., description="텍스트에 내포된 보조 의도나 감정적 방향 (예: 기대감, 우려, 비교분석)"
    )
    target_audience: str = Field(
        ..., description="예상 독자 (예: 실거주자, 투자자, 프리미엄 분양 관심자, 임대사업자)"
    )
    data_needed: list[str] = Field(
        default_factory=list,
        description="콘텐츠 목적 달성을 위해 필요한 주요 데이터 (예: 호가 변동, 입주 물량, 유동인구)",
    )
    recommended_field_checklist: list[str] = Field(
        default_factory=list,
        description="실제 임장 시 체크해야 할 핵심 포인트 (예: 주차 공간, 주변 학군, 공실 상태)",
    )
    tone: str = Field(
        ..., description="콘텐츠 전반의 어조 (중립/홍보성/비판적/리뷰형/분석적 등)"
    )



class NewsArticle(BaseModel):
    """수집된 뉴스 기사 모델."""

    title: str = Field(..., description="기사 제목")
    source: str = Field(..., description="언론사")
    url: str = Field(..., description="기사 URL")
    publish_date: datetime = Field(..., description="발행일")
    content: str = Field(..., description="기사 본문")
    category: Optional[str] = Field(None, description="카테고리 (분류 전에는 None)")


class PolicyIssue(BaseModel):
    """분석된 정책 이슈."""

    category: Literal[
        "traffic",  # 교통
        "infrastructure",  # 생활 인프라
        "policy",  # 정책 및 규제
        "economy",  # 경제 환경
        "environment",  # 환경 및 안전
        "market_trend",  # 시장 동향 (시세, 거래량)
        "living_environment",  # 생활 환경 (학군, 상권)
        "investment",  # 투자 포인트
        "other",  # 기타
    ] = Field(..., description="이슈 카테고리")
    title: str = Field(..., description="이슈 제목")
    sentiment: Literal["positive", "negative", "neutral"] = Field(
        ..., description="호재/악재 구분"
    )
    importance: int = Field(..., ge=1, le=10, description="중요도 (1-10)")
    summary: str = Field(..., description="이슈 요약")
    sources: list[str] = Field(default_factory=list, description="출처 URL 목록")


class RegionalAnalysisContent(BaseModel):
    """최종 생성된 콘텐츠."""

    region: str = Field(..., description="분석 지역명")
    analysis_date: datetime = Field(..., description="분석 일자")
    positive_issues: list[PolicyIssue] = Field(
        default_factory=list, description="호재 목록"
    )
    negative_issues: list[PolicyIssue] = Field(
        default_factory=list, description="악재 목록"
    )
    blog_title: str = Field(..., description="블로그 제목")
    blog_content: str = Field(..., description="블로그 본문 (Markdown)")
    category: str = Field(..., description="블로그 카테고리")
    tags: list[str] = Field(default_factory=list, description="블로그 태그")
    meta_description: str = Field(..., description="메타 설명")
    target_keyword: str = Field("", description="타겟 키워드")
    image_paths: list[str] = Field(default_factory=list, description="생성된 이미지 로컬 경로 목록")


# ============================================================
# Development Event Analysis Models (호재/악재 분석 전용)
# ============================================================


class DevelopmentEvent(BaseModel):
    """개별 개발 이벤트."""

    year: int = Field(..., description="이벤트 연도 (YYYY)")
    event_name: str = Field(..., description="이벤트명 (예: GTX-B 노선 확정)")
    event_type: Literal["positive", "negative"] = Field(
        ..., description="호재/악재 구분"
    )
    category: str = Field(
        ..., description="카테고리 (교통/재건축/공급/규제/학군/상업시설/인프라/기타)"
    )
    summary: str = Field(..., description="2~3줄 요약 (근거 포함)")
    tags: list[str] = Field(default_factory=list, description="관련 해시태그")
    sources: list[str] = Field(default_factory=list, description="출처 URL 목록")


class YearlyEventSummary(BaseModel):
    """연도별 이벤트 요약 통계."""

    year: int = Field(..., description="연도")
    positive: int = Field(0, description="호재 건수")
    negative: int = Field(0, description="악재 건수")
    events: list[DevelopmentEvent] = Field(
        default_factory=list, description="해당 연도 이벤트 목록"
    )


class CategoryAnalysis(BaseModel):
    """카테고리별 분석 결과."""

    category: str = Field(..., description="카테고리명 (예: 교통 호재, 규제/정책 리스크)")
    event_type: Literal["positive", "negative"] = Field(
        ..., description="호재/악재 구분"
    )
    descriptions: list[str] = Field(
        default_factory=list, description="분석 내용 문단 목록"
    )
    tags: list[str] = Field(default_factory=list, description="관련 해시태그")


class DevelopmentEventAnalysis(BaseModel):
    """호재/악재 분석 전체 결과."""

    region: str = Field(..., description="분석 대상 지역 (예: 서울 동작구 흑석동 A아파트)")
    period: str = Field(..., description="분석 기간 (예: 2024-2028)")
    yearly_summaries: list[YearlyEventSummary] = Field(
        default_factory=list, description="연도별 이벤트 요약"
    )
    category_analyses: list[CategoryAnalysis] = Field(
        default_factory=list, description="카테고리별 분석 결과"
    )
    chart_data: list[dict] = Field(
        default_factory=list, description="그래프용 JSON 데이터"
    )
    total_positive: int = Field(0, description="전체 호재 수")
    total_negative: int = Field(0, description="전체 악재 수")
    most_active_year: int = Field(0, description="이벤트가 가장 많았던 연도")
    chart_image_path: Optional[str] = Field(
        None, description="생성된 막대 그래프 이미지 경로"
    )


# ============================================================
# Supervisor Agent State
# ============================================================

# Worker 노드 이름 상수
COLLECT_DATA = "collect_data"
ANALYZE_DATA = "analyze_data"
ANALYZE_DEVELOPMENT = "analyze_development"
GENERATE_CONTENT = "generate_content"
OPTIMIZE_SEO = "optimize_seo"
PUBLISH_CONTENT = "publish_content"
FINISH = "FINISH"


class SupervisorState(TypedDict):
    """Supervisor-Worker 아키텍처의 공유 상태.

    Supervisor Router가 이 상태를 보고 다음 Worker를 결정합니다.
    """

    # 사용자 입력
    user_query: str  # "강남역 호재 알려줘"

    # Geocoding 결과
    admin_region: Optional[AdminRegion]

    # Intent Analysis 결과
    intent_analysis: Optional["IntentAnalysisResult"]

    # Data Collector 결과
    raw_articles: list[NewsArticle]

    # Data Analyzer 결과
    classified_articles: list[NewsArticle]
    policy_issues: Optional[list[PolicyIssue]]

    # Development Event Agent 결과
    development_analysis: Optional["DevelopmentEventAnalysis"]

    # Content Generator 결과
    final_content: Optional[RegionalAnalysisContent]

    # SEO Optimizer 결과
    seo_score: Optional[int]
    post_url: Optional[str]  # 발행된 블로그 포스트 URL

    # Supervisor 메타데이터
    next_action: str  # Supervisor가 결정한 다음 액션
    retry_count: int  # SEO 개선 반복 횟수
    collection_retries: int  # 데이터 수집 재시도 횟수
    steps_log: list[str]  # 실행 이력
    error: Optional[str]  # 에러 메시지
