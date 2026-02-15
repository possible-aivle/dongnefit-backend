"""SEO scoring engine with deterministic algorithms."""

import re
from typing import Any

from .models import BlogDraft, SEOScoreBreakdown


class SEOScorer:
    """결정적 알고리즘 기반 SEO 점수 계산 엔진."""

    # 점수 가중치
    WEIGHTS = {
        "title": 20,
        "content_structure": 25,
        "keyword": 20,
        "readability": 15,
        "metadata": 20,
    }

    # 최적 값 기준
    OPTIMAL_TITLE_LENGTH_MIN = 25
    OPTIMAL_TITLE_LENGTH_MAX = 60
    OPTIMAL_KEYWORD_DENSITY_MIN = 1.0
    OPTIMAL_KEYWORD_DENSITY_MAX = 3.0
    OPTIMAL_TAGS_MIN = 5
    OPTIMAL_TAGS_MAX = 10
    OPTIMAL_META_DESC_MIN = 150
    OPTIMAL_META_DESC_MAX = 160

    def __init__(self):
        """Initialize SEO scorer."""
        self.deductions: list[str] = []
        self.recommendations: list[str] = []

    def calculate_score(self, draft: BlogDraft) -> SEOScoreBreakdown:
        """
        블로그 초안의 SEO 점수를 계산합니다.

        Args:
            draft: 블로그 초안

        Returns:
            SEO 점수 breakdown
        """
        self.deductions = []
        self.recommendations = []

        # 각 항목별 점수 계산
        title_score = self._score_title(draft)
        structure_score = self._score_content_structure(draft)
        keyword_score = self._score_keyword_optimization(draft)
        readability_score = self._score_readability(draft)
        metadata_score = self._score_metadata(draft)

        # 총점 계산
        total_score = int(
            title_score
            + structure_score
            + keyword_score
            + readability_score
            + metadata_score
        )

        return SEOScoreBreakdown(
            total_score=total_score,
            title_score=title_score,
            content_structure_score=structure_score,
            keyword_optimization_score=keyword_score,
            readability_score=readability_score,
            metadata_score=metadata_score,
            deductions=self.deductions.copy(),
            recommendations=self.recommendations.copy(),
        )

    def _score_title(self, draft: BlogDraft) -> float:
        """
        제목 최적화 점수 계산 (최대 20점).

        평가 항목:
        - 타겟 키워드 포함 (10점)
        - 최적 길이 (5점)
        - 숫자/특수문자 활용 (3점)
        - 클릭 유도성 (2점)
        """
        score = 0.0
        title = draft.title
        title_len = len(title)

        # 1. 타겟 키워드 포함 (10점)
        if draft.target_keyword.lower() in title.lower():
            score += 10
        else:
            self.deductions.append(f"제목에 타겟 키워드 '{draft.target_keyword}' 미포함 (-10점)")
            self.recommendations.append(
                f"제목에 '{draft.target_keyword}' 키워드를 자연스럽게 포함시키세요"
            )

        # 2. 최적 길이 (5점)
        if self.OPTIMAL_TITLE_LENGTH_MIN <= title_len <= self.OPTIMAL_TITLE_LENGTH_MAX:
            score += 5
        elif title_len < self.OPTIMAL_TITLE_LENGTH_MIN:
            penalty = min(3, (self.OPTIMAL_TITLE_LENGTH_MIN - title_len) // 5)
            score += 5 - penalty
            self.deductions.append(f"제목이 너무 짧음 ({title_len}자, -{penalty}점)")
            self.recommendations.append(
                f"제목을 {self.OPTIMAL_TITLE_LENGTH_MIN}-{self.OPTIMAL_TITLE_LENGTH_MAX}자로 작성하세요"
            )
        else:
            penalty = min(3, (title_len - self.OPTIMAL_TITLE_LENGTH_MAX) // 10)
            score += 5 - penalty
            self.deductions.append(f"제목이 너무 김 ({title_len}자, -{penalty}점)")
            self.recommendations.append(
                f"제목을 {self.OPTIMAL_TITLE_LENGTH_MAX}자 이내로 줄이세요"
            )

        # 3. 숫자 활용 (3점)
        if re.search(r"\d+", title):
            score += 3
        else:
            self.recommendations.append("제목에 숫자를 포함하면 클릭률이 향상됩니다")

        # 4. 클릭 유도 키워드 (2점)
        cta_keywords = [
            "가이드",
            "방법",
            "완벽",
            "비법",
            "총정리",
            "꿀팁",
            "필수",
            "추천",
            "베스트",
        ]
        if any(keyword in title for keyword in cta_keywords):
            score += 2
        else:
            self.recommendations.append(
                "제목에 '가이드', '방법', '총정리' 등의 클릭 유도 키워드를 추가하세요"
            )

        return min(score, self.WEIGHTS["title"])

    def _score_content_structure(self, draft: BlogDraft) -> float:
        """
        콘텐츠 구조 점수 계산 (최대 25점).

        평가 항목:
        - H2/H3 헤딩 구조 (10점)
        - 단락 구조 (8점)
        - 서식 활용 (7점)
        """
        score = 0.0
        content = draft.content

        # 1. H2/H3 헤딩 구조 (10점)
        h2_count = len(re.findall(r"^##\s+.+$", content, re.MULTILINE))
        h3_count = len(re.findall(r"^###\s+.+$", content, re.MULTILINE))

        if 3 <= h2_count <= 7:
            score += 7
        elif h2_count < 3:
            penalty = min(5, (3 - h2_count) * 2)
            score += 7 - penalty
            self.deductions.append(f"H2 헤딩 부족 ({h2_count}개, -{penalty}점)")
            self.recommendations.append("H2 헤딩을 3-7개 작성하여 구조를 명확히 하세요")
        else:
            penalty = min(3, (h2_count - 7))
            score += 7 - penalty
            self.deductions.append(f"H2 헤딩 과다 ({h2_count}개, -{penalty}점)")

        if h3_count > 0:
            score += 3
        else:
            self.recommendations.append("H3 헤딩으로 하위 구조를 추가하세요")

        # 2. 단락 구조 (8점)
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        avg_paragraph_length = (
            sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0
        )

        if 100 <= avg_paragraph_length <= 300:
            score += 8
        elif avg_paragraph_length < 100:
            penalty = min(4, (100 - avg_paragraph_length) // 20)
            score += 8 - penalty
            self.deductions.append(f"단락이 너무 짧음 (평균 {avg_paragraph_length:.0f}자, -{penalty}점)")
            self.recommendations.append("단락을 100-300자로 작성하세요")
        else:
            penalty = min(4, (avg_paragraph_length - 300) // 50)
            score += 8 - penalty
            self.deductions.append(f"단락이 너무 김 (평균 {avg_paragraph_length:.0f}자, -{penalty}점)")
            self.recommendations.append("긴 단락을 나누어 가독성을 높이세요")

        # 3. 서식 활용 (7점)
        format_score = 0
        if re.search(r"^\d+\.", content, re.MULTILINE) or re.search(
            r"^[-*]\s", content, re.MULTILINE
        ):
            format_score += 4  # 리스트 사용
        else:
            self.recommendations.append("리스트를 활용하여 정보를 구조화하세요")

        if re.search(r"\*\*.+\*\*", content):
            format_score += 2  # 강조 사용
        else:
            self.recommendations.append("중요한 내용은 볼드체로 강조하세요")

        if re.search(r"\|.+\|", content):
            format_score += 1  # 표 사용

        score += format_score

        return min(score, self.WEIGHTS["content_structure"])

    def _score_keyword_optimization(self, draft: BlogDraft) -> float:
        """
        키워드 최적화 점수 계산 (최대 20점).

        평가 항목:
        - 키워드 밀도 (10점)
        - 첫 100단어 내 키워드 포함 (5점)
        - 키워드 자연스러운 분포 (5점)
        """
        score = 0.0
        content = draft.content
        keyword = draft.target_keyword.lower()

        # 텍스트에서 코드 블록 제거
        clean_content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
        clean_content = re.sub(r"`[^`]+`", "", clean_content)

        # 단어 수 계산
        words = clean_content.split()
        word_count = len(words)

        if word_count == 0:
            self.deductions.append("콘텐츠가 너무 짧음")
            return 0.0

        # 키워드 등장 횟수
        keyword_count = clean_content.lower().count(keyword)

        # 1. 키워드 밀도 (10점)
        keyword_density = (keyword_count / word_count) * 100

        if self.OPTIMAL_KEYWORD_DENSITY_MIN <= keyword_density <= self.OPTIMAL_KEYWORD_DENSITY_MAX:
            score += 10
        elif keyword_density < self.OPTIMAL_KEYWORD_DENSITY_MIN:
            penalty = min(7, int((self.OPTIMAL_KEYWORD_DENSITY_MIN - keyword_density) * 3))
            score += 10 - penalty
            self.deductions.append(f"키워드 밀도 부족 ({keyword_density:.1f}%, -{penalty}점)")
            self.recommendations.append(
                f"타겟 키워드를 {int(word_count * self.OPTIMAL_KEYWORD_DENSITY_MIN / 100)}회 이상 사용하세요"
            )
        else:
            penalty = min(8, int((keyword_density - self.OPTIMAL_KEYWORD_DENSITY_MAX) * 2))
            score += 10 - penalty
            self.deductions.append(f"키워드 과다 사용 ({keyword_density:.1f}%, -{penalty}점)")
            self.recommendations.append("키워드 스팸을 피하고 동의어를 활용하세요")

        # 2. 첫 100단어 내 키워드 포함 (5점)
        first_100_words = " ".join(words[:100]).lower()
        if keyword in first_100_words:
            score += 5
        else:
            self.deductions.append("첫 100단어 내 키워드 미포함 (-5점)")
            self.recommendations.append("첫 문단에 타겟 키워드를 포함시키세요")

        # 3. 키워드 분포 (5점)
        if keyword_count > 0:
            # 콘텐츠를 3등분하여 각 부분에 키워드가 있는지 확인
            third = len(clean_content) // 3
            part1 = clean_content[:third].lower()
            part2 = clean_content[third : third * 2].lower()
            part3 = clean_content[third * 2 :].lower()

            distribution_score = 0
            if keyword in part1:
                distribution_score += 2
            if keyword in part2:
                distribution_score += 2
            if keyword in part3:
                distribution_score += 1

            score += distribution_score

            if distribution_score < 5:
                self.recommendations.append("키워드를 콘텐츠 전체에 고르게 분포시키세요")
        else:
            self.deductions.append("콘텐츠에 타겟 키워드 미포함 (-5점)")
            self.recommendations.append("본문에 타겟 키워드를 추가하세요")

        return min(score, self.WEIGHTS["keyword"])

    def _score_readability(self, draft: BlogDraft) -> float:
        """
        가독성 점수 계산 (최대 15점).

        평가 항목:
        - 문장 길이 (7점)
        - 단락당 문장 수 (5점)
        - 전문용어 빈도 (3점)
        """
        score = 0.0
        content = draft.content

        # 코드 블록 제거
        clean_content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)

        # 문장 분리
        sentences = re.split(r"[.!?]\s+", clean_content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            self.deductions.append("콘텐츠 부족")
            return 0.0

        # 1. 문장 길이 (7점)
        avg_sentence_length = sum(len(s) for s in sentences) / len(sentences)

        if 30 <= avg_sentence_length <= 80:
            score += 7
        elif avg_sentence_length < 30:
            penalty = min(3, (30 - avg_sentence_length) // 10)
            score += 7 - penalty
            self.recommendations.append("문장을 좀 더 풍부하게 작성하세요")
        else:
            penalty = min(5, (avg_sentence_length - 80) // 20)
            score += 7 - penalty
            self.deductions.append(f"문장이 너무 김 (평균 {avg_sentence_length:.0f}자, -{penalty}점)")
            self.recommendations.append("긴 문장을 나누어 가독성을 높이세요")

        # 2. 단락당 문장 수 (5점)
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        if paragraphs:
            sentences_per_paragraph = len(sentences) / len(paragraphs)
            if 2 <= sentences_per_paragraph <= 5:
                score += 5
            elif sentences_per_paragraph < 2:
                penalty = min(3, (2 - sentences_per_paragraph))
                score += 5 - penalty
                self.recommendations.append("단락을 좀 더 상세하게 작성하세요")
            else:
                penalty = min(3, (sentences_per_paragraph - 5) // 2)
                score += 5 - penalty
                self.recommendations.append("긴 단락을 나누어 가독성을 높이세요")

        # 3. 전문용어 빈도 (3점) - 간단한 휴리스틱
        # 한자어나 영어 단어 비율로 측정
        words = clean_content.split()
        if words:
            # 영어 단어 비율 (한글 블로그 기준)
            english_words = len(re.findall(r"\b[a-zA-Z]{4,}\b", clean_content))
            english_ratio = english_words / len(words)

            if english_ratio < 0.1:
                score += 3
            elif english_ratio < 0.2:
                score += 2
            else:
                score += 1
                self.recommendations.append("전문용어는 설명과 함께 사용하세요")

        return min(score, self.WEIGHTS["readability"])

    def _score_metadata(self, draft: BlogDraft) -> float:
        """
        메타데이터 점수 계산 (최대 20점).

        평가 항목:
        - 카테고리 관련성 (8점)
        - 태그 개수 (7점)
        - 메타 설명 (5점)
        """
        score = 0.0

        # 1. 카테고리 관련성 (8점)
        # 카테고리와 키워드의 관련성 (간단한 휴리스틱)
        if draft.target_keyword.lower() in draft.category.lower():
            score += 8
        elif any(
            word in draft.category.lower()
            for word in draft.target_keyword.lower().split()
        ):
            score += 5
            self.recommendations.append("카테고리를 타겟 키워드와 더 관련성 있게 설정하세요")
        else:
            score += 3
            self.deductions.append("카테고리와 타겟 키워드 관련성 낮음 (-5점)")
            self.recommendations.append("카테고리를 타겟 키워드와 관련성 있게 설정하세요")

        # 2. 태그 개수 (7점)
        tag_count = len(draft.tags)
        if self.OPTIMAL_TAGS_MIN <= tag_count <= self.OPTIMAL_TAGS_MAX:
            score += 7
        elif tag_count < self.OPTIMAL_TAGS_MIN:
            penalty = min(5, (self.OPTIMAL_TAGS_MIN - tag_count) * 2)
            score += 7 - penalty
            self.deductions.append(f"태그 부족 ({tag_count}개, -{penalty}점)")
            self.recommendations.append(f"태그를 {self.OPTIMAL_TAGS_MIN}개 이상 추가하세요")
        else:
            penalty = min(3, (tag_count - self.OPTIMAL_TAGS_MAX))
            score += 7 - penalty
            self.deductions.append(f"태그 과다 ({tag_count}개, -{penalty}점)")
            self.recommendations.append("중요한 태그만 선별하세요")

        # 3. 메타 설명 (5점)
        if draft.meta_description:
            desc_len = len(draft.meta_description)
            if self.OPTIMAL_META_DESC_MIN <= desc_len <= self.OPTIMAL_META_DESC_MAX:
                score += 5
            elif desc_len < self.OPTIMAL_META_DESC_MIN:
                penalty = min(3, (self.OPTIMAL_META_DESC_MIN - desc_len) // 20)
                score += 5 - penalty
                self.recommendations.append(
                    f"메타 설명을 {self.OPTIMAL_META_DESC_MIN}자 이상으로 작성하세요"
                )
            else:
                penalty = min(2, (desc_len - self.OPTIMAL_META_DESC_MAX) // 20)
                score += 5 - penalty
                self.recommendations.append(
                    f"메타 설명을 {self.OPTIMAL_META_DESC_MAX}자 이내로 줄이세요"
                )

            # 메타 설명에 키워드 포함 여부
            if draft.target_keyword.lower() not in draft.meta_description.lower():
                self.recommendations.append("메타 설명에 타겟 키워드를 포함시키세요")
        else:
            self.deductions.append("메타 설명 없음 (-5점)")
            self.recommendations.append("메타 설명을 작성하세요 (150-160자)")

        return min(score, self.WEIGHTS["metadata"])
