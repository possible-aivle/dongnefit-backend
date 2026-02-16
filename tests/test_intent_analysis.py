import asyncio
import sys
import os
import json

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


async def test_content_intent_analysis():
    """부동산 임장 콘텐츠 의도 분석 테스트."""
    analyzer = IntentAnalyzer()

    # 맞춤형 프롬프트가 적용된 지역 위주로 테스트
    test_cases = [
        {
            "case_name": "강남구 재건축 (투자)",
            "city": "서울시 강남구",
            "building_type": "아파트",
            "content": (
                "압구정 현대아파트 재건축 신속통합기획 확정 이후 호가가 급등하고 있다. "
                "토지거래허가구역임에도 불구하고 현금 부자들의 매수 문의가 끊이지 않는다. "
                "추가 분담금 규모와 한강변 층수 규제 완화가 핵심 변수다."
            ),
        },
        {
            "case_name": "관악구 신림 (실거주/출퇴근)",
            "city": "서울시 관악구",
            "building_type": "오피스텔",
            "content": (
                "신림선 개통으로 여의도 출퇴근 시간이 20분대로 단축되었다. "
                "신림역 인근 오피스텔 월세는 보증금 1000에 70~80만원 선이다. "
                "도림천 산책로가 가깝고 순대타운 등 먹거리가 풍부해 1인 가구에게 인기다."
            ),
        },
        {
            "case_name": "안양시 평촌 (학군/신혼)",
            "city": "안양시",
            "building_type": "아파트",
            "content": (
                "평촌 학원가 도보 이용 가능한 단지들의 전세가율이 높게 형성되어 있다. "
                "GTX-C 인덕원역 호재와 월판선 착공으로 판교 출퇴근 부부들의 수요가 많다. "
                "리모델링 추진 단지들의 동의율 확보가 관건이다."
            ),
        },
         {
            "case_name": "화성시 동탄 (신도시/삼성)",
            "city": "화성시",
            "building_type": "아파트",
            "content": (
                "동탄역 롯데캐슬이 신고가를 경신했다. GTX-A 개통 효과로 수서까지 20분 컷이다. "
                "삼성전자 화성캠퍼스 직주근접 수요가 탄탄하며, 호수공원 주변 상권도 완성형이다. "
                "젊은 부부들이 많아 유치원 경쟁이 치열하다."
            ),
        },
    ]

    print("\n" + "=" * 60)
    print("Content Intent Analyzer Test (Region Specific)")
    print("=" * 60)

    for i, case in enumerate(test_cases, 1):
        print(f"\n[Test Case {i}: {case['case_name']}]")
        print(f"  City: {case['city']}")
        print(f"  Building Type: {case['building_type']}")
        print(f"  Content: {case['content'][:60]}...")
        print("-" * 40)

        result = await analyzer.analyze_content_intent(
            city=case["city"],
            building_type=case["building_type"],
            content=case["content"],
        )

        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))

        # 검증 로직 (간단한 키워드 체크)
        intent_str = str(result.model_dump())
        is_pass = True

        if "강남구" in case["city"] and "재건축" not in intent_str and "투자" not in intent_str:
             print("  [WARNING] 강남구 특성(재건축/투자) 미반영")

        if "관악구" in case["city"] and "1인" not in intent_str and "출퇴근" not in intent_str:
             print("  [WARNING] 관악구 특성(1인/출퇴근) 미반영")

        print("=" * 40)


if __name__ == "__main__":
    asyncio.run(test_content_intent_analysis())
