"""Supervisor-Worker Agent using LangGraph.

Central Supervisor Router가 현재 상태를 분석하고,
다음에 실행할 Worker 노드를 자율적으로 결정합니다.
"""

import json
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

from app.config import settings
from app.core.agent.sub_agents.data_classifier import ArticleAnalyzer
from app.core.agent.sub_agents.data_collector import NewsSearchService
from app.core.agent.sub_agents.intent_analyzer import IntentAnalyzer
from app.core.agent.sub_agents.content_generator import ContentGenerator
from app.core.agent.tools.geocoding import GeocodingService
from app.core.agent.models import (
    ANALYZE_DATA,
    COLLECT_DATA,
    FINISH,
    GENERATE_CONTENT,
    OPTIMIZE_SEO,
    PUBLISH_CONTENT,
    AddressInput,
    SupervisorState,
)
from app.core.agent.sub_agents.seo.models import BlogDraft
from app.core.agent.sub_agents.seo.tools import SEOTools
from app.core.agent.sub_agents.seo.workflow import build_seo_workflow
from app.core.agent.tools.tistory_publisher import TistoryWriter


class SupervisorAgent:
    """Supervisor-Worker 기반 자율형 AI Agent.

    사용자의 자연어 쿼리를 받아 데이터 수집, 분석, 콘텐츠 생성,
    SEO 최적화를 자율적으로 수행합니다.
    """

    MAX_SEO_RETRIES = 3
    SEO_TARGET_SCORE = 50 # 85점에서 test하기 위해 잠시 낮춤

    def __init__(self, llm_provider: str = "openai", interactive: bool = False):
        """Initialize supervisor agent.

        Args:
            llm_provider: "openai" or "anthropic"
            interactive: 사용자 인터랙션 활성화 여부
        """
        self.llm_provider = llm_provider
        self.interactive = interactive

        # Supervisor LLM (라우팅 판단용)
        if llm_provider == "anthropic" and settings.anthropic_api_key:
            self.supervisor_llm = ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                api_key=settings.anthropic_api_key,
                temperature=0,
            )
        else:
            self.supervisor_llm = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=settings.openai_api_key,
                temperature=0,
            )

        # Worker 서비스 초기화
        self.geocoding = GeocodingService()
        self.news_search = NewsSearchService()
        self.intent_analyzer = IntentAnalyzer(llm_provider=llm_provider)
        self.analyzer = ArticleAnalyzer(llm_provider=llm_provider)
        self.content_generator = ContentGenerator(llm_provider=llm_provider)
        self.seo_workflow = build_seo_workflow(llm_provider=llm_provider)

        # 그래프 빌드
        self.graph = self._build_graph()

    # ========================================================
    # Graph Builder
    # ========================================================

    def _build_graph(self):
        """LangGraph StateGraph를 구축합니다."""
        workflow = StateGraph(SupervisorState)

        # 노드 등록
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("analyze_intent", self._analyze_intent_node)
        workflow.add_node(COLLECT_DATA, self._collect_data_node)
        workflow.add_node(ANALYZE_DATA, self._analyze_data_node)
        workflow.add_node(GENERATE_CONTENT, self._generate_content_node)
        workflow.add_node(OPTIMIZE_SEO, self._optimize_seo_node)
        workflow.add_node(PUBLISH_CONTENT, self._publish_content_node)

        # 시작점: Supervisor
        workflow.set_entry_point("supervisor")

        # Supervisor → 조건부 분기
        workflow.add_conditional_edges(
            "supervisor",
            self._route_next_action,
            {
                "analyze_intent": "analyze_intent",
                COLLECT_DATA: COLLECT_DATA,
                ANALYZE_DATA: ANALYZE_DATA,
                GENERATE_CONTENT: GENERATE_CONTENT,
                OPTIMIZE_SEO: OPTIMIZE_SEO,
                PUBLISH_CONTENT: PUBLISH_CONTENT,
                FINISH: END,
            },
        )

        # 각 Worker → Supervisor로 복귀
        workflow.add_edge("analyze_intent", "supervisor")
        workflow.add_edge(COLLECT_DATA, "supervisor")
        workflow.add_edge(ANALYZE_DATA, "supervisor")
        workflow.add_edge(GENERATE_CONTENT, "supervisor")
        workflow.add_edge(OPTIMIZE_SEO, "supervisor")
        workflow.add_edge(PUBLISH_CONTENT, "supervisor")

        return workflow.compile()

    def _route_next_action(self, state: SupervisorState) -> str:
        """Supervisor의 결정에 따라 다음 노드를 라우팅합니다."""
        return state.get("next_action", FINISH)

    # ========================================================
    # Supervisor Node (The Brain)
    # ========================================================

    def _supervisor_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Supervisor Router: 현재 상태를 분석하여 다음 액션을 결정합니다."""
        # 상태 요약
        has_articles = bool(state.get("raw_articles"))
        has_issues = bool(state.get("policy_issues"))
        has_content = state.get("final_content") is not None
        seo_score = state.get("seo_score")
        post_url = state.get("post_url")
        retry_count = state.get("retry_count", 0)
        collection_retries = state.get("collection_retries", 0)

        # 결정 로직 (규칙 기반 + LLM 보조)
        if state.get("intent_analysis") is None:
            next_action = "analyze_intent"
            reason = "사용자 의도 및 개체 분석이 필요합니다."
        elif not has_articles:
            if collection_retries >= 3:
                next_action = FINISH
                reason = f"데이터 수집 {collection_retries}회 재시도 실패. 수집된 기사가 없어 종료합니다."
            else:
                next_action = COLLECT_DATA
                reason = f"데이터가 없으므로 수집이 필요합니다. (재시도 {collection_retries + 1}/3)"
        elif state.get("policy_issues") is None:
            next_action = ANALYZE_DATA
            reason = "수집된 데이터의 분석이 필요합니다."
        elif not has_content:
            next_action = GENERATE_CONTENT
            if has_issues:
                reason = "분석 결과를 바탕으로 콘텐츠를 생성해야 합니다."
            else:
                reason = "정책 이슈가 없어 일반/키워드 기반 콘텐츠를 생성합니다."
        elif seo_score is None or (seo_score < self.SEO_TARGET_SCORE and retry_count < self.MAX_SEO_RETRIES):
            next_action = OPTIMIZE_SEO
            reason = f"SEO 점수({seo_score or '미측정'})가 목표({self.SEO_TARGET_SCORE})에 미달합니다."
        else:
            next_action = FINISH
            if seo_score and seo_score >= self.SEO_TARGET_SCORE:
                reason = f"SEO 점수 {seo_score}점 달성! 모든 작업이 완료되었습니다."
            else:
                reason = f"최대 시도 횟수({self.MAX_SEO_RETRIES}) 도달. 현재 점수: {seo_score}점."

        # 발행 단계 확인
        if next_action == FINISH and not post_url and has_content: # has_content 체크 추가 (데이터 수집 실패 시 content 없음)
            # 콘텐츠가 있고 SEO가 완료되었는데 발행되지 않았다면 발행 시도
            if has_content and settings.tistory_id and settings.tistory_password:
                # 사용자 요청으로 자동 발행 일시 중지
                # next_action = PUBLISH_CONTENT
                # reason = "SEO 최적화 완료. 티스토리에 발행합니다."
                reason += " (자동 발행 일시 중지됨)"
            elif has_content and not (settings.tistory_id and settings.tistory_password):
                reason += " (티스토리 계정 설정 없음으로 발행 건너뜀)"

        # 로그 기록
        log_entry = f"[Supervisor] {reason} -> {next_action}"
        print(f"\n{log_entry}")

        steps_log = state.get("steps_log", [])
        steps_log.append(log_entry)

        return {
            **state,
            "next_action": next_action,
            "steps_log": steps_log,
        }

    # ========================================================
    # Worker Nodes
    # ========================================================

    async def _analyze_intent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Intent Analyzer: 사용자 의도 및 개체를 분석합니다."""
        print("\n[Intent Analyzer] 의도 분석 시작...")
        steps_log = state.get("steps_log", [])

        try:
            user_query = state["user_query"]
            result = await self.intent_analyzer.analyze_intent(user_query)

            log = f"[Intent] {result.intent} | 지역: {result.region} | 유형: {result.real_estate_type}"
            print(f"  [OK] {log}")
            steps_log.append(log)

            return {
                **state,
                "intent_analysis": result,
                "steps_log": steps_log
            }

        except Exception as e:
            error_msg = f"의도 분석 실패: {e}"
            steps_log.append(f"[Intent] [ERROR] {error_msg}")
            print(f"  [FAIL] {error_msg}")

            # 실패 시에도 진행은 가능하도록 None 설정 (이후 단계에서 처리)
            return {**state, "error": error_msg, "intent_analysis": None, "steps_log": steps_log}

    async def _collect_data_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Data Collector: 뉴스 데이터를 수집합니다. (재시도 및 폴백 로직 포함)"""
        print("\n[Data Collector] 데이터 수집 시작...")
        steps_log = state.get("steps_log", [])
        collection_retries = state.get("collection_retries", 0)

        try:
            # 의도 분석 결과 활용
            intent_result = state.get("intent_analysis")
            user_query = state["user_query"]

            # 검색 전략 결정 (재시도 횟수에 따른 Fallback)
            strategies = []

            # 1. Intent Analyzer가 제안한 키워드 사용 (1순위)
            if collection_retries == 0 and intent_result and hasattr(intent_result, "search_keywords") and intent_result.search_keywords:
                strategies.append("의도 기반 키워드")
                keywords = intent_result.search_keywords
            # 2. 제안된 키워드가 없거나 부족하면 보완 (Geocoding 기반)
            elif collection_retries <= 1:
                strategies.append("지역 기반 키워드")
                # 쿼리에서 주소/지역 정보 추출 (Geocoding)
                admin_region = self._extract_region_from_query(user_query)
                if admin_region:
                    keywords = self.geocoding.generate_search_keywords(admin_region)
                    # 부동산 유형이 있으면 조합
                    if intent_result and intent_result.real_estate_type:
                        keywords = [f"{k} {intent_result.real_estate_type}" for k in keywords]
                else:
                    keywords = [user_query]
            # 3. 3차 시도 이상: 원본 쿼리 또는 더 광범위한 검색
            else:
                strategies.append("원본 쿼리 (Fallback)")
                keywords = [user_query]

            strategy_name = " + ".join(strategies)
            print(f"  [Collector] 전략: {strategy_name} | 키워드 수: {len(keywords)}")
            steps_log.append(f"[Collector] 전략: {strategy_name}")

            # 키워드로 뉴스 검색
            articles = await self.news_search.search_multiple_keywords(
                keywords, display_per_keyword=10
            )

            # 주소 정보는 컨텍스트 유지를 위해 필요하므로 추출 시도 (검색에는 안 써도)
            if not locals().get("admin_region"):
                 admin_region = self._extract_region_from_query(user_query)

            log = f"[Collector] {len(articles)}개 기사 수집 완료"
            print(f"  [OK] {log}")
            steps_log.append(log)

            return {
                **state,
                "admin_region": admin_region, # 마지막으로 성공한 지역 정보 업데이트
                "raw_articles": articles,
                "steps_log": steps_log,
                "collection_retries": collection_retries + 1 # 재시도 횟수 증가
            }

        except Exception as e:
            error_msg = f"데이터 수집 실패: {e}"
            steps_log.append(f"[Collector] [ERROR] {error_msg}")
            print(f"  [FAIL] {error_msg}")
            # 에러 발생 시에도 재시도 횟수는 증가시켜야 무한 루프 방지 가능
            return {
                **state,
                "error": error_msg,
                "raw_articles": [],
                "steps_log": steps_log,
                "collection_retries": collection_retries + 1
            }

    async def _analyze_data_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Data Analyzer: 기사를 분류하고 이슈를 추출합니다."""
        print("\n[Data Analyzer] 분석 시작...")
        steps_log = state.get("steps_log", [])

        try:
            raw_articles = state.get("raw_articles", [])
            if not raw_articles:
                steps_log.append("[Analyzer] 분석할 기사가 없습니다.")
                return {**state, "policy_issues": [], "steps_log": steps_log}

            # 1. 기사 분류
            classified = await self.analyzer.classify_articles_batch(raw_articles)
            print(f"  분류 완료: {len(classified)}/{len(raw_articles)}개 관련 기사")

            # 2. 이슈 추출
            admin_region = state.get("admin_region")
            region_name = admin_region.full_address if admin_region else state["user_query"]
            issues = await self.analyzer.extract_policy_issues(classified, region_name)

            # 통계
            positive = sum(1 for i in issues if i.sentiment == "positive")
            negative = sum(1 for i in issues if i.sentiment == "negative")

            log = f"[Analyzer] {len(issues)}개 이슈 추출 (호재: {positive}, 악재: {negative})"
            print(f"  [OK] {log}")
            steps_log.append(log)

            return {
                **state,
                "classified_articles": classified,
                "policy_issues": issues,
                "steps_log": steps_log,
            }

        except Exception as e:
            error_msg = f"분석 실패: {e}"
            steps_log.append(f"[Analyzer] [ERROR] {error_msg}")
            print(f"  [FAIL] {error_msg}")
            return {**state, "error": error_msg, "policy_issues": [], "steps_log": steps_log}

    async def _generate_content_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Content Generator: 블로그 초안을 작성합니다."""
        print("\n[Content Generator] 콘텐츠 생성 시작...")
        steps_log = state.get("steps_log", [])

        try:
            policy_issues = state.get("policy_issues", [])
            admin_region = state.get("admin_region")
            region_name = admin_region.full_address if admin_region else state["user_query"]

            if not policy_issues:
                print("  [Generator] 정책 이슈 부재 -> 일반 키워드 기반 생성 모드 진입")
                # steps_log.append("[Generator] 생성할 이슈가 없습니다.")
                # return {**state, "steps_log": steps_log}

            custom_title = None

            # 인터랙티브 모드: 사전 설정 (키워드, 제목)
            if self.interactive:
                print("\n" + "="*40)
                print("[인터랙티브] 콘텐츠 생성 설정")
                use_custom = input("사용자 입력을 통해 키워드/제목 등을 직접 설정하시겠습니까? (y/n) [n]: ").strip().lower()

                if use_custom == 'y':
                    # 키워드 설정
                    print(f"\n현재 키워드 (지역/주제): {region_name}")
                    new_keyword = input(f"새 키워드를 입력하세요 (엔터: 유지): ").strip()
                    if new_keyword:
                        region_name = new_keyword
                        print(f"키워드가 변경되었습니다: {region_name}")

                    # 제목 설정
                    new_title = input("사용할 블로그 제목을 입력하세요 (엔터: 자동 생성): ").strip()
                    if new_title:
                        custom_title = new_title
                        print(f"제목이 설정되었습니다: {custom_title}")

            # 콘텐츠 생성 (사용자 의도 반영)
            content = await self.content_generator.generate_content(
                region_name, policy_issues, user_query=state["user_query"], custom_title=custom_title
            )

            # 인터랙티브 모드: 제목 확인 (사전 설정 안 했을 경우) 및 후처리 (카테고리, 태그)
            if self.interactive:
                if not custom_title:
                    print(f"\n[인터랙티브] 생성된 제목: {content.blog_title}")
                    user_title = input("이 제목을 사용하시겠습니까? (엔터: 예, 또는 새 제목 입력): ").strip()
                    if user_title:
                        content.blog_title = user_title
                        print(f"제목이 변경되었습니다: {content.blog_title}")

                # 카테고리/태그 설정
                print(f"\n[인터랙티브] 분류 및 태그 설정")
                print(f"현재 카테고리: {content.category}")
                new_category = input("카테고리를 변경하시겠습니까? (엔터: 유지, 또는 새 카테고리 입력): ").strip()
                if new_category:
                    content.category = new_category

                print(f"현재 태그: {', '.join(content.tags)}")
                change_tags = input("태그를 수정하시겠습니까? (y/n) [n]: ").strip().lower()
                if change_tags == 'y':
                    tags_input = input("새 태그를 쉼표로 구분하여 입력하세요: ").strip()
                    if tags_input:
                        content.tags = [t.strip() for t in tags_input.split(",") if t.strip()]

            # target_keyword 설정
            if self.interactive and use_custom == 'y' and region_name != (admin_region.full_address if admin_region else state["user_query"]):
                keyword = region_name
            else:
                keyword = admin_region.sigungu if admin_region else state["user_query"]

            content.target_keyword = keyword

            log = f"[Generator] \"{content.blog_title}\" 초안 작성 완료"
            print(f"  [OK] {log}")
            steps_log.append(log)

            return {
                **state,
                "final_content": content,
                "steps_log": steps_log,
            }

        except Exception as e:
            error_msg = f"콘텐츠 생성 실패: {e}"
            steps_log.append(f"[Generator] [ERROR] {error_msg}")
            print(f"  [FAIL] {error_msg}")
            return {**state, "error": error_msg, "steps_log": steps_log}

    async def _optimize_seo_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """SEO Optimizer: SEO 점수를 측정하고 개선합니다."""
        print("\n[SEO Optimizer] SEO 최적화 시작...")
        steps_log = state.get("steps_log", [])
        retry_count = state.get("retry_count", 0)

        try:
            content = state["final_content"]

            # RegionalAnalysisContent → SEO BlogDraft 변환
            draft = BlogDraft(
                title=content.blog_title,
                content=content.blog_content,
                category=content.category,
                tags=content.tags,
                target_keyword=content.target_keyword or content.region,
                meta_description=content.meta_description,
            )

            # SEO 워크플로우 실행 (분석 + 개선)
            if self.interactive:
                seo_result = await self.seo_workflow.run_interactive(draft)
            else:
                seo_result = await self.seo_workflow.run(draft)

            # 결과 추출
            improved_score = seo_result.get("improved_score")
            original_score = seo_result.get("original_score")
            improved_draft = seo_result.get("improved_draft")

            current_score = improved_score.total_score if improved_score else (
                original_score.total_score if original_score else 0
            )

            # 개선된 내용을 final_content에 반영
            if improved_draft:
                content.blog_title = improved_draft.title
                content.blog_content = improved_draft.content
                content.category = improved_draft.category
                content.tags = improved_draft.tags
                content.meta_description = improved_draft.meta_description

            log = f"[SEO] 점수 {current_score}점 (시도 {retry_count + 1}/{self.MAX_SEO_RETRIES})"
            print(f"  [OK] {log}")
            steps_log.append(log)

            return {
                **state,
                "final_content": content,
                "seo_score": current_score,
                "retry_count": retry_count + 1,
                "steps_log": steps_log,
            }

        except Exception as e:
            error_msg = f"SEO 최적화 실패: {e}"
            steps_log.append(f"[SEO] [ERROR] {error_msg}")
            print(f"  [FAIL] {error_msg}")
            # SEO 실패 시 점수 0으로 설정하여 다음 시도 또는 종료
            return {
                **state,
                "seo_score": 0,
                "retry_count": retry_count + 1,
                "error": error_msg,
                "steps_log": steps_log,
            }

    async def _publish_content_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Tistory Publisher: 블로그 글을 발행합니다."""
        print("\n[Tistory Publisher] 블로그 발행 시작...")
        steps_log = state.get("steps_log", [])

        import asyncio
        loop = asyncio.get_running_loop()

        def _publish_sync(content):
            # TistoryWriter 초기화 (Selenium 브라우저 실행)
            writer = TistoryWriter(settings.tistory_id, settings.tistory_password)
            try:
                # 로그인
                writer.login()

                # 글 작성
                image_paths = getattr(content, "image_paths", [])

                writer.write_post(
                    blog_title=content.blog_title,
                    blog_content=content.blog_content,
                    category_name=content.category,
                    hashtags=content.tags,
                    image_paths=image_paths
                )
                return "https://wodongtest.tistory.com/" # 임시 URL
            finally:
                writer.close()

        try:
            content = state["final_content"]

            # 별도 스레드에서 실행 (Selenium 블로킹 방지)
            post_url = await loop.run_in_executor(None, _publish_sync, content)

            log = f"[Publisher] 티스토리 발행 완료: {content.blog_title}"
            print(f"  [OK] {log}")
            steps_log.append(log)

            return {
                **state,
                "post_url": post_url,
                "steps_log": steps_log
            }

        except Exception as e:
            error_msg = f"티스토리 발행 실패: {e}"
            steps_log.append(f"[Publisher] [ERROR] {error_msg}")
            print(f"  [FAIL] {error_msg}")

            # 발행 실패해도 전체 프로세스는 성공으로 간주 (콘텐츠는 생성되었으므로)
            return {
                **state,
                "error": error_msg,
                "steps_log": steps_log
            }

    # ========================================================
    # Helper Methods
    # ========================================================

    def _extract_region_from_query(self, query: str):
        """사용자 쿼리에서 지역 정보를 추출합니다."""
        try:
            address_input = AddressInput(address=query)
            return self.geocoding.parse_address(address_input)
        except (ValueError, Exception):
            return None

    # ========================================================
    # Public Interface
    # ========================================================

    async def run(self, user_query: str) -> Dict[str, Any]:
        """에이전트를 실행합니다.

        Args:
            user_query: 사용자 자연어 쿼리 (예: "강남역 호재 알려줘")

        Returns:
            최종 상태 딕셔너리
        """
        initial_state: SupervisorState = {
            "user_query": user_query,
            "admin_region": None,
            "intent_analysis": None,
            "collection_retries": 0,
            "raw_articles": [],
            "classified_articles": [],
            "policy_issues": None,
            "final_content": None,
            "seo_score": None,
            "next_action": "",
            "retry_count": 0,
            "steps_log": [],
            "error": None,
            "post_url": None,
        }

        print("\n" + "=" * 60)
        print(f"[Supervisor Agent] 시작: \"{user_query}\"")
        print("=" * 60)

        result = await self.graph.ainvoke(initial_state)

        print("\n" + "=" * 60)
        if result.get("error") and not result.get("final_content"):
            print(f"[ERROR] 실행 실패: {result['error']}")
        else:
            score = result.get("seo_score", "N/A")
            print(f"[OK] 완료! SEO 점수: {score}점")
            if result.get("final_content"):
                print(f"[제목] {result['final_content'].blog_title}")
        print("=" * 60)

        # 실행 이력 출력
        print("\n[실행 이력]")
        for i, log in enumerate(result.get("steps_log", []), 1):
            print(f"  {i}. {log}")

        return result
