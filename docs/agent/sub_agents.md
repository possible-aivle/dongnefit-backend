# 🛠️ Worker 에이전트 (Sub-Agents) 상세

## 1. NewsSearchService — 뉴스 수집

> **파일**: `sub_agents/news_collector.py`

### 개요

네이버 뉴스 검색 API를 사용하여 키워드 기반 뉴스 기사를 수집합니다.

### 클래스

#### `NewsSearchService`

| 메서드 | 설명 |
|---|---|
| `search_news(keyword, display, days_ago)` | 단일 키워드로 뉴스 검색 (최대 100건) |
| `search_multiple_keywords(keywords, display_per_keyword)` | 여러 키워드 비동기 병렬 검색 + 중복 제거 |

**설정 요구사항**:
- `NAVER_CLIENT_ID` — 네이버 개발자 Client ID
- `NAVER_CLIENT_SECRET` — 네이버 개발자 Client Secret

**처리 흐름**:
```
키워드 → API 요청 → HTML 태그 제거 → 날짜 필터링 → NewsArticle 리스트 반환
```

**주요 특징**:
- `httpx.AsyncClient`를 사용한 비동기 HTTP 요청
- 날짜순(`date`) 정렬로 최신 기사 우선 수집
- `BeautifulSoup`으로 HTML 태그 제거
- URL 기준 중복 제거

#### `WebCrawler`

| 메서드 | 설명 |
|---|---|
| `fetch_article_content(url)` | 기사 URL에서 본문 추출 |

- 네이버 뉴스(`news.naver.com`) → `#dic_area` div에서 본문 추출
- 기타 사이트 → `<article>` 태그에서 추출 시도

---

## 2. ArticleAnalyzer — 기사 분석

> **파일**: `sub_agents/data_classifier.py`

### 개요

LLM을 사용하여 수집된 뉴스 기사를 분류하고 정책 이슈를 추출합니다.

### 클래스: `ArticleAnalyzer`

| 메서드 | 설명 |
|---|---|
| `classify_article(article)` | 단일 기사를 5개 카테고리 중 하나로 분류 |
| `classify_articles_batch(articles)` | 여러 기사 일괄 분류 (관련 없는 기사 필터링) |
| `extract_policy_issues(articles, region)` | 분류된 기사에서 정책 이슈 추출 |

**분류 카테고리**:

| 카테고리 | 설명 | 예시 |
|---|---|---|
| `traffic` | 교통 인프라 | GTX, 지하철 연장, 역세권 |
| `infrastructure` | 생활 인프라/도시계획 | 재개발, 재건축, 상업시설 |
| `policy` | 정책 및 규제 | 토지거래허가구역, 분양가 규제 |
| `economy` | 경제 환경 | 기업 이전, 산업단지 |
| `environment` | 환경 및 안전 | 오염시설, 자연재해 |
| `irrelevant` | 부동산 무관 | (필터링됨) |

**이슈 추출 흐름**:
```
분류된 기사 → 카테고리별 그룹화 → LLM으로 이슈 추출
→ PolicyIssue 리스트 (제목, 감성, 중요도, 요약, 출처)
→ 중요도 내림차순 정렬
```

**LLM 설정**:
- 모델: `gpt-4o-mini` (OpenAI) 또는 `claude-3-5-sonnet` (Anthropic)
- temperature: `0.3` (일관된 분류를 위해 낮은 온도)

---

## 3. ContentGenerator — 콘텐츠 생성

> **파일**: `sub_agents/content_generator.py`

### 개요

정책 이슈 분석 결과를 바탕으로 **블로그 콘텐츠를 생성**합니다. 본문 작성, 제목 생성, 카테고리 분류, 해시태그 생성, DALL-E 이미지 생성까지 포함합니다.

### 클래스: `ContentGenerator`

#### 주요 메서드

| 메서드 | 설명 |
|---|---|
| `generate_content(region, issues, ...)` | 메인 콘텐츠 생성 (전체 파이프라인) |
| `extract_keywords(texts, top_n)` | KR-WordRank 기반 키워드 추출 |

#### 내부 메서드

| 메서드 | 설명 |
|---|---|
| `_analyze_user_intent(query)` | 호재/악재 분류 필요 여부 판단 |
| `_generate_blog_content(...)` | LLM으로 블로그 본문 생성 (Markdown) |
| `_generate_title(...)` | SEO 최적화 제목 생성 |
| `_classify_category(content)` | 동네핏 카테고리 자동 분류 |
| `_generate_hashtags(content)` | 해시태그 자동 생성 (최대 10개) |
| `_generate_meta_description(...)` | 메타 설명 생성 (150-160자) |
| `_generate_image(prompt)` | DALL-E 3 이미지 생성 |
| `_download_image(url)` | 생성된 이미지 로컬 저장 |
| `_insert_images(content, keyword, num)` | 본문 섹션에 이미지 삽입 |

**콘텐츠 생성 모드**:

| 모드 | 조건 | 구조 |
|---|---|---|
| 호재/악재 분류 | 쿼리에 "호재", "악재" 등 포함 | 서론 → 호재 분석 → 악재 분석 → 결론 |
| 일반 분석 | 쿼리에 "가격", "시세", "전망" 등 포함 | 서론 → 본론 (이슈별) → 결론 |
| 키워드 기반 | 수집된 이슈가 없을 때 | 서론 → 본론 → 결론 (일반 지식 기반) |

**동네핏 카테고리 체계**:
- 동네 소식 / 동네 문화 / 동네 분석
- 동네 임장 / 주택 임장 / 상가 임장
- 부동산학개론 / 부동산 금융 / 부동산 개발
- 부동산 관리 / 부동산 법률 및 제도 / 부동산 정책 및 이슈
- 기타

**이미지 생성 설정**:
- `ENABLE_IMAGE_GENERATION = False` (현재 비활성화)
- DALL-E 3 사용, 스타일: `"realistic photo, high quality, professional photography, 8k"`
- 소제목(##) 기준으로 섹션 분리 후 균등 배치

---

## 4. SEO 서브 에이전트

> **디렉토리**: `sub_agents/seo/`

### 4.1 SEOAgent (`agent.py`)

SEO 분석 및 개선의 **상위 인터페이스**입니다.

| 메서드 | 설명 |
|---|---|
| `analyze_and_improve(draft)` | 분석 + 개선 전체 파이프라인 |
| `analyze(draft)` | 분석만 수행 (점수 + 이슈) |
| `improve(state, categories)` | 선택적 개선 수행 |

### 4.2 SEOScorer (`scoring.py`)

**결정적(deterministic) 알고리즘** 기반의 SEO 점수 엔진입니다. LLM 없이 동작합니다.

**점수 배분 (100점 만점)**:

| 항목 | 배점 | 평가 기준 |
|---|---|---|
| 제목 (Title) | 20점 | 키워드 포함(10), 길이(5), 숫자(3), 클릭유도(2) |
| 콘텐츠 구조 (Structure) | 25점 | H2/H3 헤딩(10), 단락 구조(8), 서식 활용(7) |
| 키워드 최적화 (Keyword) | 20점 | 밀도(10), 첫 100단어(5), 분포(5) |
| 가독성 (Readability) | 15점 | 문장 길이(7), 단락당 문장 수(5), 전문용어(3) |
| 메타데이터 (Metadata) | 20점 | 카테고리(8), 태그 개수(7), 메타 설명(5) |

**최적 기준값**:

| 항목 | 최적 범위 |
|---|---|
| 제목 길이 | 25~60자 |
| 키워드 밀도 | 1.0~3.0% |
| 태그 개수 | 5~10개 |
| 메타 설명 길이 | 150~160자 |

### 4.3 SEOTools (`tools.py`)

LLM을 사용하여 SEO 이슈를 분석하고 콘텐츠를 개선하는 도구 모음입니다.

| 메서드 | 설명 |
|---|---|
| `analyze_seo_score(draft)` | SEO 점수 계산 (SEOScorer 위임) |
| `analyze_seo_issues(draft, score)` | LLM으로 SEO 이슈 분석 |
| `improve_title(draft, issues)` | 제목 SEO 최적화 |
| `improve_structure(draft, issues)` | 콘텐츠 구조 개선 |
| `improve_content(draft, issues)` | 키워드/가독성 개선 |
| `optimize_metadata(draft, issues)` | 메타데이터 최적화 |
| `generate_comparison_report(...)` | 개선 전후 비교 리포트 생성 |

### 4.4 SEOWorkflow (`workflow.py`)

LangGraph 기반의 SEO 워크플로우입니다. 3가지 그래프를 보유합니다:

#### 전체 워크플로우 (`graph`)
```
validate_input → calculate_score → analyze_issues → improve_content → rescore → generate_report
```

#### 분석 전용 워크플로우 (`analysis_graph`)
```
validate_input → calculate_score → analyze_issues
```

#### 개선 전용 워크플로우 (`improvement_graph`)
```
improve_content → rescore → generate_report
```

**실행 모드**:
- `run(draft)` — 자동 모드: 분석 → 개선 → 리포트 일괄 실행
- `run_interactive(draft)` — 인터랙티브 모드: 사용자가 개선 항목 선택 가능

### 4.5 SEO 데이터 모델 (`models.py`)

| 모델 | 설명 |
|---|---|
| `BlogDraft` | SEO 분석 입력용 블로그 초안 |
| `SEOScoreBreakdown` | SEO 점수 세부 항목 (총점 + 5개 영역) |
| `SEOIssue` | 분석된 SEO 이슈 (카테고리, 심각도, 설명) |
| `ImprovedBlog` | 개선된 블로그 콘텐츠 + 변경 내역 |
| `ComparisonReport` | 개선 전/후 비교 리포트 |
| `SEOAgentState` | LangGraph 상태 관리 TypedDict |

---

## 5. IntentAnalyzer — 의도 분석

> **파일**: `sub_agents/intent_analyzer.py`

### 개요

사용자의 자연어 쿼리를 분석하여 **의도(Intent)**를 파악하고, **지역(Region)** 및 **부동산 유형(Real Estate Type)**을 추출합니다.
또한, 콘텐츠 생성 시 **지역별/건물구조별 맞춤형 분석 가이드**를 제공하여 글의 방향성을 잡는 역할을 수행합니다.

### 주요 기능

| 메서드 | 설명 |
|---|---|
| `analyze_intent(query)` | 사용자 질문에서 의도, 지역, 유형 추출 + **검색 키워드 확장** |
| `analyze_content_intent(region, real_estate_type)` | 콘텐츠 생성을 위한 심층 의도 분석 (타깃, 데이터, 톤앤매너 설정) |
| `_format_custom_prompt(...)` | 지역/유형 정보를 바탕으로 `region_prompts.py`에서 최적화된 프롬프트 조회 |

### 5.1 검색 키워드 확장 (Search Expansion)

단순히 사용자가 입력한 단어만 검색하는 것이 아니라, 의도에 맞는 **다양한 연관 키워드**를 자동으로 생성하여 데이터 수집 범위를 넓힙니다.

- **목적**: 사용자의 숨겨진 의도를 파악하여 더 풍부한 정보를 수집
- **예시**: "강남역 아파트 임장" 입력 시
    - 추출된 키워드: `["강남역 아파트 시세", "강남역 아파트 학군", "강남역 아파트 교통 호재", "강남역 아파트 실거주 후기"]`
    - 효과: '시세'뿐만 아니라 '학군', '교통', '실거주 후기' 등 다각적인 정보 수집 가능

### 5.2 맞춤형 프롬프트 (Region Prompts)

> **리소스 파일**: `app/core/agent/resources/region_prompts.py`

지역별, 건축물 용도별로 특화된 분석 가이드를 제공하는 리소스 데이터베이스입니다. `IntentAnalyzer`가 이를 활용하여 LLM에게 구체적인 지침을 제공합니다.

#### 데이터 구조

1.  **`SEOUL_GU_PROMPTS` (서울 25개 구)**
    - 각 구별 특징 (학군, 교통, 호재 등) 정의
    - 예: **강남구** → 투자/재건축/학군/교통 중심 분석

2.  **`GYEONGGI_CITY_PROMPTS` (경기 주요 도시)**
    - 주요 도시별 특징 정의
    - 예: **고양시(일산)** → 1기 신도시 재건축/GTX/호수공원 중심 분석

3.  **`BUILDING_TYPE_PROMPTS` (건축물 용도)**
    - 아파트, 오피스텔, 빌라, 상가 등 용도별 분석 포인트 정의
    - 예: **오피스텔** → 임대 수익률/역세권/1인 가구 편의성 중심 분석

#### 작동 방식

1.  사용자 입력: "강남역 오피스텔 투자"
2.  `IntentAnalyzer` 분석: `Region="강남구"`, `Type="오피스텔"`
3.  프롬프트 조합: `SEOUL_GU_PROMPTS["강남구"]` + `BUILDING_TYPE_PROMPTS["오피스텔"]`
4.  LLM 지침 생성: "강남구의 투자/재건축 관점과 오피스텔의 수익률/역세권 관점을 결합하여 분석하라"

이를 통해 같은 "부동산 분석"이라도 **지역과 물건의 특성에 맞는 깊이 있는 분석 결과**를 제공합니다.
