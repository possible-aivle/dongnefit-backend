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
    original_query: str = Field(..., description="원래 사용자 쿼리")



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
# Supervisor Agent State
# ============================================================

# Worker 노드 이름 상수
COLLECT_DATA = "collect_data"
ANALYZE_DATA = "analyze_data"
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
