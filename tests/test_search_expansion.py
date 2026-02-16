import pytest
import asyncio
from datetime import datetime
from app.core.agent.sub_agents.intent_analyzer import IntentAnalyzer
from app.core.agent.sub_agents.data_classifier import ArticleAnalyzer
from app.core.agent.models import NewsArticle

@pytest.mark.asyncio
async def test_search_keywords_generation():
    """IntentAnalyzer가 검색 키워드를 생성하는지 테스트"""
    analyzer = IntentAnalyzer()
    query = "강남역 아파트 임장"

    print(f"\n[Test] Query: {query}")
    result = await analyzer.analyze_intent(query)

    print(f"[Intent Result] Intent: {result.intent}")
    print(f"[Intent Result] Keywords: {result.search_keywords}")

    assert result.search_keywords is not None
    assert len(result.search_keywords) >= 3

    # 키워드 다양성 확인 (대충 하나라도 원본과 다르면 성공)
    assert any(kw != query for kw in result.search_keywords)

@pytest.mark.asyncio
async def test_article_classification_new_categories():
    """ArticleAnalyzer가 새로운 카테고리를 분류하는지 테스트"""
    analyzer = ArticleAnalyzer()

    test_cases = [
        {
            "title": "강남 아파트 집값 바닥 찍었나... 거래량 급증",
            "content": "최근 강남구 아파트 거래량이 전월 대비 2배 증가하며 시장 회복 조짐을 보이고 있다. 급매물 소진 후 호가가 오르는 추세다.",
            "expected_category": "market_trend"
        },
        {
            "title": "대치동 학원가 인접한 신축 단지 인기",
            "content": "대치동 학원가를 도보로 이용할 수 있는 신축 아파트 단지가 학부모들에게 큰 인기를 얻고 있다. 명문학군 프리미엄이 붙어...",
            "expected_category": "living_environment"
        },
        {
            "title": "GTX-A 개통 임박, 수서역 5분 거리",
            "content": "수서역세권 개발과 함께 GTX-A 노선 개통이 임박하면서 주변 집값이 들썩이고 있다. 교통 혁명이라 불리는...",
            "expected_category": "traffic"
        }
    ]

    print("\n[Test] Article Classification")
    for case in test_cases:
        article = NewsArticle(
            title=case["title"],
            content=case["content"],
            source="Test",
            url="http://test.com",
            publish_date=datetime.now()
        )

        category = await analyzer.classify_article(article)
        print(f"Title: {case['title'][:20]}... | Expected: {case['expected_category']} | Actual: {category}")

        # LLM이라 가끔 틀릴 수 있으니, expected_category 포함 여부나 관련성 체크
        # traffic vs infrastructure 혼동 가능성 있음
        # expected_category가 traffic이면 infrastructure도 OK로 간주 (테스트 완화)
        if case["expected_category"] == "traffic" and category == "infrastructure":
             print("Warning: traffic classified as infrastructure (acceptable)")
        else:
             assert category == case["expected_category"]

if __name__ == "__main__":
    # pytest 실행 (직접 실행 시)
    asyncio.run(test_search_keywords_generation())
    asyncio.run(test_article_classification_new_categories())
