"""Content generation for regional policy analysis.

Tistory ContentGenerator의 기능을 통합:
- 키워드 추출 (KR-WordRank)
- DALL-E 이미지 생성 및 다운로드
- 섹션 기반 이미지 삽입
- LLM 카테고리 분류 (동네핏 카테고리)
- LLM 해시태그 생성
"""

import os
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

from app.config import settings
from app.core.agent.models import (
    CategoryAnalysis,
    DevelopmentEventAnalysis,
    PolicyIssue,
    RegionalAnalysisContent,
    YearlyEventSummary,
)
from app.core.agent.resources.region_prompts import (
    GYEONGGI_CITY_PROMPTS,
    SEOUL_GU_PROMPTS,
)


class ContentGenerator:
    """블로그 콘텐츠 생성기.

    순수 콘텐츠 생성에만 집중:
    - 정책 이슈 → 블로그 초안 작성
    - 이미지 생성 및 삽입 (DALL-E)
    - 카테고리 분류 및 해시태그 생성
    """

    ENABLE_IMAGE_GENERATION = False  # 이미지 생성 활성화 여부

    def __init__(self, llm_provider: str = "openai"):
        """Initialize content generator.

        Args:
            llm_provider: "openai" or "anthropic"
        """
        if llm_provider == "anthropic" and settings.anthropic_api_key:
            self.llm = ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                api_key=settings.anthropic_api_key,
                temperature=0.7,
            )
        else:
            self.llm = ChatOpenAI(
                model="gpt-4o",
                api_key=settings.openai_api_key,
                temperature=0.7,
            )

        # DALL-E용 OpenAI 클라이언트
        self.openai_client = OpenAI(api_key=settings.openai_api_key)
        self.image_style = "realistic photo, high quality, professional photography, 8k"

    # ========================================================
    # Main Public Methods
    # ========================================================

    async def generate_content(
        self,
        region: str,
        policy_issues: List[PolicyIssue],
        user_query: str = "",
        num_images: int = 3,
        custom_title: Optional[str] = None,
        custom_keyword: Optional[str] = None,
    ) -> RegionalAnalysisContent:
        """정책 이슈 목록을 바탕으로 블로그 콘텐츠를 생성합니다.

        사용자 의도를 분석하여 적절한 글 구조를 결정합니다:
        - "호재/악재" 언급 시 → 호재/악재 섹션 구조
        - "가격 분석", "전망" 등 → 일반 분석 구조

        Args:
            region: 분석 대상 지역
            policy_issues: 추출된 정책 이슈 목록
            user_query: 사용자의 원래 질문/의도
            num_images: 삽입할 이미지 수 (기본값 3, 이미지 생성 비활성화 시 무시)

        Returns:
            생성된 블로그 콘텐츠
        """
        # 사용자 의도 분석: 호재/악재 분류가 필요한가?
        needs_classification = await self._analyze_user_intent(user_query)

        # 호재/악재 분리 (필요할 때만)
        if needs_classification:
            positive_issues = [i for i in policy_issues if i.sentiment == "positive"]
            negative_issues = [i for i in policy_issues if i.sentiment == "negative"]
        else:
            positive_issues = []
            negative_issues = []

        # 지역 데이터 조회
        region_data = self._get_region_data(region)

        # 블로그 본문 생성
        blog_content = await self._generate_blog_content(
            region,
            policy_issues,
            positive_issues,
            negative_issues,
            user_query,
            needs_classification,
            region_data,
        )

        # DALL-E 이미지 생성 및 삽입
        image_paths = []
        if num_images > 0 and self.ENABLE_IMAGE_GENERATION:
            print(f"[시스템] {num_images}개의 이미지 생성 및 삽입 중...")
            blog_content, image_paths = self._insert_images(
                blog_content, region, num_images
            )
            print(f"[시스템] {len(image_paths)}개의 이미지가 삽입되었습니다.")

        # 제목 생성
        if custom_title:
             blog_title = custom_title
        else:
             blog_title = await self._generate_title(region, policy_issues, user_query, needs_classification)

        # 카테고리 분류 (LLM 기반)
        category = await self._classify_category(blog_content)

        # 해시태그 생성 (LLM 기반)
        tags = await self._generate_hashtags(blog_content)

        # 메타 설명 생성
        meta_description = await self._generate_meta_description(
            region, policy_issues, user_query
        )

        return RegionalAnalysisContent(
            region=region,
            analysis_date=datetime.now(),
            positive_issues=positive_issues,
            negative_issues=negative_issues,
            blog_title=blog_title,
            blog_content=blog_content,
            category=category,
            tags=tags,
            meta_description=meta_description,
            image_paths=image_paths,
        )

    def extract_keywords(self, texts: List[str], top_n: int = 5) -> List[str]:
        """텍스트에서 키워드를 추출합니다 (KR-WordRank 기반).

        Args:
            texts: 키워드를 추출할 텍스트 리스트
            top_n: 상위 N개 키워드 반환

        Returns:
            추출된 키워드 리스트
        """
        try:
            from krwordrank.word import summarize_with_keywords  # type: ignore

            # 텍스트 전처리
            preprocessed_texts = []
            for text in texts:
                text = re.sub(r"[^\w\s]", " ", text.lower())
                text = re.sub(r"\s+", " ", text).strip()
                if text:
                    preprocessed_texts.append(text)

            keywords = summarize_with_keywords(
                preprocessed_texts, min_count=1, max_length=10
            )

            top_keywords = [
                keyword
                for keyword, _ in sorted(
                    keywords.items(), key=lambda x: x[1], reverse=True
                )[:top_n]
            ]

            print(f"[시스템] 키워드 추출 완료: {top_keywords}")
            return top_keywords

        except ImportError:
            print("[경고] krwordrank가 설치되지 않았습니다. 빈 리스트를 반환합니다.")
            return []
        except Exception as e:
            print(f"[오류] 키워드 추출 중 오류 발생: {e}")
            return []

    def _get_region_data(self, region: str) -> Optional[Dict]:
        """지역명을 기반으로 프롬프트 데이터를 조회합니다."""
        # 1. 서울 자치구 검색
        if region in SEOUL_GU_PROMPTS:
            return SEOUL_GU_PROMPTS[region]

        # '구'가 빠진 경우 (예: 강남 -> 강남구)
        if region + "구" in SEOUL_GU_PROMPTS:
            return SEOUL_GU_PROMPTS[region + "구"]

        # 2. 경기 주요 도시 검색
        if region in GYEONGGI_CITY_PROMPTS:
            return GYEONGGI_CITY_PROMPTS[region]

        # '시'가 빠진 경우 (예: 수원 -> 수원시)
        if region + "시" in GYEONGGI_CITY_PROMPTS:
            return GYEONGGI_CITY_PROMPTS[region + "시"]

        print(f"[시스템] '{region}'에 대한 맞춤형 프롬프트 데이터가 없습니다. 기본 설정을 사용합니다.")
        return None

    # ========================================================
    # Blog Content Generation
    # ========================================================

    async def _analyze_user_intent(self, user_query: str) -> bool:
        """사용자 의도를 분석하여 호재/악재 분류가 필요한지 판단합니다.

        Args:
            user_query: 사용자 질문

        Returns:
            True if 호재/악재 분류 필요, False otherwise
        """
        if not user_query:
            # 쿼리가 없으면 기본적으로 분류 수행
            return True

        # 키워드 기반 불리언 체크
        classification_keywords = [
            "호재", "악재", "긍정", "부정", "장점", "단점",
            "장단점", "장단", "pros", "cons"
        ]

        query_lower = user_query.lower()
        for keyword in classification_keywords:
            if keyword in query_lower:
                return True

        # 비분류 키워드
        non_classification_keywords = [
            "가격", "시세", "전망", "분석", "트렌드", "현황",
            "상황", "정보", "조사", "현황", "대해"
        ]

        for keyword in non_classification_keywords:
            if keyword in query_lower:
                return False

        # 기본값: 분류 수행 (보수적)
        return True

    async def _generate_outline(
        self,
        region: str,
        target_audience: str,
        all_issues: List[PolicyIssue],
        positive_issues: List[PolicyIssue],
        negative_issues: List[PolicyIssue],
        user_query: str,
        needs_classification: bool,
        region_context: str,
    ) -> str:
        """블로그 글의 구조(아웃라인)를 먼저 생성합니다 (Chain-of-Thought)."""

        system_prompt = f"""당신은 숙련된 콘텐츠 기획자입니다.
블로그 글 작성을 위한 상세한 '아웃라인(개요)'을 작성해주세요.

지역: {region}
타겟 독자: {target_audience}
사용자 요청: {user_query}

{region_context}

목표: 독자가 끝까지 읽게 만드는 논리적이고 매력적인 구성 설계.
"""

        if needs_classification:
            pos_text = "\n".join([f"- {i.title}" for i in positive_issues])
            neg_text = "\n".join([f"- {i.title}" for i in negative_issues])

            user_prompt = f"""다음 호재와 악재를 포함하여 아웃라인을 작성하세요.

[호재]
{pos_text if pos_text else "(없음)"}

[악재]
{neg_text if neg_text else "(없음)"}

필수 포함 구조:
I. 서론 (Hook)
II. 지역 분위기 및 호재 분석 (Main Body 1)
III. 리스크 및 악재 분석 (Main Body 2)
IV. 종합 결론 및 제언 (Conclusion)

각 섹션별로 다룰 핵심 키워드나 논거를 3~4개씩 불렛포인트로 작성해주세요."""

        elif all_issues:
             issues_text = "\n".join([f"- {i.title}" for i in all_issues])
             user_prompt = f"""다음 이슈들을 포함하여 아웃라인을 작성하세요.

[이슈 목록]
{issues_text}

필수 포함 구조:
I. 서론
II. 주요 이슈 심층 분석 (2~3개 섹션으로 구분)
III. 결론

각 섹션별로 다룰 내용을 구체적으로 기획해주세요."""

        else:
            user_prompt = f"""주제: {user_query}

위 주제에 대한 아웃라인을 자유롭게 작성하세요. 전형적인 서론-본론-결론 구조를 따르되, 독자의 흥미를 끌 수 있는 소제목을 기획해주세요."""

        try:
             messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
             response = await self.llm.ainvoke(messages)
             return response.content
        except Exception as e:
            print(f"[아웃라인 생성 오류]: {e}")
            return "아웃라인 생성 실패. 기본 구조로 진행합니다."

    async def _generate_blog_content(
        self,
        region: str,
        all_issues: List[PolicyIssue],
        positive_issues: List[PolicyIssue],
        negative_issues: List[PolicyIssue],
        user_query: str,
        needs_classification: bool,
        region_data: Optional[Dict] = None,
    ) -> str:
        """블로그 본문 생성 (사용자 의도 및 지역 데이터 반영)."""

        # 지역 데이터가 있으면 프롬프트 강화
        region_context = ""
        target_audience = "일반 부동산 관심층"

        if region_data:
            desc = region_data.get("description", "")
            audience = region_data.get("target_audience", "일반 투자자 및 실거주자")
            focus_points = region_data.get("focus_points", [])

            target_audience = audience

            focus_points_str = "\n".join([f"- {point}" for point in focus_points])

            region_context = f"""
[지역 전문 정보]
- 지역 특징: {desc}
- 타겟 독자: {audience}
- **필수 포함 핵심 포인트**:
{focus_points_str}

위 '핵심 포인트'를 글의 적절한 부분에 자연스럽게 녹여내세요.
"""

        # 1. 아웃라인 생성 (CoT)
        outline = await self._generate_outline(
            region,
            target_audience,
            all_issues,
            positive_issues,
            negative_issues,
            user_query,
            needs_classification,
            region_context
        )
        print(f"[시스템] 아웃라인 생성 완료:\n{outline[:200]}...")

        # 2. 블로그 본문 생성 (아웃라인 기반)
        if needs_classification:
            # 호재/악재 분류 모드
            system_prompt = f"""당신은 '{region}' 지역 부동산 전문가입니다.
주독자층: {target_audience}

제공된 [아웃라인]을 바탕으로, {target_audience}에게 실질적인 도움이 되는 블로그 글을 작성하세요.

{region_context}

[아웃라인]
{outline}

작성 지침:
- **반드시 위 아웃라인의 흐름과 논리를 따르세요.**
- Markdown 형식 사용 (H2, H3, 리스트 등)
- 각 이슈마다 출처 링크 포함
- 전문적인 내용을 담되, {target_audience}가 이해하기 쉬운 어조 사용
- 중요한 내용은 **강조** 처리
- 목록(-)이나 표를 활용하여 정보 정리
- SEO를 고려한 키워드 자연스러운 배치
- 글자 수는 약 2000자 정도로 작성"""

            # 상세 정보 제공 (Context for filling the outline)
            positive_text = "\n".join(
                [
                    f"- [{issue.title}] {issue.summary} (중요도: {issue.importance}/10)"
                    for issue in positive_issues
                ]
            )

            negative_text = "\n".join(
                [
                    f"- [{issue.title}] {issue.summary} (중요도: {issue.importance}/10)"
                    for issue in negative_issues
                ]
            )

            user_prompt = f"""위 아웃라인에 맞춰 다음 세부 정보를 활용해 글을 완성해주세요.

**호재 데이터:**
{positive_text if positive_text else "(없음)"}

**악재 데이터:**
{negative_text if negative_text else "(없음)"}

독자들이 이해하기 쉽고, 실질적인 정보를 제공하는 글을 작성하세요."""

        else:
            if not all_issues:
                # 데이터가 없는 경우 (일반 주제)
                system_prompt = f"""당신은 '{region}' 지역 부동산 전문가입니다.
주독자층: {target_audience}

제공된 [아웃라인]을 바탕으로 {target_audience}의 눈높이에 맞춘 상세하고 유익한 블로그 글을 작성해주세요.

{region_context}

[아웃라인]
{outline}

작성 지침:
1. **반드시 위 아웃라인의 흐름과 논리를 따르세요.**
2. 전문적인 내용을 담되, 독자가 이해하기 쉽게 작성해주세요.
3. 소제목(##)을 사용하여 가독성을 높여주세요.
4. 중요한 내용은 **강조**해주세요.
5. 목록(-)이나 표를 사용해 정보를 정리해주세요.
6. 실제 사례나 통계 자료가 있다면(가상의 예시라도) 포함해주세요.
7. 마지막에 결론과 함께 독자에게 도움이 될 만한 조언을 추가해주세요.
8. 마크다운 형식으로 작성해주세요.
9. 글자 수는 약 2000자 정도로 작성해주세요.
"""
                user_prompt = f"""주제: {region} {user_query}

위 주제에 대해 아웃라인을 충실히 따르는 블로그 글을 작성해주세요.
현재 수집된 구체적인 정책 데이터가 없으므로, 일반적인 부동산 지식과 통찰력을 바탕으로 풍부하게 내용을 채워주세요."""

            else:
                # 일반 분석 모드 (이슈 존재)
                system_prompt = f"""당신은 '{region}' 지역 부동산 전문가입니다.
주독자층: {target_audience}

제공된 [아웃라인]을 바탕으로 {target_audience}에게 도움이 되는 전문적인 블로그 글을 작성하세요.

{region_context}

[아웃라인]
{outline}

작성 지침:
- **반드시 위 아웃라인의 흐름과 논리를 따르세요.**
- Markdown 형식 사용 (H2, H3, 리스트 등)
- 전문가적인 내용이지만 일반인도 이해하기 쉽게 작성
- 중요한 내용은 **강조** 처리
- 목록(-)이나 표를 활용하여 정보 정리
- SEO를 고려한 키워드 자연스러운 배치
- 글자 수는 약 2000자 정도로 작성"""

                issues_text = "\n".join(
                    [
                        f"- [{issue.category}] {issue.title}: {issue.summary}"
                        for issue in all_issues
                    ]
                )

                user_prompt = f"""위 아웃라인에 맞춰 다음 이슈 데이터를 활용해 글을 완성해주세요.

**관련 이슈 목록:**
{issues_text}

사용자의 요청("{user_query}")에 맞게 유용하고 실질적인 정보를 제공하세요."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            response = await self.llm.ainvoke(messages)
            draft = response.content

            # 3. 비평 및 수정 (Critique & Revision)
            print(f"[시스템] 초안 작성 완료 (길이: {len(draft)})")

            critique = await self._critique_content(
                draft, outline, region_context, target_audience
            )
            print(f"[시스템] 비평 완료:\n{critique[:200]}...")

            final_content = await self._revise_content(
                draft, critique, region_context, target_audience
            )
            print(f"[시스템] 수정 완료 (길이: {len(final_content)})")

            return final_content

        except Exception as e:
            print(f"[콘텐츠 생성 오류]: {e}")
            return self._generate_fallback_content(
                region, all_issues if not needs_classification else positive_issues + negative_issues
            )



    async def _critique_content(
        self,
        draft: str,
        outline: str,
        region_context: str,
        target_audience: str,
    ) -> str:
        """블로그 초안을 비평하여 개선점을 도출합니다."""
        system_prompt = f"""당신은 꼼꼼한 콘텐츠 에디터입니다.
작성된 블로그 글(초안)을 검토하고, 더 나은 글이 되도록 구체적인 피드백을 제공하세요.

타겟 독자: {target_audience}
{region_context}

[검토 기준]
1. **아웃라인 준수**: 아웃라인의 논리적 흐름을 잘 따르고 있는가?
2. **독자 지향성**: {target_audience}가 흥미를 가질 만한 어조와 내용을 담고 있는가?
3. **가독성**: 문단이 너무 길지 않고, 소제목과 강조가 적절히 사용되었는가?
4. **전문성**: 부동산 전문 용어가 적절히 사용되었으며, 신뢰감을 주는가?
5. **SEO**: 지역명과 핵심 키워드가 자연스럽게 포함되었는가?

비평은 다음 형식으로 작성하세요:
1. 잘된 점: (1~2줄)
2. 개선할 점(구체적인 수정 지침): (3~4가지 핵심 포인트)"""

        user_prompt = f"""[아웃라인]
{outline}

[블로그 초안]
{draft}

위 초안을 비평해주세요."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as e:
            print(f"[비평 생성 오류]: {e}")
            return "비평 생성 실패"

    async def _revise_content(
        self,
        draft: str,
        critique: str,
        region_context: str,
        target_audience: str,
    ) -> str:
        """비평을 반영하여 블로그 글을 수정합니다."""
        system_prompt = f"""당신은 전문 블로그 작가입니다.
에디터의 [비평 및 수정 지침]을 반영하여 [블로그 초안]을 다시 작성하세요.

타겟 독자: {target_audience}
{region_context}

작성 지침:
- 에디터의 지적 사항을 적극 반영하여 글을 개선하세요.
- 마크다운 형식을 유지하세요.
- 글의 흐름이 끊기지 않도록 자연스럽게 연결하세요.
- 글자 수는 기존 분량을 유지하거나 약간 늘리세요."""

        user_prompt = f"""[블로그 초안]
{draft}

[비평 및 수정 지침]
{critique}

위 지침을 반영하여 완성도 높은 최종 원고를 작성해주세요."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as e:
            print(f"[수정 생성 오류]: {e}")
            return draft # 수정 실패 시 초안 반환

    async def _generate_title(

        self,
        region: str,
        policy_issues: List[PolicyIssue],
        user_query: str,
        needs_classification: bool,
    ) -> str:
        """블로그 제목 생성 (사용자 의도 반영)."""
        try:
            # 주요 이슈 키워드 추출 (제목에 포함하기 위해)
            keywords = []
            if policy_issues:
                 # 중요도 높은 이슈 2개 정도 추출
                 top_issues = sorted(policy_issues, key=lambda x: x.importance, reverse=True)[:2]
                 keywords = [issue.title for issue in top_issues]

            keywords_str = ", ".join(keywords)

            system_prompt = "당신은 전문 카피라이터입니다. 독자의 호기심을 자극하고 클릭을 유도하는 매력적인 블로그 제목을 지어주세요."

            if needs_classification:
                positive_count = len([i for i in policy_issues if i.sentiment == "positive"])
                negative_count = len([i for i in policy_issues if i.sentiment == "negative"])

                prompt = f"""'{region}' 부동산 분석 글의 제목을 작성해주세요.

[분석 내용]
- 호재 {positive_count}건, 악재 {negative_count}건
- 주요 키워드: {keywords_str}

[작성 수칙]
1. **기계적인 나열 금지**: "호재 7개와 악재 2개" 같은 제목은 절대 쓰지 마세요.
2. **Hook(훅) 활용**: "지금 들어가도 될까?", "OOO의 진실", "절대 놓치지 마세요" 등 감성적/자극적 문구 활용.
3. **구체성**: 막연한 "분석"보다는 구체적인 이득이나 상황을 암시하세요.
4. **자연스러움**: 친구에게 말하듯 자연스러운 한국어 문장으로 작성하세요.

[예시]
- (Bad) 강남역 호재 5개, 악재 2개 완벽 분석
- (Good) 강남역, 지금이 기회일까? {keywords[0] if keywords else 'GTX'} 호재와 숨겨진 리스크
- (Good) "역시 {region} 불패?" 신고가 갱신 속 불안 요소는?
- (Good) 실거주 관점에서 본 {region}, 딱 이것만 조심하세요

제목 1개만 출력하세요 (따옴표 없이)."""
            else:
                prompt = f"""'{region}' 관련 글의 제목을 작성해주세요.
주제: {user_query}
관련 키워드: {keywords_str}

[작성 수칙]
1. 독자의 호기심을 자극하는 매력적인 카피라이팅.
2. 검색(SEO)을 고려하여 '{region}'과 핵심 키워드를 반드시 포함.
3. "~에 대한 분석" 같은 딱딱한 표현 지양.

[예시]
- (Good) {region} 맛집, 여기 모르면 간첩! 현지인 추천 Best 5
- (Good) {region} 임장 가기 전 필독! A부터 Z까지 총정리

제목 1개만 출력하세요 (따옴표 없이)."""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt)
            ]
            response = await self.llm.ainvoke(messages)
            return response.content.strip().strip('"')

        except Exception as e:
            print(f"[제목 생성 오류]: {e}")
            if needs_classification:
                return f"{region} 부동산 분석: 투자 전 꼭 알아야 할 핵심 포인트" # Fallback도 자연스럽게 수정
            else:
                return f"{region} {user_query} - 총정리"

    async def _generate_meta_description(
        self,
        region: str,
        policy_issues: List[PolicyIssue],
        user_query: str,
    ) -> str:
        """메타 설명 생성 (사용자 의도 반영)."""
        try:
            if policy_issues:
                first_issue = policy_issues[0]
                prompt = f"""'{region}' 지역 부동산 분석 블로그의 메타 설명을 작성하세요.

사용자 요청: "{user_query}"

주요 정보:
- 첫 번째 이슈: {first_issue.title}

조건:
- 150-160자 길이
- 핵심 키워드 포함
- 독자의 클릭을 유도하는 설명

메타 설명만 반환하세요."""
            else:
                prompt = f"""'{region}' 지역 부동산 분석 블로그의 메타 설명을 작성하세요.

사용자 요청: "{user_query}"

조건:
- 150-160자 길이
- 핵심 키워드 포함
- 독자의 클릭을 유도하는 설명

메타 설명만 반환하세요."""

            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            return response.content.strip()

        except Exception as e:
            print(f"[메타 설명 생성 오류]: {e}")
            return f"{region} 지역의 최신 부동산 정책 호재와 악재를 분석합니다. 투자 전 꼭 확인하세요."

    # ========================================================
    # Category & Hashtag (Tistory 기능 통합)
    # ========================================================

    async def _classify_category(self, content: str) -> str:
        """블로그 글 내용을 기반으로 카테고리를 분류합니다 (동네핏 카테고리 체계).

        Args:
            content: 블로그 글 내용

        Returns:
            분류된 카테고리
        """
        system_prompt = (
            "당신은 블로그 카테고리 분류 전문가입니다. 주어진 블로그 글을 분석하여 가장 적합한 카테고리를 하나만 선택해주세요. "
            "다음 중 하나의 카테고리만 선택하세요: \n"
            "- 동네 소식\n"
            "- 동네 문화\n"
            "- 동네 분석\n"
            "- 동네 임장\n"
            "- 주택 임장\n"
            "- 상가 임장\n"
            "- 부동산학개론\n"
            "- 부동산 금융\n"
            "- 부동산 개발\n"
            "- 부동산 관리\n"
            "- 부동산 법률 및 제도\n"
            "- 부동산 정책 및 이슈\n"
            "- 기타\n"
            "선택한 카테고리 이름만 출력해주세요."
        )

        truncated_content = content[:1000] if len(content) > 1000 else content

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"블로그 글 내용:\n{truncated_content}"),
            ]
            # temperature=0.3 설정
            response = await self.llm.bind(temperature=0.3).ainvoke(messages)
            return response.content.strip()

        except Exception as e:
            print(f"[카테고리 분류 오류]: {e}")
            return "부동산 정책 및 이슈"

    async def _generate_hashtags(self, content: str, max_tags: int = 10) -> List[str]:
        """블로그 글 내용을 기반으로 해시태그를 생성합니다.

        Args:
            content: 블로그 글 내용
            max_tags: 최대 해시태그 개수

        Returns:
            생성된 해시태그 리스트
        """
        system_prompt = (
            "당신은 소셜 미디어 마케팅 전문가입니다. 주어진 블로그 글을 분석하여 효과적인 해시태그를 생성해주세요.\n"
            "해시태그는 블로그 글의 주요 주제와 관련이 있어야 하며, 검색 최적화에 도움이 되어야 합니다.\n"
            f"총 {max_tags}개의 해시태그를 생성해주세요.\n"
            "생성된 해시태그는 쉼표로 구분하여 한 줄로 출력해주세요.\n"
            "해시태그의 앞에는 #이 없이 출력해주세요."
        )

        truncated_content = content[:1500] if len(content) > 1500 else content

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"블로그 글 내용:\n{truncated_content}"),
            ]
            response = await self.llm.ainvoke(messages)
            result = response.content.strip()

            # 파싱: 쉼표로 분리하고 # 제거
            tags = [tag.strip().lstrip("#") for tag in result.split(",") if tag.strip()]

            # 중복 제거 및 최대 개수 제한
            unique_tags = list(dict.fromkeys(tags))
            return unique_tags[:max_tags]

        except Exception as e:
            print(f"[해시태그 생성 오류]: {e}")
            return []

    # ========================================================
    # Image Generation (DALL-E, Tistory 기능 통합)
    # ========================================================

    def _generate_image(self, prompt: str) -> str:
        """DALL-E를 사용하여 이미지를 생성하고 URL을 반환합니다.

        Args:
            prompt: 이미지 생성 프롬프트

        Returns:
            생성된 이미지 URL (실패 시 빈 문자열)
        """
        if not self.ENABLE_IMAGE_GENERATION:
            return ""

        try:
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=f"{prompt}, {self.image_style}",
                size="1024x1024",
                quality="standard",
                n=1,
            )
            return response.data[0].url
        except Exception as e:
            print(f"[오류] 이미지 생성 중 오류: {e}")
            return ""

    def _download_image(self, image_url: str, save_dir: str = "images") -> str:
        """이미지 URL에서 이미지를 다운로드하여 로컬에 저장합니다.

        Args:
            image_url: 다운로드할 이미지 URL
            save_dir: 저장할 디렉토리 (기본값: 현재 모듈 폴더 내 images)

        Returns:
            저장된 파일 경로 (실패 시 빈 문자열)
        """
        if save_dir == "images":
            save_dir = os.path.join(os.path.dirname(__file__), "images")

        if not image_url:
            return ""

        try:
            os.makedirs(save_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"dalle_{timestamp}_{unique_id}.png"
            filepath = os.path.join(save_dir, filename)

            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            with open(filepath, "wb") as f:
                f.write(response.content)

            print(f"[시스템] 이미지 다운로드 완료: {filepath}")
            return filepath

        except Exception as e:
            print(f"[오류] 이미지 다운로드 중 오류: {e}")
            return ""

    def _insert_images(
        self, content: str, keyword: str, num_images: int = 3
    ) -> Tuple[str, list]:
        """SEO 최적화된 방식으로 콘텐츠에 이미지를 삽입합니다.

        소제목(##)을 기준으로 섹션을 분리하고,
        각 섹션의 내용을 반영한 이미지를 생성하여 본문 중간에 자연스럽게 배치합니다.

        Args:
            content: 이미지가 삽입될 콘텐츠
            keyword: 이미지 생성에 사용할 키워드
            num_images: 삽입할 이미지 수

        Returns:
            (이미지가 삽입된 콘텐츠, 생성된 이미지 로컬 경로 리스트)
        """
        if num_images <= 0 or not self.ENABLE_IMAGE_GENERATION:
            return content, []

        # 1. 소제목(##) 기준으로 섹션 분리
        lines = content.split("\n")
        sections = []
        current_section = {"title": "", "content": []}

        for line in lines:
            if line.strip().startswith("##") and not line.strip().startswith("###"):
                if current_section["content"]:
                    sections.append(current_section)
                current_section = {
                    "title": line.strip().replace("##", "").strip(),
                    "content": [line],
                }
            else:
                current_section["content"].append(line)

        if current_section["content"]:
            sections.append(current_section)

        print(f"[시스템] 총 {len(sections)}개 섹션 발견")

        # 섹션이 부족한 경우 단락 기반 삽입
        if len(sections) < 2:
            print("[경고] 소제목이 부족하여 단락 기준으로 이미지 배치")
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            if len(paragraphs) < 3:
                return content, []

            total_paragraphs = len(paragraphs)
            step = max(2, total_paragraphs // (num_images + 1))
            insert_positions = [
                step * (i + 1)
                for i in range(num_images)
                if step * (i + 1) < total_paragraphs
            ]

            result = []
            image_paths = []
            image_count = 0

            for i, para in enumerate(paragraphs):
                result.append(para)
                if image_count < len(insert_positions) and i == insert_positions[image_count]:
                    image_prompt = f"{keyword} 관련 이미지, {para[:100]}"
                    image_url = self._generate_image(image_prompt)
                    if image_url:
                        local_path = self._download_image(image_url)
                        if local_path:
                            alt_text = f"{keyword} 관련 이미지"
                            image_placeholder = f"{{{{IMAGE:{local_path}|{alt_text}}}}}"
                            result.append(image_placeholder)
                            image_paths.append(local_path)
                    image_count += 1

            return "\n\n".join(result), image_paths

        # 2. 서론 제외, 본문 섹션에 균등 배치
        body_sections = sections[1:]
        if len(body_sections) == 0:
            return content, []

        num_insertable = min(num_images, len(body_sections))

        if num_insertable == 1:
            insert_indices = [len(body_sections) // 2]
        elif num_insertable >= len(body_sections):
            insert_indices = list(range(len(body_sections)))
        else:
            step = len(body_sections) / num_insertable
            insert_indices = [int(step * i) for i in range(num_insertable)]

        print(f"[시스템] {len(body_sections)}개 섹션에 {len(insert_indices)}개 이미지 배치")

        # 3. 이미지 생성 및 삽입
        result_lines = []
        image_paths = []

        result_lines.extend(sections[0]["content"])

        images_to_insert = {}
        for img_idx, section_idx in enumerate(insert_indices):
            if section_idx >= len(body_sections):
                continue

            section = body_sections[section_idx]
            section_title = section["title"]
            section_content_preview = " ".join(section["content"][:5])[:200]

            image_prompt = f"{keyword}, {section_title}, {section_content_preview}"
            print(f"[시스템] 이미지 생성 중 [{img_idx + 1}/{len(insert_indices)}]: '{section_title}'")

            image_url = self._generate_image(image_prompt)
            if image_url:
                local_path = self._download_image(image_url)
                if local_path:
                    alt_text = f"{keyword} - {section_title}"
                    images_to_insert[section_idx] = {"path": local_path, "alt": alt_text}
                    image_paths.append(local_path)

        for i, section in enumerate(body_sections):
            result_lines.extend(section["content"])

            if i in images_to_insert:
                img_info = images_to_insert[i]
                image_placeholder = f"{{{{IMAGE:{img_info['path']}|{img_info['alt']}}}}}"
                result_lines.append("")
                result_lines.append(image_placeholder)
                result_lines.append("")

        return "\n".join(result_lines), image_paths

    # ========================================================
    # Content from DevelopmentEventAnalysis (새 Agent 연동)
    # ========================================================

    async def generate_content_from_analysis(
        self,
        region: str,
        analysis: DevelopmentEventAnalysis,
        policy_issues: list,
        user_query: str = "",
        custom_title: Optional[str] = None,
    ) -> RegionalAnalysisContent:
        """DevelopmentEventAnalysis를 기반으로 블로그 콘텐츠를 생성합니다.

        호재/악재 분석 Agent의 구조화된 데이터를 입력받아:
        - 연도별 이슈 요약 표
        - 카테고리별 분석 섹션
        - 그래프 설명 문단
        - SEO 최적화 블로그 글
        을 생성합니다.

        Args:
            region: 분석 대상 지역
            analysis: DevelopmentEventAnalysis 구조화 데이터
            policy_issues: 기존 PolicyIssue 목록 (하위 호환)
            user_query: 사용자 쿼리
            custom_title: 사용자 지정 제목

        Returns:
            RegionalAnalysisContent: 생성된 블로그 콘텐츠
        """
        # 지역 데이터 조회
        region_data = self._get_region_data(region)

        # 연도별 통계 표 생성
        yearly_table = self._generate_yearly_table(analysis.yearly_summaries)

        # 카테고리별 섹션 포맷
        category_sections = self._format_category_sections(analysis.category_analyses)

        # 그래프 설명 문단
        chart_desc = await self._generate_chart_description(analysis)

        # 지역 컨텍스트 구성
        region_context = ""
        target_audience = "일반 부동산 관심층"
        if region_data:
            desc = region_data.get("description", "")
            audience = region_data.get("target_audience", "일반 투자자 및 실거주자")
            target_audience = audience
            focus_points = region_data.get("focus_points", [])
            focus_str = "\n".join([f"- {p}" for p in focus_points])
            region_context = f"\n[지역 전문 정보]\n- 지역 특징: {desc}\n- 타겟 독자: {audience}\n- 핵심 포인트:\n{focus_str}\n"

        # 블로그 본문 생성 (구조화 데이터 기반)
        system_prompt = f"""당신은 '{region}' 지역 부동산 전문가이자 블로그 작가입니다.
주독자층: {target_audience}

아래 구조화된 데이터를 바탕으로 SEO 최적화된 블로그 글을 작성하세요.

{region_context}

작성 지침:
1. Markdown 형식 사용 (H2, H3, 리스트, 표 등)
2. 서론에서 독자의 흥미를 끄는 훅(Hook) 사용
3. 연도별 이슈 요약 표를 포함
4. 카테고리별 호재/악재 분석을 상세히 서술
5. 그래프 설명 문단을 자연스럽게 삽입
6. 투자 인사이트와 결론을 포함
7. 글자 수는 약 2500자 이상으로 작성
8. 중요한 내용은 **강조** 처리
9. {target_audience}의 눈높이에 맞게 작성"""

        user_prompt = f"""'{region}' 지역의 개발 이벤트 분석({analysis.period}) 블로그 글을 작성해주세요.

[연도별 통계]
{yearly_table}

[카테고리별 분석 데이터]
{category_sections}

[그래프 설명]
{chart_desc}

[전체 통계]
- 총 호재: {analysis.total_positive}건
- 총 악재: {analysis.total_negative}건
- 가장 활발한 연도: {analysis.most_active_year}년

사용자 요청: "{user_query}"

위 데이터를 활용하여 독자에게 실질적인 도움이 되는 블로그 글을 작성해주세요."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            response = await self.llm.ainvoke(messages)
            blog_content = response.content
        except Exception as e:
            print(f"[콘텐츠 생성 오류]: {e}")
            # 폴백: 구조화된 데이터를 직접 마크다운으로 변환
            blog_content = f"# {region} 개발 이벤트 분석\n\n{yearly_table}\n\n{category_sections}\n\n{chart_desc}"

        # 제목 생성
        if custom_title:
            blog_title = custom_title
        else:
            blog_title = await self._generate_title(
                region, policy_issues, user_query, needs_classification=True
            )

        # 카테고리 / 해시태그 / 메타 설명
        category = await self._classify_category(blog_content)
        tags = await self._generate_hashtags(blog_content)
        meta_description = await self._generate_meta_description(
            region, policy_issues, user_query
        )

        # 호재/악재 분리 (하위 호환)
        positive_issues = [i for i in policy_issues if hasattr(i, 'sentiment') and i.sentiment == "positive"]
        negative_issues = [i for i in policy_issues if hasattr(i, 'sentiment') and i.sentiment == "negative"]

        # 이미지 경로 (그래프 이미지 포함)
        image_paths = []
        if analysis.chart_image_path:
            image_paths.append(analysis.chart_image_path)

        return RegionalAnalysisContent(
            region=region,
            analysis_date=datetime.now(),
            positive_issues=positive_issues,
            negative_issues=negative_issues,
            blog_title=blog_title,
            blog_content=blog_content,
            category=category,
            tags=tags,
            meta_description=meta_description,
            image_paths=image_paths,
        )

    async def _generate_chart_description(
        self, analysis: DevelopmentEventAnalysis
    ) -> str:
        """그래프 데이터를 기반으로 설명 문단을 생성합니다."""
        if not analysis.chart_data:
            return ""

        chart_summary = "\n".join(
            [f"- {d['year']}년: 호재 {d['positive']}건, 악재 {d['negative']}건" for d in analysis.chart_data]
        )

        prompt = f"""다음 연도별 호재/악재 통계를 기반으로 그래프 설명 문단(2~3문장)을 작성하세요.

지역: {analysis.region}
분석 기간: {analysis.period}

{chart_summary}

총 호재: {analysis.total_positive}건, 총 악재: {analysis.total_negative}건
가장 활발한 연도: {analysis.most_active_year}년

설명 문단만 반환하세요 (따옴표나 다른 표시 없이)."""

        try:
            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            return response.content.strip()
        except Exception as e:
            print(f"[그래프 설명 생성 오류]: {e}")
            return f"{analysis.period} 기간 동안 총 {analysis.total_positive}건의 호재와 {analysis.total_negative}건의 악재가 확인되었습니다."

    def _generate_yearly_table(self, yearly_summaries: List[YearlyEventSummary]) -> str:
        """연도별 통계를 마크다운 표 + 텍스트 형식으로 변환합니다."""
        if not yearly_summaries:
            return "(연도별 데이터 없음)"

        lines = []

        # 텍스트 형식 (사용자 요구 형식)
        lines.append("### 연도별 개발 이슈 요약")
        lines.append("")
        for ys in yearly_summaries:
            event_parts = []
            pos_count = 0
            neg_count = 0
            for event in ys.events:
                if event.event_type == "positive":
                    pos_count += 1
                    event_parts.append(f"{event.event_name}(호재 {pos_count})")
                else:
                    neg_count += 1
                    event_parts.append(f"{event.event_name}(악재 {neg_count})")
            events_str = ", ".join(event_parts)
            lines.append(f"- **{ys.year}년**: {events_str}")

        lines.append("")

        # 마크다운 표
        lines.append("| 연도 | 호재 | 악재 | 합계 |")
        lines.append("|------|------|------|------|")
        for ys in yearly_summaries:
            total = ys.positive + ys.negative
            lines.append(f"| {ys.year} | {ys.positive}건 | {ys.negative}건 | {total}건 |")

        return "\n".join(lines)

    def _format_category_sections(self, category_analyses: List[CategoryAnalysis]) -> str:
        """카테고리별 분석을 마크다운 섹션으로 포맷합니다."""
        if not category_analyses:
            return "(카테고리별 분석 없음)"

        sections = []
        for ca in category_analyses:
            emoji = "✅" if ca.event_type == "positive" else "⚠️"
            section = f"### {emoji} {ca.category}\n"
            section += "내용:\n"
            for desc in ca.descriptions:
                section += f'\n"{desc}"\n'
            tags_str = " ".join(ca.tags)
            section += f"\n태그: {tags_str}\n"
            sections.append(section)

        return "\n".join(sections)

    # ========================================================
    # Fallback
    # ========================================================

    def _generate_fallback_content(
        self,
        region: str,
        policy_issues: List[PolicyIssue],
    ) -> str:
        """LLM 실패 시 폴백 콘텐츠 생성."""
        content = f"# {region} 부동산 정책 분석\n\n"

        positive_issues = [i for i in policy_issues if i.sentiment == "positive"]
        negative_issues = [i for i in policy_issues if i.sentiment == "negative"]

        if positive_issues:
            content += "## 호재\n\n"
            for issue in positive_issues:
                content += f"### {issue.title}\n\n{issue.summary}\n\n"

        if negative_issues:
            content += "## 악재\n\n"
            for issue in negative_issues:
                content += f"### {issue.title}\n\n{issue.summary}\n\n"

        return content

    # ========================================================
    # 하위 호환성 (공개 메서드)
    # ========================================================

    def classify_category(self, content: str) -> str:
        """동기식 카테고리 분류 (하위 호환성)."""
        import asyncio
        return asyncio.run(self._classify_category(content))

    def generate_hashtags(self, content: str, max_tags: int = 10) -> List[str]:
        """동기식 해시태그 생성 (하위 호환성)."""
        import asyncio
        return asyncio.run(self._generate_hashtags(content, max_tags))
