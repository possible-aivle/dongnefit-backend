import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.agent.sub_agents.intent_analyzer import IntentAnalyzer

async def test_intent_analysis():
    analyzer = IntentAnalyzer()

    test_cases = [
        "강남역 역삼동 오피스텔",
        "역삼동 오피스텔 시세 분석해서 블로그 글 써줘",
        "송파구 아파트 투자 가치 어때?",
        "강남역 맛집 추천해줘",
        "서울시 강남구 삼성동 빌라 전세",
    ]

    print("=" * 60)
    print("Intent Analyzer Test")
    print("=" * 60)

    for query in test_cases:
        print(f"\nQuery: {query}")
        result = await analyzer.analyze_intent(query)
        print(f"Result: {result}")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_intent_analysis())
