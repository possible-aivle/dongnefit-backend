"""Analyzer tools for article classification and sentiment analysis."""

import json
from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

from app.config import settings
from app.core.agent.models import NewsArticle, PolicyIssue


class ArticleAnalyzer:
    """LLM 기반 기사 분석기."""

    def __init__(self, llm_provider: str = "openai"):
        """
        Initialize article analyzer.

        Args:
            llm_provider: "openai" or "anthropic"
        """
        if llm_provider == "anthropic" and settings.anthropic_api_key:
            self.llm = ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                api_key=settings.anthropic_api_key,
                temperature=0.3,
            )
        else:
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=settings.openai_api_key,
                temperature=0.3,
            )

    async def classify_article(self, article: NewsArticle) -> Optional[str]:
        """
        기사의 카테고리를 분류합니다.

        Args:
            article: 분류할 기사

        Returns:
            카테고리 ("traffic", "infrastructure", "policy", "economy", "environment", None)
        """
        system_prompt = """당신은 부동산 관련 뉴스 기사를 분류하는 전문가입니다.

다음 카테고리 중 하나로 기사를 분류하세요:
- traffic: 교통 인프라 (지하철, GTX, 도로, 역세권 등)
- infrastructure: 생활 인프라 및 도시계획 (재개발, 재건축, 상업시설, 산업단지 등)
- policy: 정책 및 규제 (토지거래허가구역, 분양가 규제, 세금 정책 등)
- economy: 경제 환경 (기업 이전, 일자리, 산업 동향 등)
- environment: 환경 및 안전 (오염시설, 혐오시설, 자연재해 등)

부동산과 관련 없는 기사는 "irrelevant"로 분류하세요.

응답은 반드시 JSON 형식으로만 작성하세요:
{"category": "traffic"}"""

        user_prompt = f"""기사 제목: {article.title}
기사 내용: {article.content}

이 기사의 카테고리를 분류하세요."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            response = await self.llm.ainvoke(messages)
            result = json.loads(response.content)
            category = result.get("category")

            if category == "irrelevant":
                return None

            return category

        except Exception as e:
            print(f"[분류 오류] {article.title}: {e}")
            return None

    async def classify_articles_batch(
        self, articles: List[NewsArticle]
    ) -> List[NewsArticle]:
        """
        여러 기사를 일괄 분류합니다.

        Args:
            articles: 분류할 기사 목록

        Returns:
            카테고리가 할당된 기사 목록 (관련 없는 기사는 제외)
        """
        classified = []

        for article in articles:
            category = await self.classify_article(article)
            if category:
                article.category = category
                classified.append(article)

        print(
            f"[분류 완료] {len(classified)}/{len(articles)}개 기사가 부동산 관련으로 분류됨"
        )
        return classified

    async def extract_policy_issues(
        self, articles: List[NewsArticle], region: str
    ) -> List[PolicyIssue]:
        """
        분류된 기사에서 정책 이슈를 추출합니다.

        Args:
            articles: 분류된 기사 목록
            region: 분석 대상 지역

        Returns:
            추출된 정책 이슈 목록
        """
        # 카테고리별로 그룹화
        by_category = {}
        for article in articles:
            if article.category:
                if article.category not in by_category:
                    by_category[article.category] = []
                by_category[article.category].append(article)

        # 카테고리별로 이슈 추출
        all_issues = []
        for category, category_articles in by_category.items():
            issues = await self._extract_issues_for_category(
                category, category_articles, region
            )
            all_issues.extend(issues)

        # 중요도 순으로 정렬
        all_issues.sort(key=lambda x: x.importance, reverse=True)

        print(f"[이슈 추출] 총 {len(all_issues)}개 정책 이슈 추출")
        return all_issues

    async def _extract_issues_for_category(
        self, category: str, articles: List[NewsArticle], region: str
    ) -> List[PolicyIssue]:
        """카테고리별로 이슈를 추출합니다."""
        system_prompt = f"""당신은 부동산 정책 분석 전문가입니다.

{region} 지역의 {category} 관련 뉴스 기사들을 분석하여 주요 이슈를 추출하세요.

각 이슈에 대해 다음을 판단하세요:
- title: 이슈 제목 (간결하게)
- sentiment: "positive" (호재) | "negative" (악재) | "neutral"
- importance: 1-10 (10이 가장 중요)
- summary: 이슈 요약 (2-3문장)

응답은 반드시 다음 JSON 형식을 따르세요:
{{
  "issues": [
    {{
      "title": "GTX-A 노선 개통 예정",
      "sentiment": "positive",
      "importance": 9,
      "summary": "2024년 GTX-A 노선이 개통되어 교통 접근성이 대폭 향상될 예정입니다..."
    }}
  ]
}}"""

        # 기사 목록 구성
        articles_text = "\n\n".join(
            [
                f"[기사 {i+1}]\n제목: {article.title}\n내용: {article.content[:500]}...\nURL: {article.url}"
                for i, article in enumerate(articles[:10])  # 최대 10개까지만
            ]
        )

        user_prompt = f"""다음 기사들을 분석하여 주요 이슈를 추출하세요:

{articles_text}"""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            response = await self.llm.ainvoke(messages)
            result = json.loads(response.content)

            issues = []
            for issue_data in result.get("issues", []):
                # 해당 이슈와 관련된 기사 URL 수집
                sources = [article.url for article in articles[:5]]

                issue = PolicyIssue(
                    category=category,
                    title=issue_data["title"],
                    sentiment=issue_data["sentiment"],
                    importance=issue_data["importance"],
                    summary=issue_data["summary"],
                    sources=sources,
                )
                issues.append(issue)

            return issues

        except Exception as e:
            print(f"[이슈 추출 오류] {category}: {e}")
            return []
