"""LangGraph tools for SEO analysis and improvement."""

import json
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from app.core.seo_agent.models import (
    BlogDraft,
    ComparisonReport,
    ImprovedBlog,
    SEOIssue,
    SEOScoreBreakdown,
)
from app.core.seo_agent.scoring import SEOScorer


class SEOTools:
    """SEO 분석 및 개선을 위한 LangGraph Tools."""

    def __init__(self, llm: BaseChatModel):
        """
        Initialize SEO tools.

        Args:
            llm: Language model for analysis and improvement
        """
        self.llm = llm
        self.scorer = SEOScorer()

    def analyze_seo_score(self, draft: BlogDraft) -> SEOScoreBreakdown:
        """
        블로그 초안의 SEO 점수를 계산합니다.

        Args:
            draft: 블로그 초안

        Returns:
            SEO 점수 breakdown
        """
        return self.scorer.calculate_score(draft)

    async def analyze_seo_issues(
        self, draft: BlogDraft, score: SEOScoreBreakdown
    ) -> list[SEOIssue]:
        """
        LLM을 사용하여 SEO 이슈를 분석합니다.

        Args:
            draft: 블로그 초안
            score: SEO 점수

        Returns:
            이슈 목록
        """
        system_prompt = """당신은 SEO 전문가입니다. 블로그 콘텐츠의 SEO 점수와 감점 사유를 분석하여 구체적인 이슈를 도출하세요.

각 이슈는 다음 형식으로 작성하세요:
- category: "title", "structure", "keyword", "metadata", "readability" 중 하나
- severity: "High", "Medium", "Low"
- description: 이슈 설명
- current_value: 현재 상태
- recommended_value: 권장 값
- impact: 점수에 미치는 영향

JSON 배열로 반환하세요."""

        user_prompt = f"""
블로그 정보:
- 제목: {draft.title}
- 타겟 키워드: {draft.target_keyword}
- 카테고리: {draft.category}
- 태그: {', '.join(draft.tags)}
- 메타 설명: {draft.meta_description or '없음'}

SEO 점수:
- 총점: {score.total_score}/100
- 제목: {score.title_score}/{SEOScorer.WEIGHTS['title']}
- 구조: {score.content_structure_score}/{SEOScorer.WEIGHTS['content_structure']}
- 키워드: {score.keyword_optimization_score}/{SEOScorer.WEIGHTS['keyword']}
- 가독성: {score.readability_score}/{SEOScorer.WEIGHTS['readability']}
- 메타데이터: {score.metadata_score}/{SEOScorer.WEIGHTS['metadata']}

감점 사유:
{chr(10).join(f'- {d}' for d in score.deductions)}

개선 제안:
{chr(10).join(f'- {r}' for r in score.recommendations)}

본문 일부:
{draft.content[:500]}...

위 정보를 바탕으로 구체적인 SEO 이슈를 분석하여 JSON 배열로 반환하세요.
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        content = response.content

        # JSON 파싱
        try:
            # JSON 코드 블록에서 추출
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()

            issues_data = json.loads(json_str)
            issues = [SEOIssue(**issue) for issue in issues_data]
            return issues
        except Exception as e:
            # Fallback: 기본 이슈 생성
            print(f"Failed to parse LLM response: {e}")
            return self._create_fallback_issues(score)

    def _create_fallback_issues(self, score: SEOScoreBreakdown) -> list[SEOIssue]:
        """LLM 응답 파싱 실패 시 기본 이슈 생성."""
        issues = []

        # 점수가 낮은 카테고리에 대한 기본 이슈 생성
        if score.title_score < SEOScorer.WEIGHTS["title"] * 0.7:
            issues.append(
                SEOIssue(
                    category="title",
                    severity="High",
                    description="제목 최적화 필요",
                    current_value="최적화 부족",
                    recommended_value="타겟 키워드 포함, 25-60자 길이",
                    impact=f"-{SEOScorer.WEIGHTS['title'] - score.title_score:.0f}점",
                )
            )

        if score.content_structure_score < SEOScorer.WEIGHTS["content_structure"] * 0.7:
            issues.append(
                SEOIssue(
                    category="structure",
                    severity="High",
                    description="콘텐츠 구조 개선 필요",
                    current_value="구조 부족",
                    recommended_value="H2 3-7개, H3로 하위 구조 구성",
                    impact=f"-{SEOScorer.WEIGHTS['content_structure'] - score.content_structure_score:.0f}점",
                )
            )

        if score.keyword_optimization_score < SEOScorer.WEIGHTS["keyword"] * 0.7:
            issues.append(
                SEOIssue(
                    category="keyword",
                    severity="High",
                    description="키워드 최적화 필요",
                    current_value="키워드 부족",
                    recommended_value="키워드 밀도 1-3%, 첫 문단 포함",
                    impact=f"-{SEOScorer.WEIGHTS['keyword'] - score.keyword_optimization_score:.0f}점",
                )
            )

        return issues

    async def improve_title(
        self, draft: BlogDraft, issues: list[SEOIssue]
    ) -> str:
        """
        제목을 개선합니다.

        Args:
            draft: 블로그 초안
            issues: 이슈 목록

        Returns:
            개선된 제목
        """
        title_issues = [i for i in issues if i.category == "title"]

        system_prompt = """당신은 SEO 전문가입니다. 블로그 제목을 SEO에 최적화하세요.

요구사항:
1. 타겟 키워드를 자연스럽게 포함
2. 25-60자 길이
3. 클릭 유도성 향상 (숫자, 가이드, 방법, 총정리 등)
4. 원본의 의도 유지

새로운 제목만 반환하세요 (설명 없이)."""

        user_prompt = f"""
원본 제목: {draft.title}
타겟 키워드: {draft.target_keyword}
카테고리: {draft.category}

이슈:
{chr(10).join(f'- {i.description}: {i.recommended_value}' for i in title_issues)}

개선된 제목을 작성하세요."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        improved_title = response.content.strip().strip('"\'')

        return improved_title

    async def improve_structure(
        self, draft: BlogDraft, issues: list[SEOIssue]
    ) -> str:
        """
        콘텐츠 구조를 개선합니다.

        Args:
            draft: 블로그 초안
            issues: 이슈 목록

        Returns:
            구조 개선된 콘텐츠
        """
        structure_issues = [i for i in issues if i.category == "structure"]

        system_prompt = """당신은 SEO 전문가입니다. 블로그 콘텐츠의 구조를 개선하세요.

요구사항:
1. H2 헤딩으로 주요 섹션 구성 (3-7개)
2. H3로 하위 구조 추가
3. 리스트, 표 등 서식 활용
4. 원본 내용 최대한 보존
5. Markdown 형식 유지

개선된 전체 콘텐츠를 Markdown으로 반환하세요."""

        user_prompt = f"""
타겟 키워드: {draft.target_keyword}

구조 이슈:
{chr(10).join(f'- {i.description}: {i.recommended_value}' for i in structure_issues)}

원본 콘텐츠:
{draft.content}

위 콘텐츠의 구조를 개선하세요."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        improved_content = response.content.strip()

        # Markdown 코드 블록 제거
        if improved_content.startswith("```"):
            improved_content = improved_content.split("```")[1]
            if improved_content.startswith("markdown\n"):
                improved_content = improved_content[9:]
            improved_content = improved_content.strip()

        return improved_content

    async def improve_content(
        self, draft: BlogDraft, issues: list[SEOIssue]
    ) -> str:
        """
        콘텐츠를 개선합니다 (키워드 최적화, 가독성).

        Args:
            draft: 블로그 초안
            issues: 이슈 목록

        Returns:
            개선된 콘텐츠
        """
        keyword_issues = [i for i in issues if i.category == "keyword"]
        readability_issues = [i for i in issues if i.category == "readability"]

        system_prompt = """당신은 SEO 전문가입니다. 블로그 콘텐츠를 개선하세요.

요구사항:
1. 타겟 키워드를 자연스럽게 추가 (키워드 밀도 1-3%)
2. 첫 문단에 키워드 포함
3. 가독성 향상 (문장 길이 조절, 단락 나누기)
4. 원본 내용과 구조 최대한 보존
5. Markdown 형식 유지

개선된 전체 콘텐츠를 반환하세요."""

        user_prompt = f"""
타겟 키워드: {draft.target_keyword}

키워드 이슈:
{chr(10).join(f'- {i.description}: {i.recommended_value}' for i in keyword_issues)}

가독성 이슈:
{chr(10).join(f'- {i.description}: {i.recommended_value}' for i in readability_issues)}

원본 콘텐츠:
{draft.content}

위 콘텐츠를 개선하세요."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        improved_content = response.content.strip()

        # Markdown 코드 블록 제거
        if improved_content.startswith("```"):
            improved_content = improved_content.split("```")[1]
            if improved_content.startswith("markdown\n"):
                improved_content = improved_content[9:]
            improved_content = improved_content.strip()

        return improved_content

    async def optimize_metadata(
        self, draft: BlogDraft, issues: list[SEOIssue]
    ) -> dict[str, Any]:
        """
        메타데이터를 최적화합니다.

        Args:
            draft: 블로그 초안
            issues: 이슈 목록

        Returns:
            개선된 메타데이터 (category, tags, meta_description)
        """
        metadata_issues = [i for i in issues if i.category == "metadata"]

        system_prompt = """당신은 SEO 전문가입니다. 블로그 메타데이터를 최적화하세요.

요구사항:
1. 카테고리: 타겟 키워드와 관련성 높게
2. 태그: 5-10개, 관련성 높은 순서
3. 메타 설명: 150-160자, 타겟 키워드 포함

JSON 형식으로 반환:
{
  "category": "카테고리",
  "tags": ["태그1", "태그2", ...],
  "meta_description": "메타 설명"
}"""

        user_prompt = f"""
타겟 키워드: {draft.target_keyword}
현재 카테고리: {draft.category}
현재 태그: {', '.join(draft.tags)}
현재 메타 설명: {draft.meta_description or '없음'}

메타데이터 이슈:
{chr(10).join(f'- {i.description}: {i.recommended_value}' for i in metadata_issues)}

본문 요약:
{draft.content[:300]}...

메타데이터를 최적화하세요."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        content = response.content

        # JSON 파싱
        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()

            metadata = json.loads(json_str)
            return metadata
        except Exception as e:
            print(f"Failed to parse metadata: {e}")
            # Fallback
            return {
                "category": draft.category,
                "tags": draft.tags + [draft.target_keyword]
                if len(draft.tags) < 5
                else draft.tags,
                "meta_description": draft.meta_description
                or f"{draft.target_keyword}에 대한 완벽 가이드",
            }

    def generate_comparison_report(
        self,
        original_score: SEOScoreBreakdown,
        improved_score: SEOScoreBreakdown,
        changes: list[str],
    ) -> ComparisonReport:
        """
        개선 전/후 비교 리포트를 생성합니다.

        Args:
            original_score: 원본 점수
            improved_score: 개선 후 점수
            changes: 변경 내역

        Returns:
            비교 리포트
        """
        score_improvement = improved_score.total_score - original_score.total_score

        category_improvements = {
            "title": improved_score.title_score - original_score.title_score,
            "content_structure": improved_score.content_structure_score
            - original_score.content_structure_score,
            "keyword": improved_score.keyword_optimization_score
            - original_score.keyword_optimization_score,
            "readability": improved_score.readability_score
            - original_score.readability_score,
            "metadata": improved_score.metadata_score - original_score.metadata_score,
        }

        # 주요 개선 항목
        key_improvements = []
        for category, improvement in category_improvements.items():
            if improvement > 0:
                key_improvements.append(f"{category}: +{improvement:.1f}점")

        summary = f"SEO 점수가 {original_score.total_score}점에서 {improved_score.total_score}점으로 {score_improvement}점 상승했습니다."

        return ComparisonReport(
            original_total_score=original_score.total_score,
            improved_total_score=improved_score.total_score,
            score_improvement=score_improvement,
            category_improvements=category_improvements,
            key_changes=changes,
            summary=summary,
        )
