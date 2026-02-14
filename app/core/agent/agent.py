"""Main agent interface for regional policy analysis."""

from typing import Any, Dict

from .models import RegionalAnalysisContent
from .supervisor import SupervisorAgent


class RegionalPolicyAgent:
    """지역 정책 분석 AI Agent.

    Supervisor-Worker 아키텍처 기반의 자율형 에이전트입니다.
    사용자의 자연어 쿼리를 받아 데이터 수집, 분석, 콘텐츠 생성,
    SEO 최적화를 자율적으로 수행합니다.
    """

    def __init__(self, llm_provider: str = "openai", interactive: bool = False):
        """Initialize regional policy agent.

        Args:
            llm_provider: "openai" or "anthropic"
            interactive: 사용자 인터랙션 활성화 여부
        """
        self.agent = SupervisorAgent(llm_provider=llm_provider, interactive=interactive)

    async def run(self, user_query: str) -> Dict[str, Any]:
        """에이전트를 실행합니다.

        Args:
            user_query: 사용자 자연어 쿼리
                예: "강남역 호재 알려줘", "서울시 강남구 역삼동"

        Returns:
            {
                "success": bool,
                "content": RegionalAnalysisContent | None,
                "seo_score": int | None,
                "steps_log": list[str],
                "error": str | None,
            }
        """
        try:
            result = await self.agent.run(user_query)

            content = result.get("final_content")
            if not content:
                return {
                    "success": False,
                    "content": None,
                    "seo_score": None,
                    "steps_log": result.get("steps_log", []),
                    "error": result.get("error", "콘텐츠 생성 실패"),
                }

            return {
                "success": True,
                "content": content,
                "seo_score": result.get("seo_score"),
                "post_url": result.get("post_url"),
                "steps_log": result.get("steps_log", []),
                "error": None,
            }

        except Exception as e:
            return {
                "success": False,
                "content": None,
                "seo_score": None,
                "steps_log": [],
                "error": str(e),
            }

    def get_blog_content(self, content: RegionalAnalysisContent) -> Dict[str, str | list[str]]:
        """RegionalAnalysisContent를 블로그 포스팅용 딕셔너리로 변환합니다.

        Args:
            content: 생성된 콘텐츠

        Returns:
            {
                "title": str,
                "content": str,
                "category": str,
                "meta_description": str
            }
        """
        return {
            "title": content.blog_title,
            "content": content.blog_content,
            "category": content.category,
            "tags": content.tags,
            "meta_description": content.meta_description,
        }
