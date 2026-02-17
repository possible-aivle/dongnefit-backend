"""Development Event Analysis Agent (호재/악재 분석 전용).

주소 또는 아파트명을 입력받아 해당 지역의 연도별 개발 이슈를 분석하고,
구조화된 데이터 + 그래프를 반환합니다.
"""

import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

from app.config import settings
from app.core.agent.models import (
    CategoryAnalysis,
    DevelopmentEvent,
    DevelopmentEventAnalysis,
    NewsArticle,
    YearlyEventSummary,
)


class DevelopmentEventAgent:
    """호재/악재 분석 전용 Agent.

    수집된 뉴스 기사를 기반으로 지역 개발 이벤트를 연도별로 분석하고,
    카테고리별 구조화된 결과와 시각화 데이터를 반환합니다.
    """

    # 카테고리 한/영 매핑
    CATEGORY_MAP = {
        "교통": "교통",
        "재건축": "재건축/재개발",
        "재개발": "재건축/재개발",
        "재건축/재개발": "재건축/재개발",
        "공급": "공급",
        "규제": "규제/정책",
        "정책": "규제/정책",
        "규제/정책": "규제/정책",
        "학군": "학군",
        "상업시설": "상업시설",
        "인프라": "생활 인프라",
        "생활 인프라": "생활 인프라",
        "기타": "기타",
    }

    def __init__(self, llm_provider: str = "openai"):
        """Initialize Development Event Agent.

        Args:
            llm_provider: "openai" or "anthropic"
        """
        if llm_provider == "anthropic" and settings.anthropic_api_key:
            self.llm = ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                api_key=settings.anthropic_api_key,
                temperature=0.3,
            )
        else:
            self.llm = ChatOpenAI(
                model="gpt-4o",
                api_key=settings.openai_api_key,
                temperature=0.3,
            )

    # ========================================================
    # Main Public Method
    # ========================================================

    async def analyze(
        self,
        region: str,
        articles: List[NewsArticle],
        policy_issues: list,
        user_query: str = "",
    ) -> DevelopmentEventAnalysis:
        """수집된 기사와 이슈를 바탕으로 연도별 개발 이벤트를 분석합니다.

        Args:
            region: 분석 대상 지역 (예: "서울 동작구 흑석동 A아파트")
            articles: 수집된 뉴스 기사 목록
            policy_issues: 추출된 정책 이슈 목록
            user_query: 사용자의 원래 쿼리

        Returns:
            DevelopmentEventAnalysis: 구조화된 분석 결과
        """
        print(f"\n[Development Event Agent] '{region}' 호재/악재 분석 시작...")

        # 1. 기사 + 이슈로부터 이벤트 추출
        events = await self._extract_events(region, articles, policy_issues)
        print(f"  [OK] {len(events)}개 개발 이벤트 추출")

        if not events:
            # 이벤트가 없는 경우 빈 분석 결과 반환
            return DevelopmentEventAnalysis(
                region=region,
                period="N/A",
                yearly_summaries=[],
                category_analyses=[],
                chart_data=[],
                total_positive=0,
                total_negative=0,
                most_active_year=0,
            )

        # 2. 연도별 그룹화 및 통계 생성
        yearly_summaries = self._build_yearly_summaries(events)

        # 3. 카테고리별 분석 생성
        category_analyses = await self._build_category_analyses(region, events)

        # 4. 통계 데이터 계산
        total_positive = sum(ys.positive for ys in yearly_summaries)
        total_negative = sum(ys.negative for ys in yearly_summaries)

        most_active_year = 0
        if yearly_summaries:
            most_active_year = max(
                yearly_summaries,
                key=lambda ys: ys.positive + ys.negative,
            ).year

        years = sorted([ys.year for ys in yearly_summaries])
        period = f"{years[0]}-{years[-1]}" if len(years) > 1 else str(years[0])

        # 5. 그래프용 JSON
        chart_data = [
            {"year": ys.year, "positive": ys.positive, "negative": ys.negative}
            for ys in yearly_summaries
        ]

        # 6. 막대 그래프 이미지 생성
        chart_image_path = self._generate_chart_image(region, period, chart_data)

        # 7. 연도별 요약 텍스트 출력
        self._print_yearly_summary(yearly_summaries)

        # 8. 카테고리별 결과 출력
        self._print_category_analyses(category_analyses)

        analysis = DevelopmentEventAnalysis(
            region=region,
            period=period,
            yearly_summaries=yearly_summaries,
            category_analyses=category_analyses,
            chart_data=chart_data,
            total_positive=total_positive,
            total_negative=total_negative,
            most_active_year=most_active_year,
            chart_image_path=chart_image_path,
        )

        print(f"\n  [OK] 분석 완료: 호재 {total_positive}건 / 악재 {total_negative}건")
        print(f"  [OK] 분석 기간: {period}")
        if chart_image_path:
            print(f"  [OK] 그래프 이미지: {chart_image_path}")

        return analysis

    # ========================================================
    # Event Extraction
    # ========================================================

    async def _extract_events(
        self,
        region: str,
        articles: List[NewsArticle],
        policy_issues: list,
    ) -> List[DevelopmentEvent]:
        """기사와 정책 이슈에서 개발 이벤트를 추출합니다."""

        # 기사 요약 텍스트 구성
        articles_text = ""
        for i, article in enumerate(articles[:30], 1):  # 최대 30개 기사
            year = article.publish_date.year if article.publish_date else datetime.now().year
            articles_text += f"\n[기사 {i}] ({year}년)\n제목: {article.title}\n내용: {article.content[:300]}\n"

        # 정책 이슈 텍스트 구성
        issues_text = ""
        for i, issue in enumerate(policy_issues, 1):
            sentiment_kr = "호재" if issue.sentiment == "positive" else "악재" if issue.sentiment == "negative" else "중립"
            issues_text += f"\n[이슈 {i}] {issue.title} ({sentiment_kr})\n카테고리: {issue.category}\n요약: {issue.summary}\n"

        current_year = datetime.now().year

        system_prompt = f"""당신은 부동산 개발 이슈 분석 전문가입니다.
주어진 뉴스 기사와 정책 이슈를 분석하여, '{region}' 지역과 관련된 개발 이벤트를 추출해주세요.

[추출할 이벤트 유형]
- 교통: GTX, 지하철 연장/신설, 도로 개통, BRT 등
- 재건축/재개발: 안전진단, 사업인가, 관리처분, 착공, 입주 등
- 공급: 신규 분양, 입주 물량, 택지 개발 등
- 규제/정책: 토지거래허가, 대출 규제, 세금 정책 변화 등
- 학군: 학교 신설, 학군 변화, 교육 시설 등
- 상업시설: 쇼핑몰, 백화점, 대형마트 착공/개장 등
- 생활 인프라: 병원, 공원, 문화시설, 도시계획 등
- 기타: 위 카테고리에 속하지 않는 이벤트

[분류 기준]
- positive (호재): 해당 지역 부동산 가치 상승에 기여하는 이벤트
- negative (악재): 해당 지역 부동산 가치 하락 또는 리스크 요인

[응답 형식 - JSON 배열]
반드시 아래 형식의 JSON 배열만 반환하세요. 다른 텍스트는 포함하지 마세요.

[
  {{
    "year": {current_year},
    "event_name": "이벤트명",
    "event_type": "positive 또는 negative",
    "category": "교통/재건축/재개발/공급/규제/정책/학군/상업시설/인프라/기타",
    "summary": "2~3줄 상세 요약 (사례나 근거 포함)",
    "tags": ["#태그1", "#태그2", "#태그3"]
  }}
]

주의사항:
- 최소 5개 이상의 이벤트를 추출하세요.
- 각 이벤트의 summary에는 근거와 배경을 포함하세요.
- tags는 각 이벤트별 3개 이상 생성하세요.
- year는 기사 발행 연도 또는 이벤트 예정 연도를 사용하세요.
- 미래 이벤트(예정/계획)도 포함할 수 있습니다.
"""

        user_prompt = f"""[분석 대상 지역]: {region}

[수집된 뉴스 기사]
{articles_text if articles_text else "(수집된 기사 없음)"}

[추출된 정책 이슈]
{issues_text if issues_text else "(추출된 이슈 없음)"}

위 데이터를 바탕으로 '{region}' 지역의 개발 이벤트를 JSON 배열로 추출해주세요."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            response = await self.llm.ainvoke(messages)
            events = self._parse_events_response(response.content)
            return events

        except Exception as e:
            print(f"  [FAIL] 이벤트 추출 실패: {e}")
            return []

    def _parse_events_response(self, content: str) -> List[DevelopmentEvent]:
        """LLM 응답에서 이벤트 JSON을 파싱합니다."""
        try:
            # JSON 블록 추출
            text = content.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            # 배열이 아닌 경우 배열로 감싸기
            if not text.startswith("["):
                text = f"[{text}]"

            raw_events = json.loads(text)

            events = []
            for raw in raw_events:
                try:
                    # 카테고리 정규화
                    category = self.CATEGORY_MAP.get(
                        raw.get("category", "기타"), "기타"
                    )

                    event = DevelopmentEvent(
                        year=int(raw.get("year", datetime.now().year)),
                        event_name=raw.get("event_name", ""),
                        event_type=raw.get("event_type", "positive"),
                        category=category,
                        summary=raw.get("summary", ""),
                        tags=raw.get("tags", []),
                        sources=raw.get("sources", []),
                    )
                    events.append(event)
                except Exception as e:
                    print(f"  [경고] 이벤트 파싱 실패: {e}")
                    continue

            return events

        except json.JSONDecodeError as e:
            print(f"  [경고] JSON 파싱 실패: {e}")
            return []

    # ========================================================
    # Yearly Summaries
    # ========================================================

    def _build_yearly_summaries(
        self, events: List[DevelopmentEvent]
    ) -> List[YearlyEventSummary]:
        """이벤트를 연도별로 그룹화하여 요약 통계를 생성합니다."""
        year_groups: Dict[int, List[DevelopmentEvent]] = defaultdict(list)
        for event in events:
            year_groups[event.year].append(event)

        summaries = []
        for year in sorted(year_groups.keys()):
            year_events = year_groups[year]
            positive = sum(1 for e in year_events if e.event_type == "positive")
            negative = sum(1 for e in year_events if e.event_type == "negative")

            summaries.append(
                YearlyEventSummary(
                    year=year,
                    positive=positive,
                    negative=negative,
                    events=year_events,
                )
            )

        return summaries

    def _print_yearly_summary(self, yearly_summaries: List[YearlyEventSummary]):
        """연도별 요약을 사용자 요구 형식으로 출력합니다."""
        print("\n" + "=" * 50)
        print("📊 연도별 개발 이슈 요약")
        print("=" * 50)

        for ys in yearly_summaries:
            # 이벤트 요약 문자열 구성
            event_parts = []
            positive_count = 0
            negative_count = 0

            for event in ys.events:
                if event.event_type == "positive":
                    positive_count += 1
                    event_parts.append(f"{event.event_name}(호재 {positive_count})")
                else:
                    negative_count += 1
                    event_parts.append(f"{event.event_name}(악재 {negative_count})")

            events_str = ", ".join(event_parts)
            print(f"{ys.year}년: {events_str}")

        print()

    # ========================================================
    # Category Analyses
    # ========================================================

    async def _build_category_analyses(
        self, region: str, events: List[DevelopmentEvent]
    ) -> List[CategoryAnalysis]:
        """이벤트를 카테고리+유형으로 그룹화하여 분석 결과를 생성합니다."""

        # 카테고리 + event_type 으로 그룹화
        groups: Dict[str, List[DevelopmentEvent]] = defaultdict(list)
        for event in events:
            if event.event_type == "positive":
                key = f"{event.category} 호재"
            else:
                key = f"{event.category} 리스크"
            groups[key].append(event)

        category_analyses = []

        for group_name, group_events in groups.items():
            event_type = "positive" if "호재" in group_name else "negative"

            # LLM을 사용하여 해당 카테고리의 분석 문단 생성
            descriptions = await self._generate_category_descriptions(
                region, group_name, group_events
            )

            # 태그 수집 (이벤트별 태그 병합 + 중복 제거)
            all_tags = []
            seen_tags = set()
            for event in group_events:
                for tag in event.tags:
                    tag_clean = tag if tag.startswith("#") else f"#{tag}"
                    if tag_clean not in seen_tags:
                        all_tags.append(tag_clean)
                        seen_tags.add(tag_clean)

            category_analyses.append(
                CategoryAnalysis(
                    category=group_name,
                    event_type=event_type,
                    descriptions=descriptions,
                    tags=all_tags,
                )
            )

        # 호재 먼저, 악재 나중에 정렬
        category_analyses.sort(key=lambda ca: (0 if ca.event_type == "positive" else 1, ca.category))

        return category_analyses

    async def _generate_category_descriptions(
        self,
        region: str,
        category_name: str,
        events: List[DevelopmentEvent],
    ) -> List[str]:
        """카테고리별 분석 설명 문단을 생성합니다."""

        events_text = "\n".join(
            [f"- {e.event_name} ({e.year}년): {e.summary}" for e in events]
        )

        prompt = f"""'{region}' 지역의 [{category_name}] 분석을 위한 설명 문단을 작성하세요.

[관련 이벤트 목록]
{events_text}

[작성 지침]
- 2~3개의 설명 문단을 작성하세요.
- 각 문단은 해당 카테고리의 핵심 인사이트를 담아야 합니다.
- 사례나 근거를 포함하여 신뢰성을 높이세요.
- 각 문단은 독립적으로 읽을 수 있어야 합니다.

[응답 형식]
JSON 배열로 문단들을 반환하세요. 다른 텍스트는 포함하지 마세요.
["문단1 내용", "문단2 내용", "문단3 내용"]
"""

        try:
            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)

            # JSON 파싱
            text = response.content.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            descriptions = json.loads(text)
            if isinstance(descriptions, list):
                return [str(d) for d in descriptions]
            return [str(descriptions)]

        except Exception as e:
            print(f"  [경고] 카테고리 설명 생성 실패 ({category_name}): {e}")
            # 폴백: 이벤트 요약을 그대로 사용
            return [e.summary for e in events]

    def _print_category_analyses(self, category_analyses: List[CategoryAnalysis]):
        """카테고리별 분석 결과를 출력합니다."""
        print("=" * 50)
        print("📋 카테고리별 분석 결과")
        print("=" * 50)

        for ca in category_analyses:
            emoji = "✅" if ca.event_type == "positive" else "⚠️"
            print(f"\n{emoji} ## {ca.category}")
            print("내용:")
            for desc in ca.descriptions:
                print(f'  "{desc}"')
            tags_str = " ".join(ca.tags)
            print(f"태그: {tags_str}")

        print()

    # ========================================================
    # Chart Image Generation
    # ========================================================

    def _generate_chart_image(
        self,
        region: str,
        period: str,
        chart_data: List[dict],
    ) -> Optional[str]:
        """Plotly로 연도별 호재/악재 막대 그래프 이미지를 생성합니다."""

        if not chart_data:
            return None

        try:
            import plotly.graph_objects as go
            import plotly.io as pio

            # 데이터 준비
            years = [d["year"] for d in chart_data]
            positives = [d["positive"] for d in chart_data]
            negatives = [d["negative"] for d in chart_data]

            # 그래프 생성
            fig = go.Figure()

            # 호재 막대 (초록 계열)
            fig.add_trace(go.Bar(
                name="호재",
                x=years,
                y=positives,
                marker_color="#00CC96",  # 세련된 민트 그린
                text=positives,
                textposition="auto",
                hovertemplate="%{x}년 호재: %{y}건<extra></extra>"
            ))

            # 악재 막대 (붉은 계열)
            fig.add_trace(go.Bar(
                name="악재/리스크",
                x=years,
                y=negatives,
                marker_color="#EF553B",  # 세련된 코랄 레드
                text=negatives,
                textposition="auto",
                hovertemplate="%{x}년 악재: %{y}건<extra></extra>"
            ))

            # 레이아웃 설정
            fig.update_layout(
                title={
                    "text": f"<b>{region} 개발 이벤트 추이 ({period})</b>",
                    "y": 0.95,
                    "x": 0.5,
                    "xanchor": "center",
                    "yanchor": "top",
                    "font": {"size": 20, "family": "Malgun Gothic, AppleGothic, NanumGothic, sans-serif"}
                },
                xaxis_title="연도",
                yaxis_title="이벤트 수",
                barmode="group",
                template="plotly_white",  # 깔끔한 흰색 배경 템플릿
                font=dict(
                    family="Malgun Gothic, AppleGothic, NanumGothic, sans-serif",
                    size=12,
                    color="#333333"
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                margin=dict(l=40, r=40, t=80, b=40),
                bargap=0.15,
                bargroupgap=0.1
            )

            # X축 설정 (모든 연도 표시)
            fig.update_xaxes(
                tickmode="array",
                tickvals=years,
                showgrid=False
            )

            # Y축 설정 (정수만 표시, 그리드 추가)
            max_val = max(max(positives, default=0), max(negatives, default=0))
            fig.update_yaxes(
                range=[0, max_val * 1.2],  # 위쪽 여백 확보
                dtick=1,
                showgrid=True,
                gridcolor="#E5E5E5"
            )

            # 이미지 저장 경로 설정
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )))),
                "output", "charts",
            )
            os.makedirs(output_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_region = region.replace(" ", "_").replace("/", "_")
            filename = f"development_events_{safe_region}_{timestamp}.png"
            filepath = os.path.join(output_dir, filename)

            # 이미지로 저장 (kaleido 필요)
            # scale=2로 설정하여 고해상도 저장
            fig.write_image(filepath, scale=2, width=1000, height=600)

            print(f"  [OK] 그래프 이미지 저장 (Plotly): {filepath}")
            return filepath

        except ImportError as e:
            print(f"  [경고] Plotly 또는 kaleido가 설치되지 않아 그래프를 생성할 수 없습니다: {e}")
            return None
        except Exception as e:
            print(f"  [오류] 그래프 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
