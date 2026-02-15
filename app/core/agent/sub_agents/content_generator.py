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
from app.core.agent.models import PolicyIssue, RegionalAnalysisContent


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

        # 블로그 본문 생성
        blog_content = await self._generate_blog_content(
            region, policy_issues, positive_issues, negative_issues, user_query, needs_classification
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

    async def _generate_blog_content(
        self,
        region: str,
        all_issues: List[PolicyIssue],
        positive_issues: List[PolicyIssue],
        negative_issues: List[PolicyIssue],
        user_query: str,
        needs_classification: bool,
    ) -> str:
        """블로그 본문 생성 (사용자 의도에 따라 유연하게)."""

        if needs_classification:
            # 호재/악재 분류 모드
            system_prompt = """당신은 전문 부동산 블로거입니다.

주어진 지역의 정책 호재와 악재를 바탕으로 독자들에게 유익한 블로그 글을 작성하세요.

글 구성:
1. 서론: 해당 지역의 최근 동향 소개
2. 호재 분석: 각 호재를 섹션으로 나누어 상세 설명
3. 악재 분석: 각 악재를 섹션으로 나누어 상세 설명
4. 결론: 종합 의견 및 투자 시사점

작성 지침:
- Markdown 형식 사용 (H2, H3, 리스트 등)
- 각 이슈마다 출처 링크 포함
- 전문가적인 내용이지만 일반인도 이해하기 쉽게 작성
- 중요한 내용은 **강조** 처리
- 목록(-)이나 표를 활용하여 정보 정리
- 소제목(##)을 사용하여 가독성을 높이기
- SEO를 고려한 키워드 자연스러운 배치
- 글자 수는 약 2000자 정도로 작성"""

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

            user_prompt = f"""다음 정보를 바탕으로 '{region}' 지역 분석 블로그 글을 작성하세요.

**호재:**
{positive_text if positive_text else "(없음)"}

**악재:**
{negative_text if negative_text else "(없음)"}

독자들이 이해하기 쉽고, 실질적인 정보를 제공하는 글을 작성하세요."""
        else:
            if not all_issues:
                # 데이터가 없는 경우: 일반 키워드/주제 기반 생성 (구 Tistory 기능 통합)
                system_prompt = """당신은 전문 부동산 블로거입니다.
주어진 주제에 대해 자세하고 유익한 블로그 글을 작성해주세요.

작성 지침:
1. 전문가적인 내용이지만 일반인도 이해하기 쉽게 작성해주세요.
2. 소제목(##)을 사용하여 가독성을 높여주세요.
3. 중요한 내용은 **강조**해주세요.
4. 목록(-)이나 표를 사용해 정보를 정리해주세요.
5. 실제 사례나 통계 자료가 있다면(가상의 예시라도) 포함해주세요.
6. 마지막에 결론과 함께 독자에게 도움이 될 만한 조언을 추가해주세요.
7. 마크다운 형식으로 작성해주세요.
8. 글자 수는 약 2000자 정도로 작성해주세요.
"""
                user_prompt = f"""주제: {region} {user_query}

위 주제에 대한 블로그 글을 작성해주세요.
블로그 글은 서론, 본론, 결론으로 구성하고, 필요한 경우 하위 섹션을 추가해주세요.
가독성을 높이기 위해 적절한 소제목(##)을 사용해주세요.
현재 수집된 구체적인 정책 데이터가 없으므로, 일반적인 부동산 지식과 통찰력을 바탕으로 작성해주세요."""

            else:
                # 일반 분석 모드 (호재/악재 분류 없음)
                system_prompt = """당신은 전문 부동산 블로거입니다.

사용자의 질문에 맞는 유익하고 전문적인 블로그 글을 작성하세요.

글 구성:
1. 서론: 주제 소개 및 배경
2. 본론: 주제에 맞는 다양한 분석 및 정보 (소제목으로 구분)
3. 결론: 종합 의견 및 실용적인 팁

작성 지침:
- Markdown 형식 사용 (H2, H3, 리스트 등)
- 전문가적인 내용이지만 일반인도 이해하기 쉽게 작성
- 중요한 내용은 **강조** 처리
- 목록(-)이나 표를 활용하여 정보 정리
- 소제목(##)을 사용하여 가독성을 높이기
- SEO를 고려한 키워드 자연스러운 배치
- 글자 수는 약 2000자 정도로 작성"""

                issues_text = "\n".join(
                    [
                        f"- [{issue.category}] {issue.title}: {issue.summary}"
                        for issue in all_issues
                    ]
                )

                user_prompt = f"""사용자 요청: "{user_query}"

'{region}' 지역에 대한 다음 정보를 참고하여 블로그 글을 작성하세요:

**관련 이슈:**
{issues_text}

사용자의 요청에 맞게 유용하고 실질적인 정보를 제공하세요."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            response = await self.llm.ainvoke(messages)
            return response.content

        except Exception as e:
            print(f"[콘텐츠 생성 오류]: {e}")
            return self._generate_fallback_content(
                region, all_issues if not needs_classification else positive_issues + negative_issues
            )

    async def _generate_title(
        self,
        region: str,
        policy_issues: List[PolicyIssue],
        user_query: str,
        needs_classification: bool,
    ) -> str:
        """블로그 제목 생성 (사용자 의도 반영)."""
        try:
            if needs_classification:
                positive_count = len([i for i in policy_issues if i.sentiment == "positive"])
                negative_count = len([i for i in policy_issues if i.sentiment == "negative"])

                prompt = f"""'{region}' 지역의 부동산 정책 분석 블로그 제목을 생성하세요.

주요 이슈:
- 호재 {positive_count}개
- 악재 {negative_count}개

제목 조건:
- 25-60자 길이
- 클릭 유도성 있는 표현 사용
- 숫자 포함
- SEO 고려

제목만 반환하세요 (다른 설명 없이)."""
            else:
                prompt = f"""사용자 요청: "{user_query}"

'{region}' 지역에 대한 블로그 제목을 생성하세요.

제목 조건:
- 25-60자 길이
- 클릭 유도성 있는 표현 사용
- 사용자 요청 내용 반영
- SEO 고려

제목만 반환하세요 (다른 설명 없이)."""

            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            return response.content.strip().strip('"')

        except Exception as e:
            print(f"[제목 생성 오류]: {e}")
            if needs_classification:
                positive_count = len([i for i in policy_issues if i.sentiment == "positive"])
                negative_count = len([i for i in policy_issues if i.sentiment == "negative"])
                return f"{region} 부동산 분석: {positive_count}가지 호재와 {negative_count}가지 악재"
            else:
                return f"{region} {user_query}"

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
