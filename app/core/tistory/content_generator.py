import os
import random
import re
import uuid
from datetime import datetime
from typing import Dict, List, Tuple

import requests
from krwordrank.word import summarize_with_keywords  # type: ignore
from openai import OpenAI


class ContentGenerator:
    """
    블로그 콘텐츠 생성을 담당하는 클래스
    - 키워드 추출
    - 제목 생성
    - 본문 생성
    - 카테고리 분류
    - 해시태그 생성
    """

    ENABLE_IMAGE_GENERATION = False  # 이미지 생성 활성화 여부

    def __init__(self, openai_api_key: str, model: str = "gpt-3.5-turbo"):
        """
        ContentGenerator 초기화

        Args:
            openai_api_key (str): OpenAI API 키
            model (str, optional): 사용할 모델명. 기본값은 "gpt-3.5-turbo"
        """
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model
        self.image_style = "realistic photo, high quality, professional photography, 8k"

    def _call_openai(
        self, messages: List[Dict[str, str]], temperature: float = 0.7
    ) -> str:
        """
        OpenAI API를 호출하는 내부 메서드

        Args:
            messages (List[Dict[str, str]]): 대화 메시지 목록
            temperature (float, optional): 생성 다양성 조절 (0.0 ~ 1.0). 기본값은 0.7

        Returns:
            str: 생성된 텍스트
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=2000,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[오류] OpenAI API 호출 중 오류 발생: {e}")
            raise

    def extract_keywords(self, texts: List[str], top_n: int = 5) -> List[str]:
        """
        텍스트에서 키워드를 추출하는 메서드

        Args:
            texts (List[str]): 키워드를 추출할 텍스트 리스트
            top_n (int, optional): 상위 N개 키워드 반환. 기본값은 5

        Returns:
            List[str]: 추출된 키워드 리스트
        """
        try:
            # 텍스트 전처리
            preprocessed_texts = []
            for text in texts:
                # 특수문자 제거 및 소문자 변환
                text = re.sub(r"[^\w\s]", " ", text.lower())
                # 다중 공백 제거
                text = re.sub(r"\s+", " ", text).strip()
                if text:
                    preprocessed_texts.append(text)

            # KR-WordRank를 사용한 키워드 추출
            keywords = summarize_with_keywords(
                preprocessed_texts, min_count=1, max_length=10
            )

            # 빈도수 기반으로 정렬하여 상위 N개 키워드 추출
            top_keywords = [
                keyword
                for keyword, _ in sorted(
                    keywords.items(), key=lambda x: x[1], reverse=True
                )[:top_n]
            ]

            print(f"[시스템] 키워드 추출 완료: {top_keywords}")
            return top_keywords

        except Exception as e:
            print(f"[오류] 키워드 추출 중 오류 발생: {e}")
            # 오류 발생 시 빈 리스트 반환
            return []

    def generate_title(self, keyword: str) -> str:
        """
        주제에 맞는 블로그 제목을 생성하는 메서드

        Args:
            keyword (str): 블로그 주제 키워드

        Returns:
            str: 생성된 블로그 제목
        """
        system_prompt = (
            "당신은 전문 블로거입니다. 주어진 주제에 대한 매력적이고 SEO에 최적화된 블로그 제목을 생성해주세요. "
            "제목은 30자 이내로 작성하고, 클릭 유도 문구를 포함해주세요. "
            "제목만 출력해주세요."
        )

        user_prompt = (
            f"주제: {keyword}\n"
            f"이 주제에 대한 블로그 제목을 3가지 추천해주세요. 가장 좋은 제목 1개만 선택해서 제목만 출력해주세요."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        print(f"[시스템] '{keyword}'에 대한 제목 생성 중...")
        return self._call_openai(messages, temperature=0.7)

    def _generate_image(self, prompt: str) -> str:
        """
        DALL-E를 사용하여 이미지를 생성하고 URL을 반환합니다.

        Args:
            prompt (str): 이미지 생성에 사용할 프롬프트

        Returns:
            str: 생성된 이미지의 URL
        """
        if not self.ENABLE_IMAGE_GENERATION:
            print("[안내] 이미지 생성이 비활성화되어 있습니다.")
            return ""

        try:
            response = self.client.images.generate(
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
        """
        이미지 URL에서 이미지를 다운로드하여 로컬에 저장합니다.

        Args:
            image_url (str): 다운로드할 이미지 URL
            save_dir (str, optional): 저장할 디렉토리. 기본값은 "images" (현재 모듈 폴더 내)
        """
        if save_dir == "images":
            # tistory 폴더 내부의 images 폴더로 변경
            save_dir = os.path.join(os.path.dirname(__file__), "images")

        if not image_url:
            return ""

        try:
            # 저장 디렉토리 생성 (존재하지 않는 경우)
            os.makedirs(save_dir, exist_ok=True)

            # 고유한 파일명 생성 (타임스탬프 + UUID)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"dalle_{timestamp}_{unique_id}.png"
            filepath = os.path.join(save_dir, filename)

            # 이미지 다운로드
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            # 파일로 저장
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
        """
        SEO 최적화된 방식으로 콘텐츠에 이미지를 삽입합니다.
        - 소제목(##)을 기준으로 섹션 분리
        - 각 섹션의 내용을 반영한 이미지 생성
        - 본문 중간중간에 자연스럽게 배치

        Args:
            content (str): 이미지가 삽입될 콘텐츠
            keyword (str): 이미지 생성에 사용할 키워드
            num_images (int, optional): 삽입할 이미지 수. 기본값은 3

        Returns:
            Tuple[str, list]: 이미지가 삽입된 콘텐츠와 생성된 이미지 로컬 경로 리스트
        """
        if num_images <= 0 or not self.ENABLE_IMAGE_GENERATION:
            return content, []

        # 1. 소제목(##) 기준으로 섹션 분리
        lines = content.split("\n")
        sections = []
        current_section = {"title": "", "content": []}

        for line in lines:
            if line.strip().startswith("##") and not line.strip().startswith("###"):
                # 이전 섹션 저장 (내용이 있는 경우에만)
                if current_section["content"]:
                    sections.append(current_section)
                # 새 섹션 시작
                current_section = {
                    "title": line.strip().replace("##", "").strip(),
                    "content": [line]
                }
            else:
                current_section["content"].append(line)

        # 마지막 섹션 저장
        if current_section["content"]:
            sections.append(current_section)

        print(f"[시스템] 총 {len(sections)}개 섹션 발견")
        for idx, sec in enumerate(sections):
            print(f"  섹션 {idx}: {sec['title'][:30] if sec['title'] else '(제목 없음)'}")

        # 섹션이 충분하지 않으면 기존 방식 사용
        if len(sections) < 2:
            print("[경고] 소제목이 충분하지 않아 단락 기준으로 이미지 배치")
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            if len(paragraphs) < 3:
                return content, []

            # 기존 로직 사용 (fallback)
            total_paragraphs = len(paragraphs)
            step = max(2, total_paragraphs // (num_images + 1))
            insert_positions = [
                step * (i + 1)
                for i in range(num_images)
                if step * (i + 1) < total_paragraphs
            ]

            print(f"[시스템] 단락 기준 이미지 삽입 위치: {insert_positions}")

            result = []
            image_paths = []
            image_count = 0

            for i, para in enumerate(paragraphs):
                result.append(para)
                if (image_count < len(insert_positions)
                    and i == insert_positions[image_count]):
                    image_prompt = f"{keyword} 관련 이미지, {para[:100]}"
                    print(f"[시스템] 이미지 생성 중 [{image_count+1}/{len(insert_positions)}]: 단락 {i} 뒤")

                    image_url = self._generate_image(image_prompt)
                    if image_url:
                        local_path = self._download_image(image_url)
                        if local_path:
                            alt_text = f"{keyword} 관련 이미지"
                            image_placeholder = f'{{{{IMAGE:{local_path}|{alt_text}}}}}'
                            result.append(image_placeholder)
                            image_paths.append(local_path)
                            print(f"[시스템] 이미지 저장 완료: {local_path}")
                    image_count += 1

            return "\n\n".join(result), image_paths

        # 2. SEO 최적화: 첫 번째 섹션(서론) 제외하고 이미지 삽입 위치 결정
        # 본문 섹션들(1번 인덱스부터)에 균등하게 분배
        body_sections = sections[1:]  # 첫 섹션(서론) 제외

        if len(body_sections) == 0:
            print("[경고] 본문 섹션이 없어 이미지를 삽입하지 않습니다")
            return content, []

        # 이미지 삽입 위치 계산 (균등 분배)
        num_insertable = min(num_images, len(body_sections))

        # 더 나은 분산을 위한 로직: body_sections를 균등하게 나눔
        if num_insertable == 1:
            # 이미지가 1개면 중간쯤에 배치
            insert_indices = [len(body_sections) // 2]
        elif num_insertable >= len(body_sections):
            # 이미지가 섹션보다 많거나 같으면 각 섹션마다 이미지
            insert_indices = list(range(len(body_sections)))
        else:
            # 이미지를 균등하게 분산
            step = len(body_sections) / num_insertable
            insert_indices = [int(step * i) for i in range(num_insertable)]

        print(f"[시스템] 서론 제외 {len(body_sections)}개 섹션에 {len(insert_indices)}개 이미지 배치")
        print(f"[시스템] 이미지 삽입 섹션 인덱스: {insert_indices}")

        # 3. 이미지 생성 및 삽입
        result_lines = []
        image_paths = []

        # 첫 번째 섹션(서론)은 이미지 없이 추가
        result_lines.extend(sections[0]["content"])
        print(f"[시스템] 서론 추가 완료 (이미지 없음)")

        # 본문 섹션들 처리
        images_to_insert = {}  # {섹션_인덱스: 이미지_정보}

        # 먼저 모든 이미지를 생성 (병렬 처리는 아니지만 명확하게)
        for img_idx, section_idx in enumerate(insert_indices):
            if section_idx >= len(body_sections):
                continue

            section = body_sections[section_idx]
            section_title = section["title"]
            section_content_preview = " ".join(section["content"][:5])[:200]

            # 섹션 제목과 내용을 반영한 이미지 프롬프트
            image_prompt = f"{keyword}, {section_title}, {section_content_preview}"
            print(f"[시스템] 이미지 생성 중 [{img_idx+1}/{len(insert_indices)}]: '{section_title}'")

            # DALL-E로 이미지 생성
            image_url = self._generate_image(image_prompt)

            if image_url:
                # 이미지 다운로드
                local_path = self._download_image(image_url)

                if local_path:
                    # SEO 친화적인 alt 텍스트 생성
                    alt_text = f"{keyword} - {section_title}"

                    images_to_insert[section_idx] = {
                        "path": local_path,
                        "alt": alt_text
                    }
                    image_paths.append(local_path)
                    print(f"[시스템] 이미지 저장 완료: {local_path}")
                    print(f"   섹션 '{section_title}' 뒤에 삽입 예정")
                else:
                    print(f"[오류] 이미지 다운로드 실패: '{section_title}'")
            else:
                print(f"[오류] 이미지 생성 실패: '{section_title}'")

        # 이제 섹션들을 추가하면서 해당 위치에 이미지 삽입
        for i, section in enumerate(body_sections):
            # 섹션 내용 추가
            result_lines.extend(section["content"])
            print(f"[시스템] 섹션 {i+1} 추가: '{section['title'][:30] if section['title'] else '(제목 없음)'}'")

            # 이 섹션 뒤에 이미지가 있으면 삽입
            if i in images_to_insert:
                img_info = images_to_insert[i]
                # 플레이스홀더 형식: {{IMAGE:로컬경로|alt텍스트}}
                image_placeholder = f"{{{{IMAGE:{img_info['path']}|{img_info['alt']}}}}}"
                result_lines.append("")  # 빈 줄
                result_lines.append(image_placeholder)
                result_lines.append("")  # 빈 줄
                print(f"[시스템] 이미지 삽입: 섹션 {i+1} 뒤")

        return "\n".join(result_lines), image_paths

    def generate_blog(
        self, keyword: str, length: int = 2000, num_images: int = 3
    ) -> Dict[str, any]:
        """
        주제에 맞는 블로그 본문을 생성하고 이미지를 삽입하는 메서드

        Args:
            keyword (str): 블로그 주제 키워드
            length (int, optional): 생성할 본문 길이. 기본값은 2000자
            num_images (int, optional): 삽입할 이미지 수. 기본값은 3개

        Returns:
            Dict: {
                'content': 생성된 블로그 본문 (마크다운 형식, 이미지는 {{IMAGE:경로}} 플레이스홀더로 표시),
                'images': 생성된 이미지 로컬 파일 경로 리스트
            }
        """
        # 1. 텍스트 콘텐츠 생성
        system_prompt = (
            "당신은 전문 부동산 블로거입니다. 주어진 주제에 대해 자세하고 유익한 블로그 글을 작성해주세요.\n"
            "작성 시 다음 사항을 지켜주세요:\n"
            "1. 전문가적인 내용이지만 일반인도 이해하기 쉽게 작성해주세요.\n"
            "2. 소제목(##)을 사용하여 가독성을 높여주세요.\n"
            "3. 중요한 내용은 **강조**해주세요.\n"
            "4. 목록(-)이나 표를 사용해 정보를 정리해주세요.\n"
            "5. 실제 사례나 통계 자료가 있다면 포함해주세요.\n"
            "6. 마지막에 결론과 함께 독자에게 도움이 될 만한 조언을 추가해주세요.\n"
            "7. 마크다운 형식으로 작성해주세요.\n"
            f"8. 글자 수는 약 {length}자 정도로 작성해주세요."
        )

        user_prompt = (
            f"주제: {keyword}\n"
            "위 주제에 대한 블로그 글을 작성해주세요. "
            "블로그 글은 서론, 본론, 결론으로 구성하고, 필요한 경우 하위 섹션을 추가해주세요. "
            "가독성을 높이기 위해 적절한 소제목(##)을 사용해주세요."
        )

        print(f"[시스템] '{keyword}'에 대한 본문 생성 중...")
        content = self._call_openai(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )

        # 2. 이미지 생성 및 삽입
        if num_images > 0 and self.ENABLE_IMAGE_GENERATION:
            print(f"[시스템] {num_images}개의 이미지 생성 및 삽입 중...")
            content, image_paths = self._insert_images(content, keyword, num_images)
            print(f"[시스템] {len(image_paths)}개의 이미지가 성공적으로 삽입되었습니다.")
        else:
            image_paths = []

        return {"content": content, "images": image_paths}

    def _classify_category(self, content: str) -> str:
        """
        블로그 글 내용을 기반으로 카테고리를 분류하는 메서드

        Args:
            content (str): 블로그 글 내용

        Returns:
            str: 분류된 카테고리
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
            "부동산 정책 및 이슈\n"
            "기타\n"
            "선택한 카테고리 이름만 출력해주세요."
        )

        # 내용이 길 경우 앞부분만 사용
        truncated_content = content[:1000] if len(content) > 1000 else content

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"블로그 글 내용:\n{truncated_content}"},
        ]

        return self._call_openai(messages, temperature=0.3)

    def _generate_hashtags(self, content: str, max_tags: int = 5) -> List[str]:
        """
        블로그 글 내용을 기반으로 해시태그를 생성하는 메서드

        Args:
            content (str): 블로그 글 내용
            max_tags (int, optional): 최대 해시태그 개수. 기본값은 5

        Returns:
            List[str]: 생성된 해시태그 리스트
        """
        system_prompt = (
            "당신은 소셜 미디어 마케팅 전문가입니다. 주어진 블로그 글을 분석하여 효과적인 해시태그를 생성해주세요.\n"
            "해시태그는 블로그 글의 주요 주제와 관련이 있어야 하며, 검색 최적화에 도움이 되어야 합니다.\n"
            f"총 {max_tags}개의 해시태그를 생성해주세요.\n"
            "생성된 해시태그는 쉼표로 구분하여 한 줄로 출력해주세요.\n"
            "해시태그의 앞에는 #이 없이 출력해주세요."
        )

        # 내용이 길 경우 앞부분만 사용
        truncated_content = content[:1500] if len(content) > 1500 else content

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"블로그 글 내용:\n{truncated_content}"},
        ]

        result = self._call_openai(messages, temperature=0.5)

        # 결과 파싱: 쉼표로 분리하고 공백 제거, #으로 시작하지 않는 태그에 # 추가
        tags = [tag.strip() for tag in result.split(",") if tag.strip()]
        tags = [f"#{tag[1:]}" if tag.startswith("#") else f"#{tag}" for tag in tags]

        # 중복 제거 및 최대 개수 제한
        unique_tags = list(dict.fromkeys(tags))  # 순서 유지하며 중복 제거
        return unique_tags[:max_tags]

    # 이전 버전과의 호환성을 위한 메서드
    def classify_category(self, content: str) -> str:
        """
        이전 버전과의 호환성을 유지하기 위한 메서드입니다.
        내부적으로는 새로운 _classify_category 메서드를 호출합니다.
        """
        return self._classify_category(content)

    # 이전 버전과의 호환성을 위한 메서드
    def generate_hashtags(self, content: str, max_tags: int = 5) -> List[str]:
        """
        이전 버전과의 호환성을 유지하기 위한 메서드입니다.
        내부적으로는 새로운 _generate_hashtags 메서드를 호출합니다.
        """
        return self._generate_hashtags(content, max_tags)
