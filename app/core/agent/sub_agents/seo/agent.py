"""Main SEO Agent class."""

from typing import Any, Optional

from .models import BlogDraft
from .workflow import build_seo_workflow


class SEOAgent:
    """SEO 분석 및 개선 AI Agent."""

    def __init__(self, llm_provider: str = "openai"):
        """
        Initialize SEO Agent.

        Args:
            llm_provider: "openai" or "anthropic"
        """
        self.workflow = build_seo_workflow(llm_provider)

    async def analyze_and_improve(
        self, draft: BlogDraft
    ) -> dict[str, Any]:
        """
        블로그 초안을 분석하고 개선합니다.

        Args:
            draft: 블로그 초안

        Returns:
            {
                "original_draft": BlogDraft,
                "original_score": SEOScoreBreakdown,
                "issues": List[SEOIssue],
                "improved_draft": ImprovedBlog,
                "improved_score": SEOScoreBreakdown,
                "comparison_report": Dict
            }
        """
        result = await self.workflow.run(draft)
        return result

    async def analyze(self, draft: BlogDraft) -> dict[str, Any]:
        """
        블로그 초안을 분석합니다 (점수 계산 및 이슈 도출).

        Args:
            draft: 블로그 초안

        Returns:
            SEOAgentState (analysis phase only)
        """
        return await self.workflow.run_analysis(draft)

    async def improve(
        self, state: dict[str, Any], selected_categories: list[str] = None
    ) -> dict[str, Any]:
        """
        분석된 결과를 바탕으로 콘텐츠를 개선합니다.

        Args:
            state: 분석 단계의 결과 상태
            selected_categories: 개선할 카테고리 리스트 (None이면 전체)

        Returns:
            Final SEOAgentState
        """
        return await self.workflow.run_improvement(state, selected_categories)
