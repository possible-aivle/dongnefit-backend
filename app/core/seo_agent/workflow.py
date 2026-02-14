"""LangGraph workflow for SEO optimization."""

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from app.config import settings
from app.core.seo_agent.models import (
    BlogDraft,
    ImprovedBlog,
    SEOAgentState,
    SEOIssue,
    SEOScoreBreakdown,
)
from app.core.seo_agent.tools import SEOTools


class SEOWorkflow:
    """LangGraph workflow for SEO optimization."""

    def __init__(self, llm: BaseChatModel):
        """
        Initialize SEO workflow.

        Args:
            llm: Language model
        """
        self.llm = llm
        self.tools = SEOTools(llm)
        self.analysis_graph = self._build_analysis_graph()
        self.improvement_graph = self._build_improvement_graph()
        # 호환성을 위해 전체 워크플로우도 유지 (analyze_and_improve용)
        self.graph = self._build_graph()

    def _build_analysis_graph(self) -> Any:
        """Build the graph for analysis phase only."""
        workflow = StateGraph(dict)
        workflow.add_node("validate_input", self._validate_input_node)
        workflow.add_node("calculate_score", self._calculate_score_node)
        workflow.add_node("analyze_issues", self._analyze_issues_node)

        workflow.set_entry_point("validate_input")
        workflow.add_edge("validate_input", "calculate_score")
        workflow.add_edge("calculate_score", "analyze_issues")
        workflow.add_edge("analyze_issues", END)

        return workflow.compile()

    def _build_improvement_graph(self) -> Any:
        """Build the graph for improvement phase only."""
        workflow = StateGraph(dict)
        workflow.add_node("improve_content", self._improve_content_node)
        workflow.add_node("rescore", self._rescore_node)
        workflow.add_node("generate_report", self._generate_report_node)

        workflow.set_entry_point("improve_content")
        workflow.add_edge("improve_content", "rescore")
        workflow.add_edge("rescore", "generate_report")
        workflow.add_edge("generate_report", END)

        return workflow.compile()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        workflow = StateGraph(dict)

        # Add nodes
        workflow.add_node("validate_input", self._validate_input_node)
        workflow.add_node("calculate_score", self._calculate_score_node)
        workflow.add_node("analyze_issues", self._analyze_issues_node)
        workflow.add_node("improve_content", self._improve_content_node)
        workflow.add_node("rescore", self._rescore_node)
        workflow.add_node("generate_report", self._generate_report_node)

        # Add edges
        workflow.set_entry_point("validate_input")
        workflow.add_edge("validate_input", "calculate_score")
        workflow.add_edge("calculate_score", "analyze_issues")
        workflow.add_edge("analyze_issues", "improve_content")
        workflow.add_edge("improve_content", "rescore")
        workflow.add_edge("rescore", "generate_report")
        workflow.add_edge("generate_report", END)

        return workflow.compile()

    def _validate_input_node(self, state: dict) -> dict:
        """입력 검증 노드."""
        draft = state["original_draft"]

        # 기본 검증
        if not draft.title:
            raise ValueError("제목이 비어있습니다")
        if not draft.content:
            raise ValueError("콘텐츠가 비어있습니다")
        if not draft.target_keyword:
            raise ValueError("타겟 키워드가 비어있습니다")

        print("[SEO Agent] Input validation complete")
        return state

    def _calculate_score_node(self, state: dict) -> dict:
        """초기 점수 계산 노드."""
        draft: BlogDraft = state["original_draft"]

        score = self.tools.analyze_seo_score(draft)
        state["original_score"] = score

        print(f"[SEO Agent] Initial SEO score calculated: {score.total_score}")
        print(f"  - 제목: {score.title_score}/{self.tools.scorer.WEIGHTS['title']}")
        print(
            f"  - 구조: {score.content_structure_score}/{self.tools.scorer.WEIGHTS['content_structure']}"
        )
        print(
            f"  - 키워드: {score.keyword_optimization_score}/{self.tools.scorer.WEIGHTS['keyword']}"
        )
        print(
            f"  - 가독성: {score.readability_score}/{self.tools.scorer.WEIGHTS['readability']}"
        )
        print(
            f"  - 메타데이터: {score.metadata_score}/{self.tools.scorer.WEIGHTS['metadata']}"
        )

        return state

    async def _analyze_issues_node(self, state: dict) -> dict:
        """이슈 분석 노드."""
        draft: BlogDraft = state["original_draft"]
        score: SEOScoreBreakdown = state["original_score"]

        issues = await self.tools.analyze_seo_issues(draft, score)
        state["issues"] = issues

        print(f"[SEO Agent] SEO issue analysis complete: {len(issues)} issues found")
        for issue in issues:
            print(f"  - [{issue.severity}] {issue.category}: {issue.description}")

        return state

    async def _improve_content_node(self, state: dict) -> dict:
        """콘텐츠 개선 노드."""
        draft: BlogDraft = state["original_draft"]
        issues: list[SEOIssue] = state["issues"]

        changes = []
        selected = state.get("selected_categories")

        # 선별적 개선 여부 확인 (None이나 빈 리스트면 전체 개선)
        should_improve_title = not selected or "title" in selected
        should_improve_structure = not selected or "structure" in selected
        should_improve_keyword = not selected or "keyword" in selected
        should_improve_readability = not selected or "readability" in selected
        should_improve_metadata = not selected or "metadata" in selected

        print(f"[시스템] Improvement mode: {'Selective' if selected else 'Auto (All)'}")
        if selected:
            print(f"  Targets: {selected}")

        # 1. 제목 개선
        title_issues = [i for i in issues if i.category == "title"]
        if title_issues and should_improve_title:
            print("  개선 중: 제목...")
            improved_title = await self.tools.improve_title(draft, issues)
            if improved_title != draft.title:
                changes.append(f"제목 변경: '{draft.title}' → '{improved_title}'")
        else:
            improved_title = draft.title

        # 2. 구조 개선
        structure_issues = [i for i in issues if i.category == "structure"]
        if structure_issues and should_improve_structure:
            print("  개선 중: 콘텐츠 구조...")
            improved_content = await self.tools.improve_structure(draft, issues)
            changes.append("콘텐츠 구조 개선 (H2/H3 헤딩 추가)")
        else:
            improved_content = draft.content

        # 3. 키워드 및 가독성 개선
        keyword_issues = [i for i in issues if i.category == "keyword"]
        readability_issues = [i for i in issues if i.category == "readability"]

        # 실제 개선 대상 확인
        target_keyword_issues = keyword_issues if should_improve_keyword else []
        target_readability_issues = readability_issues if should_improve_readability else []

        if target_keyword_issues or target_readability_issues:
            print("  개선 중: 키워드 최적화 및 가독성...")
            # 구조가 이미 개선되었다면 그것을 기반으로 개선
            temp_draft = BlogDraft(
                title=improved_title,
                content=improved_content,
                category=draft.category,
                tags=draft.tags,
                target_keyword=draft.target_keyword,
                meta_description=draft.meta_description,
            )

            # 선택된 이슈만 전달하여 개선
            target_issues = target_keyword_issues + target_readability_issues
            improved_content = await self.tools.improve_content(temp_draft, target_issues)

            if target_keyword_issues:
                changes.append("키워드 최적화 (밀도 및 분포 조정)")
            if target_readability_issues:
                changes.append("가독성 개선 (문장 길이 조절)")

        # 4. 메타데이터 개선
        metadata_issues = [i for i in issues if i.category == "metadata"]
        if metadata_issues and should_improve_metadata:
            print("  개선 중: 메타데이터...")
            metadata = await self.tools.optimize_metadata(draft, issues)
            improved_category = metadata.get("category", draft.category)
            improved_tags = metadata.get("tags", draft.tags)
            improved_meta_desc = metadata.get(
                "meta_description", draft.meta_description or ""
            )
            changes.append("메타데이터 최적화 (카테고리, 태그, 메타 설명)")
        else:
            improved_category = draft.category
            improved_tags = draft.tags
            improved_meta_desc = draft.meta_description or ""

        # 개선된 블로그 생성
        improved_blog = ImprovedBlog(
            title=improved_title,
            content=improved_content,
            category=improved_category,
            tags=improved_tags,
            meta_description=improved_meta_desc,
            target_keyword=draft.target_keyword,
            changes_summary=changes,
        )

        state["improved_draft"] = improved_blog
        print(f"[시스템] Content improvement complete: {len(changes)} items changed")

        return state

    def _rescore_node(self, state: dict) -> dict:
        """재점수 계산 노드."""
        improved: ImprovedBlog = state["improved_draft"]

        # ImprovedBlog을 BlogDraft로 변환
        draft = BlogDraft(
            title=improved.title,
            content=improved.content,
            category=improved.category,
            tags=improved.tags,
            target_keyword=state["original_draft"].target_keyword,
            meta_description=improved.meta_description,
        )

        improved_score = self.tools.analyze_seo_score(draft)
        state["improved_score"] = improved_score

        original_score: SEOScoreBreakdown = state["original_score"]
        improvement = improved_score.total_score - original_score.total_score

        print(f"[시스템] Rescoring complete: {improved_score.total_score} (+{improvement})")

        return state

    def _generate_report_node(self, state: dict) -> dict:
        """비교 리포트 생성 노드."""
        original_score: SEOScoreBreakdown = state["original_score"]
        improved_score: SEOScoreBreakdown = state["improved_score"]
        improved: ImprovedBlog = state["improved_draft"]

        report = self.tools.generate_comparison_report(
            original_score, improved_score, improved.changes_summary
        )

        state["comparison_report"] = report.model_dump()

        print(f"[시스템] Comparison report generated")
        print(f"  {report.summary}")

        return state

    async def run(self, draft: BlogDraft) -> dict[str, Any]:
        """
        Run the SEO optimization workflow.

        Args:
            draft: Blog draft

        Returns:
            Final state with scores and improved content
        """
        initial_state: SEOAgentState = {
            "original_draft": draft,
            "original_score": None,
            "issues": None,
            "improved_draft": None,
            "improved_score": None,
            "comparison_report": None,
            "selected_categories": None,
        }

        print("[시스템] SEO optimization workflow starting...\n")
        result = await self.graph.ainvoke(initial_state)
        print("\n[시스템] SEO optimization complete!")

        return result

    async def run_analysis(self, draft: BlogDraft) -> dict[str, Any]:
        """Run only the analysis phase."""
        initial_state: SEOAgentState = {
            "original_draft": draft,
            "original_score": None,
            "issues": None,
            "improved_draft": None,
            "improved_score": None,
            "comparison_report": None,
            "selected_categories": None,
        }

        print("[시스템] Starting analysis phase...\n")
        result = await self.analysis_graph.ainvoke(initial_state)
        print("\n[시스템] Analysis complete!")
        return result

    async def run_improvement(self, state: dict[str, Any], selected_categories: list[str] = None) -> dict[str, Any]:
        """Run the improvement phase with optional selection."""
        # 상태 업데이트
        current_state = state.copy()
        if selected_categories:
            current_state["selected_categories"] = selected_categories

        print(f"[시스템] Starting improvement phase (Selected: {selected_categories})...\n")
        result = await self.improvement_graph.ainvoke(current_state)
        print("\n[시스템] Improvement complete!")
        return result


def build_seo_workflow(llm_provider: str = "openai") -> SEOWorkflow:
    """
    Build SEO workflow with specified LLM provider.

    Args:
        llm_provider: "openai" or "anthropic"

    Returns:
        SEOWorkflow instance
    """
    if llm_provider == "anthropic" and settings.anthropic_api_key:
        llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=settings.anthropic_api_key,
        )
    else:
        llm = ChatOpenAI(
            model="gpt-4o",
            api_key=settings.openai_api_key,
        )

    return SEOWorkflow(llm)
