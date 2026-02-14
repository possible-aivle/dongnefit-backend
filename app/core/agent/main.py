"""Interactive execution script for the Regional Policy Agent with human-in-the-loop."""

import asyncio
import sys
import os

# 현재 디렉토리를 path에 추가하여 모듈 import 가능하게 함
# app/core/agent/main.py 위치 기준, 프로젝트 루트는 ../../../
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.core.agent.agent import RegionalPolicyAgent
from app.config import settings


async def main():
    """Supervisor Agent 인터랙티브 모드 테스트 실행."""
    print("=" * 60)
    print("Regional Policy Agent - 인터랙티브 모드")
    print("=" * 60)

    # 에이전트 초기화 (interactive=True)
    try:
        agent = RegionalPolicyAgent(llm_provider="openai", interactive=True)
    except Exception as e:
        print(f"[오류] 에이전트 초기화 실패: {e}")
        return

    while True:
        # 사용자 입력 받기
        print("\n" + "-" * 60)
        user_query = input("분석할 주제나 지역을 입력하세요 (종료하려면 'q' 입력): ").strip()

        if user_query.lower() in ('q', 'quit', 'exit'):
            print("종료합니다.")
            break

        if not user_query:
            continue

        print(f"\n[시스템] '{user_query}' 분석을 시작합니다...\n")

        # 에이전트 실행
        try:
            result = await agent.run(user_query)

            # 결과 출력
            if result["success"]:
                content = result["content"]
                print("\n" + "=" * 60)
                print("[최종 생성된 콘텐츠]")
                print("=" * 60)
                print(f"제목: {content.blog_title}")
                print(f"카테고리: {content.category}")
                print(f"태그: {', '.join(content.tags)}")
                print(f"최종 SEO 점수: {result['seo_score']}점")

                if result.get("post_url"):
                    print(f"\n[발행 완료] URL: {result['post_url']}")
                elif result.get("success"):
                     print("\n[발행 건너뜀] (설정 또는 일시 중지됨)")

                print(f"\n--- 본문 요약 (앞 300자) ---")
                print(content.blog_content[:300])
                print("...")

                # 전체 내용 저장 여부 묻기
                save = input("\n전체 내용을 파일로 저장하시겠습니까? (y/n) [n]: ").strip().lower()
                if save == 'y':
                    filename = f"blog_post_{content.region}_{content.analysis_date.strftime('%Y%m%d')}.md"
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(content.blog_content)
                    print(f"파일 저장 완료: {filename}")

            else:
                print(f"\n[ERROR] 실행 실패: {result['error']}")

        except Exception as e:
             print(f"\n[ERROR] 치명적 오류 발생: {e}")

if __name__ == "__main__":
    asyncio.run(main())
