"""Interactive execution script for the Regional Policy Agent with human-in-the-loop."""

import asyncio
import json
import os
import sys
from datetime import datetime

# 현재 디렉토리를 path에 추가하여 모듈 import 가능하게 함
# app/core/agent/main.py 위치 기준, 프로젝트 루트는 ../../../
sys.path.append(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
)

from app.core.agent.agent import RegionalPolicyAgent
from app.core.agent.models import AddressInput, DevelopmentEventAnalysis, SupervisorState


async def run_analysis_only(agent: RegionalPolicyAgent, region: str):
    """호재/악재 분석 전용 모드 실행."""
    print(f"\n[시스템] '{region}' 호재/악재 분석을 시작합니다...")

    # 1. 데이터 수집
    print("\n[1/3] 뉴스 데이터 수집 중...")
    supervisor = agent.agent

    # 지역 정보 파싱
    admin_region = supervisor._extract_region_from_query(region)
    region_query = admin_region.full_address if admin_region else region

    # 뉴스 검색
    articles = await supervisor.news_search.search_news(region_query)
    if not articles:
        print("[오류] 뉴스 기사를 찾을 수 없습니다.")
        return None, None, None

    # 2. 기사 분류 및 이슈 추출
    print(f"\n[2/3] 기사 분류 및 이슈 추출 중 ({len(articles)}건)...")
    classified = await supervisor.analyzer.classify_articles_batch(articles)

    issues = await supervisor.analyzer.extract_policy_issues(classified, region_query)

    # 3. 호재/악재 분석
    print("\n[3/3] 연도별 호재/악재 분석 중...")
    analysis = await supervisor.dev_event_agent.analyze(
        region=region_query,
        articles=classified,
        policy_issues=issues,
        user_query=region
    )

    return analysis, issues, articles


def save_analysis_to_file(analysis: DevelopmentEventAnalysis):
    """분석 결과를 파일로 저장합니다."""
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "output", "analysis"
    )
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_region = analysis.region.replace(" ", "_").replace("/", "_")

    # JSON 저장
    json_path = os.path.join(output_dir, f"analysis_{safe_region}_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(analysis.model_dump_json(indent=2))

    # 요약 텍스트 저장
    txt_path = os.path.join(output_dir, f"analysis_{safe_region}_{timestamp}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"[{analysis.region} 개발 이벤트 분석]\n")
        f.write(f"기간: {analysis.period}\n\n")

        f.write("1. 연도별 요약\n")
        for ys in analysis.yearly_summaries:
            f.write(f"- {ys.year}년: 호재 {ys.positive}, 악재 {ys.negative}\n")
            for e in ys.events:
                f.write(f"  * {e.event_name} ({e.event_type})\n")

        f.write("\n2. 카테고리별 상세\n")
        for ca in analysis.category_analyses:
            f.write(f"[{ca.category}]\n")
            for d in ca.descriptions:
                f.write(f"- {d}\n")
            f.write("\n")

    print(f"\n[파일 저장 완료]")
    print(f"- JSON: {json_path}")
    print(f"- TXT: {txt_path}")


async def main():
    """메인 실행 루프."""
    print("=" * 60)
    print("TownFit AI Agent - 통합 실행 모드")
    print("=" * 60)

    try:
        agent = RegionalPolicyAgent(llm_provider="openai", interactive=True)
    except Exception as e:
        print(f"[오류] 에이전트 초기화 실패: {e}")
        return

    while True:
        print("\n" + "-" * 60)
        print("1. 호재/악재 분석 전용 모드 (결과 확인 후 저장/블로그 생성 선택)")
        print("2. 블로그 자동 생성 모드 (전체 자동화)")
        print("q. 종료")
        print("-" * 60)

        mode = input("실행할 모드를 선택하세요: ").strip().lower()

        if mode in ('q', 'quit', 'exit'):
            print("종료합니다.")
            break

        if mode not in ('1', '2'):
            print("잘못된 입력입니다.")
            continue

        region = input("\n분석할 지역/주제를 입력하세요: ").strip()
        if not region:
            continue

        if mode == '1':
            # --- 모드 1: 분석 전용 ---
            try:
                analysis, issues, articles = await run_analysis_only(agent, region)
                if not analysis:
                    continue

                # 사용자 선택 루프
                while True:
                    print("\n[선택]")
                    print("1. 결과 파일로 저장")
                    print("2. 이어서 블로그 콘텐츠 생성")
                    print("3. 메인 메뉴로 돌아가기")

                    choice = input("선택하세요: ").strip()

                    if choice == '1':
                        save_analysis_to_file(analysis)

                    elif choice == '2':
                        print(f"\n[시스템] '{region}' 블로그 콘텐츠 생성을 시작합니다...")

                        # Supervisor 초기 상태 수동 구성
                        supervisor = agent.agent
                        initial_state: SupervisorState = {
                            "user_query": region,
                            "admin_region": supervisor._extract_region_from_query(region),
                            "intent_analysis": None,
                            "collection_retries": 0,
                            "raw_articles": articles,  # 수집된 기사 재사용
                            "classified_articles": [], # analyzer가 반환했지만 내부 로직용이라 비워둠(필요시 채움)
                            "policy_issues": issues,   # 추출된 이슈 재사용
                            "development_analysis": analysis, # 분석 결과 재사용
                            "final_content": None,
                            "seo_score": None,
                            "next_action": "",
                            "retry_count": 0,
                            "steps_log": [],
                            "error": None,
                            "post_url": None,
                        }

                        # 그래프 실행 (GENERATE_CONTENT 단계부터 시작되도록 유도됨)
                        result = await supervisor.graph.ainvoke(initial_state)

                        # 결과 출력 (기존 로직 활용)
                        if result.get("final_content"):
                            print(f"\n[완료] 블로그 생성 및 SEO 최적화 완료")
                            print(f"제목: {result['final_content'].blog_title}")
                            if result.get("post_url"):
                                print(f"발행 URL: {result['post_url']}")
                        else:
                            print(f"\n[실패] {result.get('error')}")
                        break

                    elif choice == '3':
                        break

            except Exception as e:
                print(f"[오류] 분석 중 예외 발생: {e}")

        else:
            # --- 모드 2: 전체 자동화 (기존) ---
            try:
                print(f"\n[시스템] '{region}' 블로그 자동 생성을 시작합니다...")
                result = await agent.run(region)

                if result["success"]:
                    content = result["content"]
                    print("\n" + "=" * 60)
                    print(f"제목: {content.blog_title}")
                    print(f"SEO 점수: {result['seo_score']}점")
                    if result.get("post_url"):
                        print(f"URL: {result['post_url']}")

                    save = input("\n전체 내용을 저장하시겠습니까? (y/n) [n]: ").strip().lower()
                    if save == 'y':
                        filename = f"blog_{content.region}_{datetime.now().strftime('%Y%m%d')}.md"
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(content.blog_content)
                        print(f"저장 완료: {filename}")
                else:
                    print(f"\n[실패] {result['error']}")

            except Exception as e:
                print(f"[오류] 실행 중 예외 발생: {e}")


if __name__ == "__main__":
    asyncio.run(main())
