# 📁 디렉토리 구조 및 파일 설명

## 전체 디렉토리 트리

```
app/core/agent/
├── __init__.py                          # 패키지 진입점 (RegionalPolicyAgent, SupervisorAgent export)
├── agent.py                             # 메인 에이전트 인터페이스 (RegionalPolicyAgent)
├── main.py                              # CLI 인터랙티브 실행 스크립트
├── models.py                            # 데이터 모델 및 상태 정의 (Pydantic + TypedDict)
├── supervisor.py                        # Supervisor-Worker 그래프 및 라우팅 로직
│
├── sub_agents/                          # Worker 에이전트 (서브 에이전트)
│   ├── __init__.py
│   ├── data_collector.py                # 뉴스 검색 및 수집 서비스
│   ├── data_classifier.py               # 기사 분류 및 정책 이슈 추출
│   ├── content_generator.py             # 블로그 콘텐츠 생성 (LLM + DALL-E)
│   │
│   └── seo/                             # SEO 최적화 서브 에이전트
│       ├── __init__.py                  # SEO 패키지 export
│       ├── agent.py                     # SEO Agent 인터페이스 (SEOAgent)
│       ├── models.py                    # SEO 관련 데이터 모델
│       ├── scoring.py                   # 결정적 SEO 점수 계산 엔진
│       ├── tools.py                     # SEO 분석 및 개선 LLM 도구
│       └── workflow.py                  # SEO LangGraph 워크플로우
│
└── tools/                               # 유틸리티 도구
    ├── __init__.py
    ├── geocoding.py                     # 주소 → 행정구역 변환 서비스
    └── tistory_publisher.py             # 티스토리 블로그 자동 발행 (Selenium)
```

---

## 코어 파일 상세 설명

### `__init__.py`
- `RegionalPolicyAgent`와 `SupervisorAgent`를 외부에 export
- `from app.core.agent import RegionalPolicyAgent`로 사용

### `agent.py` — `RegionalPolicyAgent` 클래스
- **역할**: 외부에서 호출하는 **메인 인터페이스**
- 내부적으로 `SupervisorAgent`를 생성하여 실행을 위임
- 주요 메서드:
  - `run(user_query)` → 에이전트 실행, 결과 딕셔너리 반환
  - `get_blog_content(content)` → `RegionalAnalysisContent`를 블로그 포스팅용 딕셔너리로 변환

### `main.py` — CLI 인터랙티브 스크립트
- **역할**: 터미널에서 직접 에이전트를 실행하는 **대화형 스크립트**
- `interactive=True`로 에이전트를 초기화하여 사용자 입력을 받음
- 무한 루프로 여러 쿼리를 연속 처리 가능
- 결과를 마크다운 파일로 저장하는 기능 포함

### `models.py` — 데이터 모델
- **역할**: 시스템 전체에서 사용하는 **데이터 모델 정의**
- Pydantic 모델:
  - `AddressInput` — 사용자 입력 주소
  - `AdminRegion` — 파싱된 행정구역 (시/도, 시/군/구, 읍/면/동)
  - `NewsArticle` — 수집된 뉴스 기사
  - `PolicyIssue` — 분석된 정책 이슈 (카테고리, 감성, 중요도)
  - `RegionalAnalysisContent` — 최종 생성 블로그 콘텐츠
- TypedDict:
  - `SupervisorState` — Supervisor-Worker 아키텍처의 공유 상태
- 상수:
  - `COLLECT_DATA`, `ANALYZE_DATA`, `GENERATE_CONTENT`, `OPTIMIZE_SEO`, `PUBLISH_CONTENT`, `FINISH`

### `supervisor.py` — `SupervisorAgent` 클래스
- **역할**: 전체 워크플로우를 관장하는 **핵심 두뇌(Brain)**
- LangGraph `StateGraph`를 구축하여 조건부 분기 그래프를 생성
- 주요 구성:
  - `_build_graph()` — 노드 등록 및 엣지 설정
  - `_supervisor_node()` — 상태를 분석하여 다음 Worker를 결정 (규칙 기반)
  - `_collect_data_node()` — 뉴스 데이터 수집 Worker
  - `_analyze_data_node()` — 기사 분석 Worker
  - `_generate_content_node()` — 콘텐츠 생성 Worker (인터랙티브 모드 지원)
  - `_optimize_seo_node()` — SEO 최적화 Worker
  - `_publish_content_node()` — 티스토리 발행 Worker
  - `run(user_query)` — 에이전트 실행 엔트리포인트
- SEO 목표 점수: `SEO_TARGET_SCORE` (기본 50, 실제 운영 시 85)
- 최대 SEO 재시도: `MAX_SEO_RETRIES` (기본 3)

---

## Sub-Agents 디렉토리

### `sub_agents/news_collector.py`
- `NewsSearchService` — 네이버 뉴스 검색 API 기반 기사 수집
- `WebCrawler` — 기사 URL에서 본문을 추출하는 크롤러

### `sub_agents/data_classifier.py`
- `ArticleAnalyzer` — LLM 기반 기사 분류 및 이슈 추출

### `sub_agents/content_generator.py`
- `ContentGenerator` — 블로그 콘텐츠 생성 (LLM + DALL-E 이미지)

### `sub_agents/seo/`
- `SEOAgent` — SEO 분석 및 개선 인터페이스
- `SEOScorer` — 결정적 알고리즘 기반 점수 엔진
- `SEOTools` — LLM 기반 이슈 분석 및 콘텐츠 개선 도구
- `SEOWorkflow` — LangGraph 기반 SEO 워크플로우

→ 각 상세 설명은 [sub_agents.md](sub_agents.md) 참조

---

## Tools 디렉토리

### `tools/geocoding.py`
- `GeocodingService` — 주소를 행정구역으로 변환 (정규식 기반)

### `tools/tistory_publisher.py`
- `TistoryWriter` — Selenium 기반 티스토리 자동 발행

→ 각 상세 설명은 [tools.md](tools.md) 참조
