"""Data models for SEO AI Agent."""

from typing import Any, Literal, Optional, TypedDict

from pydantic import BaseModel, Field, field_validator


class BlogDraft(BaseModel):
    """입력 블로그 초안 스키마."""

    title: str = Field(..., description="블로그 제목")
    content: str = Field(..., description="블로그 본문 (Markdown 형식)")
    category: str = Field(..., description="카테고리")
    tags: list[str] = Field(..., description="태그 리스트")
    target_keyword: str = Field(..., description="타겟 키워드")
    meta_description: Optional[str] = Field(None, description="메타 설명")


class SEOScoreBreakdown(BaseModel):
    """SEO 점수 세부 항목."""

    total_score: int = Field(..., ge=0, le=100, description="총점 (0-100)")
    title_score: float = Field(..., ge=0, le=20, description="제목 최적화 점수 (최대 20점)")
    content_structure_score: float = Field(
        ..., ge=0, le=25, description="콘텐츠 구조 점수 (최대 25점)"
    )
    keyword_optimization_score: float = Field(
        ..., ge=0, le=20, description="키워드 최적화 점수 (최대 20점)"
    )
    readability_score: float = Field(
        ..., ge=0, le=15, description="가독성 점수 (최대 15점)"
    )
    metadata_score: float = Field(
        ..., ge=0, le=20, description="메타데이터 점수 (최대 20점)"
    )
    deductions: list[str] = Field(default_factory=list, description="감점 사유 목록")
    recommendations: list[str] = Field(
        default_factory=list, description="개선 제안 목록"
    )


class SEOIssue(BaseModel):
    """분석된 SEO 이슈."""

    category: Literal["title", "structure", "keyword", "metadata", "readability"] = (
        Field(..., description="이슈 카테고리")
    )
    severity: Literal["High", "Medium", "Low"] = Field(..., description="심각도")
    description: str = Field(..., description="이슈 설명")
    current_value: str = Field(..., description="현재 상태")
    recommended_value: str = Field(..., description="권장 값")
    impact: str = Field(..., description="점수에 미치는 영향")

    @field_validator("impact", mode="before")
    @classmethod
    def force_string(cls, v: Any) -> str:
        return str(v)


class ImprovedBlog(BaseModel):
    """개선된 블로그 콘텐츠."""

    title: str = Field(..., description="개선된 제목")
    content: str = Field(..., description="개선된 본문")
    category: str = Field(..., description="개선된 카테고리")
    tags: list[str] = Field(..., description="개선된 태그")
    meta_description: str = Field(..., description="개선된 메타 설명")
    target_keyword: str = Field(..., description="타겟 키워드 (유지)")
    changes_summary: list[str] = Field(
        default_factory=list, description="변경 내역 요약"
    )


class ComparisonReport(BaseModel):
    """개선 전/후 비교 리포트."""

    original_total_score: int = Field(..., description="원본 총점")
    improved_total_score: int = Field(..., description="개선 후 총점")
    score_improvement: int = Field(..., description="점수 상승")
    category_improvements: dict[str, float] = Field(
        default_factory=dict, description="카테고리별 점수 변화"
    )
    key_changes: list[str] = Field(default_factory=list, description="주요 변경사항")
    summary: str = Field(..., description="전체 요약")


class SEOAgentState(TypedDict):
    """LangGraph 상태 관리용 TypedDict."""

    original_draft: BlogDraft
    original_score: Optional[SEOScoreBreakdown]
    issues: Optional[list[SEOIssue]]
    improved_draft: Optional[ImprovedBlog]
    improved_score: Optional[SEOScoreBreakdown]
    comparison_report: Optional[dict[str, Any]]
    selected_categories: Optional[list[str]]
