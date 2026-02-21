# DongneFit Backend

부동산 콘텐츠 자동 생성 SaaS 플랫폼 백엔드

## 기술 스택

| 카테고리        | 패키지                                  |
| --------------- | --------------------------------------- |
| Package Manager | uv                                      |
| Web Framework   | FastAPI, Uvicorn                        |
| ORM             | SQLAlchemy 2.0 (async), SQLModel        |
| Database        | PostgreSQL 17, asyncpg, PostGIS, Alembic |
| Validation      | Pydantic v2 (+ email)                   |
| Authentication  | OAuth2 (Google, Kakao), Session-based   |
| AI/LLM          | LangGraph 멀티에이전트, LangChain, OpenAI, Anthropic, Ollama |
| Data Pipeline   | httpx, fiona (SHP), openpyxl (Excel)    |
| Code Quality    | Ruff (lint + format), mypy (strict)     |
| Testing         | pytest, pytest-asyncio, pytest-cov      |

## 프로젝트 구조

```
backend/
├── app/                         # 메인 애플리케이션
│   ├── main.py                  # FastAPI 앱 진입점 (미들웨어, 라우터 설정)
│   ├── config.py                # Pydantic Settings 환경설정
│   ├── database.py              # Async SQLAlchemy 엔진/세션
│   │
│   ├── api/                     # API 레이어
│   │   ├── deps.py              # 공통 의존성 (DBSession)
│   │   └── v1/endpoints/        # API v1 엔드포인트
│   │       ├── users.py         # 사용자 관리
│   │       ├── neighborhoods.py # 동네 정보
│   │       ├── lots.py          # 필지/토지 조회
│   │       ├── buildings.py     # 건축물 조회
│   │       ├── transactions.py  # 실거래가 조회
│   │       ├── properties.py    # 부동산 종합 조회
│   │       ├── reports.py       # 부동산 리포트
│   │       ├── discussions.py   # 커뮤니티 게시판
│   │       ├── notifications.py # 알림
│   │       ├── talk.py          # Tool-calling agent API
│   │       └── map.py           # 지도 서비스
│   │
│   ├── auth/                    # 인증
│   │   ├── deps.py              # get_current_user 등
│   │   └── oauth.py             # Google & Kakao OAuth
│   │
│   ├── models/                  # SQLAlchemy/SQLModel 모델
│   │   ├── base.py              # TimestampMixin, PublicDataBase
│   │   ├── enums.py             # PropertyType, TransactionType, PublicDataType 등
│   │   ├── user.py              # 사용자 (OAuth ID PK, 역할, 제공자)
│   │   ├── report.py            # 리포트, 카테고리, 리뷰
│   │   ├── discussion.py        # 게시글, 댓글, 좋아요
│   │   ├── notification.py      # 알림, 알림설정
│   │   ├── neighborhood.py      # 동네 정보
│   │   ├── lot.py               # 필지 통합 (지적도 + 6개 토지 데이터 JSONB)
│   │   ├── building.py          # 건축물대장 (표제부, 총괄, 층별, 면적)
│   │   ├── administrative.py    # 행정경계 (시도, 시군구, 읍면동)
│   │   ├── transaction.py       # 실거래가 (매매, 전월세)
│   │   ├── spatial.py           # 도로중심선, 용도지역지구
│   │   └── file.py              # 파일 저장소
│   │
│   ├── schemas/                 # Pydantic 요청/응답 스키마
│   │   ├── base.py              # 공통 응답, 페이지네이션
│   │   ├── user.py, admin.py    # 사용자/관리자 스키마
│   │   ├── lot.py               # 필지 조회 스키마
│   │   ├── building.py          # 건축물 조회 스키마
│   │   ├── transaction.py       # 실거래가 스키마
│   │   ├── administrative.py    # 행정경계 스키마
│   │   ├── spatial.py           # 공간 데이터 스키마
│   │   ├── public_data.py       # 공공데이터 통합 스키마
│   │   └── ...                  # report, discussion, notification, content, map 등
│   │
│   ├── crud/                    # 데이터베이스 CRUD
│   │   ├── base.py              # CRUDBase[ModelType] (Generic CRUD)
│   │   └── ...                  # user, report, discussion, notification, neighborhood
│   │
│   ├── services/                # 비즈니스 로직
│   │   ├── content/             # 콘텐츠 생성
│   │   │   ├── generator.py     # ContentGenerator
│   │   │   └── scraper.py       # RealEstateScraper (Selenium)
│   │   └── map/                 # 지도 서비스 (Naver/Google)
│   │
│   ├── core/                    # AI 에이전트 시스템
│   │   ├── agent/               # AI Agent
│   │   │   ├── talk_agent.py   # Tool-calling talk agent (RTMS/LAWD/VWorld)
│   │   │   ├── agent.py         # Regional Policy Agent
│   │   │   ├── supervisor.py    # Supervisor-Worker 아키텍처
│   │   │   └── tools/           # Agent tools
│   │   │       ├── lawd.py      # 법정동코드 조회
│   │   │       ├── rtms.py      # 실거래가 조회
│   │   │       └── geocoding.py # 주소 파싱
│   │   ├── public_data/         # 공공데이터 연동
│   │   │   ├── rtms.py          # RTMS (국토교통부 실거래가) 클라이언트
│   │   │   ├── lawd.py          # 법정동코드 로컬 데이터
│   │   │   ├── vworld.py        # VWorld 주소→좌표 변환
│   │   │   └── xml.py           # XML 파싱 유틸리티
│   │   ├── agent/               # LangGraph 멀티에이전트
│   │   │   ├── agent.py         # 메인 에이전트 오케스트레이터
│   │   │   ├── supervisor.py    # 멀티에이전트 수퍼바이저
│   │   │   ├── sub_agents/      # 서브 에이전트
│   │   │   │   ├── intent_analyzer.py    # 의도 분석
│   │   │   │   ├── data_collector.py     # 데이터 수집
│   │   │   │   ├── data_classifier.py    # 데이터 분류
│   │   │   │   ├── content_generator.py  # 콘텐츠 생성
│   │   │   │   └── seo/                  # SEO 최적화 에이전트
│   │   │   ├── tools/           # 에이전트 도구
│   │   │   └── resources/       # 프롬프트 템플릿
│   │   └── langgraph/           # LangGraph 워크플로우
│   │
│   ├── utils/                   # 유틸리티
│   │   └── pnu.py               # PNU 코드 파싱 (sido_code, sgg_code 등)
│   │
│   ├── scripts/                 # 유틸리티 스크립트
│   │   ├── seed_data.py         # 더미 데이터 시딩 (Faker)
│   │   └── clear_data.py        # 데이터 초기화 (admin 보존)
│   │
│   └── pipeline/                # 공공데이터 수집 CLI 파이프라인
│       ├── __main__.py          # CLI 진입점
│       ├── cli.py               # 인터랙티브 메뉴
│       ├── registry.py          # 프로세서 자동 등록 레지스트리
│       ├── loader.py            # bulk_upsert / bulk_insert (JSONB aggregation)
│       ├── db_manager.py        # DB 관리 (테이블 통계, truncate)
│       ├── regions.py           # 시도/시군구 지역 데이터
│       ├── parsing.py           # safe_int(), safe_float() 공통 파싱
│       ├── file_utils.py        # ZIP 추출, SHP 읽기, CRS 변환, NFC 정규화
│       ├── processors/          # 데이터 변환 프로세서 (14개 파일, 19종 데이터)
│       │   ├── base.py          # BaseProcessor (batch_size, jsonb_column, simplify_tolerance)
│       │   ├── cadastral.py     # 연속지적도 (SHP)
│       │   ├── land_characteristic.py  # 토지특성 (CSV)
│       │   ├── land_use_plan.py        # 토지이용계획 (CSV → JSONB)
│       │   ├── land_forest.py          # 토지임야 (CSV)
│       │   ├── land_ownership.py       # 토지소유 (CSV → JSONB)
│       │   ├── official_land_price.py  # 개별공시지가 (CSV → JSONB)
│       │   ├── vworld_csv.py           # VWorld CSV 공통 프로세서
│       │   ├── building_register.py    # 건축물대장 5종 (TXT, pipe-delimited)
│       │   ├── gis_building_integrated.py  # GIS건물통합 (SHP)
│       │   ├── administrative_boundary.py  # 행정경계 3종 (SHP)
│       │   ├── road_center_line.py     # 도로중심선 (SHP)
│       │   ├── use_region_district.py  # 용도지역지구 (SHP)
│       │   └── real_estate_transaction.py  # 실거래가 매매/전월세 (Excel)
│       ├── transaction_crawler/ # 실거래가 엑셀 크롤러
│       │   ├── __main__.py      # CLI 진입점
│       │   └── crawler.py       # 크롤러 로직 (httpx 기반)
│       └── public_data/         # 원본 데이터 파일 (ZIP/CSV/TXT/XLSX)
│
├── alembic/                     # DB 마이그레이션
│   ├── env.py
│   └── versions/
│
├── docs/                        # 문서
│   ├── agent/                   # 에이전트 시스템 문서
│   │   ├── README.md            # 에이전트 개요
│   │   ├── structure.md         # 아키텍처 구조
│   │   ├── workflow.md          # 워크플로우
│   │   └── sub_agents.md        # 서브 에이전트 명세
│   ├── data/                    # 공공데이터 문서
│   │   ├── public-data-erd.md   # ERD
│   │   ├── geometry-handling.md # 공간 데이터 처리
│   │   └── ...                  # DB 적재 시나리오, SHP 전처리 등
│   └── uv.md                    # uv 사용법
│
├── tests/                       # 테스트
├── pyproject.toml               # 프로젝트 설정 (uv)
├── alembic.ini                  # Alembic 설정
├── docker-compose.yaml          # 로컬 PostgreSQL
└── .env.example                 # 환경변수 템플릿
```

## 시작하기

### 1. 의존성 설치

```bash
uv sync
```

### 2. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일의 주요 항목:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/realestate

# Session
SECRET_KEY=your-secret-key-change-in-production

# OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
KAKAO_CLIENT_ID=...
KAKAO_CLIENT_SECRET=...

# AI (콘텐츠 생성)
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...

# Local LLM (Ollama) - Talk API에서 local_llm provider 사용 시
OLLAMA_BASE_URL=http://localhost:11434  # Ollama 서버 URL (기본값)
OLLAMA_MODEL=llama3.2                   # 사용할 Ollama 모델명
LLM_PROVIDER=gpt                         # LLM 제공자: "gpt" 또는 "local_llm"

# 공공데이터 (Talk API 사용 시 필수)
DATA_GO_KR_API_DECODE_KEY=...  # 공공데이터포털 API 키 (RTMS 실거래가)
VWORLD_API_KEY=...              # VWorld API 키 (주소→좌표 변환)
```

### 3. 데이터베이스 설정

```bash
# PostgreSQL 컨테이너 실행
docker compose up -d db

# 마이그레이션 실행
uv run alembic upgrade head
```

### 4. 데이터베이스 시딩/초기화

```bash
# 더미 데이터 삽입
uv run python -m app.scripts.seed_data

# 데이터 초기화 (admin 보존)
uv run python -m app.scripts.clear_data
```

### 5. 서버 실행

```bash
uv run uvicorn app.main:app --reload --port 8000
```

### 6. 공공데이터 파이프라인 실행

```bash
# CLI 실행 (인터랙티브 메뉴)
uv run python -m app.pipeline

# "공공데이터 적재 (파일 → DB)" 선택
# → 데이터 소스 복수 선택 (토지/건물/공간/거래 19종)
# → 지역 선택 (시도/시군구 단위 필터링)
# → UPSERT/TRUNCATE 옵션 → 적재 실행
```

`app/pipeline/public_data/` 디렉토리에 ZIP/CSV/TXT/XLSX 원본 파일이 필요합니다.

### 7. 실거래가 크롤러

국토교통부 실거래가공개시스템(https://rt.molit.go.kr)에서 엑셀 데이터를 월별로 다운로드합니다.

- 대상: 아파트(A), 연립/다세대(B), 단독/다가구(C), 오피스텔(D), 토지(G)
- 매매 + 전월세 (전월세는 신규 계약만)
- 전국 단위 다운로드 시 1개월(31일) 제한 → 자동 월별 분할
- 일일 다운로드 100건 제한 감지 시 자동 중단
- 이미 받은 파일은 자동 스킵 (재실행 안전)

```bash
# 전체 다운로드 (기본: 최근 1년)
uv run python -m app.pipeline.transaction_crawler

# 기간 지정
uv run python -m app.pipeline.transaction_crawler --start 2025-01-01 --end 2025-12-31

# 특정 부동산 유형만 (A=아파트, B=연립다세대, C=단독다가구, D=오피스텔, G=토지)
uv run python -m app.pipeline.transaction_crawler --types A B

# 매매만 (전월세 제외)
uv run python -m app.pipeline.transaction_crawler --no-rent

# 테스트 (아파트 매매 당월만)
uv run python -m app.pipeline.transaction_crawler --test
```

다운로드 파일 위치: `app/pipeline/public_data/실거래가_매매/`, `실거래가_전월세/`

### 8. Local LLM (Ollama) 설정

Talk API에서 로컬 LLM을 사용하려면 Ollama를 설치하고 모델을 다운로드해야 합니다.

#### Ollama 설치

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# https://ollama.com/download 에서 다운로드
```

#### Ollama 서버 실행

```bash
# Ollama 서버 시작 (백그라운드)
ollama serve

# 또는 포그라운드에서 실행
ollama serve
```

기본적으로 `http://localhost:11434`에서 서버가 실행됩니다.

#### 모델 다운로드 (Pull)

```bash
# 기본 모델 (llama3.2)
ollama pull llama3.2

# 다른 모델 예시
ollama pull llama3.1
ollama pull mistral
ollama pull qwen2.5
```

#### 환경변수 설정

`.env` 파일에 다음 설정을 추가하세요:

```env
# Ollama 설정
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
LLM_PROVIDER=local_llm  # "gpt" 또는 "local_llm"
```
또는 요청에서 `provider`를 지정하지 않으면 환경변수 `LLM_PROVIDER`의 값이 사용됩니다.

## DB 스키마

### 공공데이터 테이블 (13개)

| 테이블 | PK/Unique | 설명 |
|--------|-----------|------|
| `lots` | pnu + data_type | 필지 통합 (지적도 + JSONB: use_plans, ownerships, official_prices, ancillary_lots) |
| `building_register_mains` | mgm_bldrgst_pk | 건축물대장 표제부 |
| `building_register_generals` | mgm_bldrgst_pk | 건축물대장 총괄표제부 |
| `building_register_floor_details` | mgm_bldrgst_pk + floor_no + floor_type | 건축물대장 층별개요 |
| `building_register_areas` | mgm_bldrgst_pk + area_type + area_name | 건축물대장 전유공용면적 |
| `gis_building_integrated` | pnu + building_id | GIS건물통합정보 |
| `administrative_sidos` | sido_code | 시도 행정경계 |
| `administrative_sggs` | sgg_code | 시군구 행정경계 |
| `administrative_emds` | emd_code | 읍면동 행정경계 |
| `road_center_lines` | source_id | 도로중심선 |
| `use_region_districts` | source_id | 용도지역지구 |
| `real_estate_sales` | composite | 실거래가 매매 |
| `real_estate_rentals` | composite | 실거래가 전월세 |

### 파이프라인 아키텍처

```
수집 (collect)     →  변환 (transform)    →  적재 (load)
ZIP/CSV/TXT/XLSX      컬럼 매핑              bulk_upsert
SHP → fiona           타입 변환              batch_size별 처리
Excel → openpyxl      PNU 생성              JSONB 집계 (jsonb_column)
                      geometry → WKT         ST_Simplify (simplify_tolerance)
```

- **BaseProcessor**: `batch_size`, `jsonb_column`, `simplify_tolerance` 클래스 속성으로 프로세서별 동작 제어
- **자동 등록**: `registry.py`가 processors/ 하위 모듈을 자동 탐색하여 등록 (19종)
- **JSONB 집계**: 1:N 관계 데이터(이용계획, 소유, 공시지가 등)를 PNU 기준으로 그룹화하여 JSONB 배열로 저장

## API 문서

서버 실행 후:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API 엔드포인트

### 인증

| Method | Endpoint                    | 설명                |
| ------ | --------------------------- | ------------------- |
| GET    | `/api/auth/google`          | Google OAuth 로그인 |
| GET    | `/api/auth/google/callback` | Google OAuth 콜백   |
| GET    | `/api/auth/kakao`           | Kakao OAuth 로그인  |
| GET    | `/api/auth/kakao/callback`  | Kakao OAuth 콜백    |
| POST   | `/api/auth/logout`          | 로그아웃            |
| GET    | `/api/auth/me`              | 현재 사용자 정보    |

### 사용자 (Admin)

| Method | Endpoint             | 설명                                   |
| ------ | -------------------- | -------------------------------------- |
| GET    | `/api/v1/users`      | 사용자 목록 (필터링/정렬/페이지네이션) |
| GET    | `/api/v1/users/me`   | 내 정보                                |
| POST   | `/api/v1/users`      | 사용자 생성                            |
| PATCH  | `/api/v1/users/{id}` | 사용자 수정                            |

### 부동산 데이터

| Method | Endpoint                           | 설명                            |
| ------ | ---------------------------------- | ------------------------------- |
| GET    | `/api/v1/lots/{pnu}`               | 필지 상세 (토지 통합 데이터)    |
| GET    | `/api/v1/buildings/{pnu}`          | 건축물 정보                     |
| GET    | `/api/v1/transactions/{sgg_code}`  | 실거래가 조회                   |
| GET    | `/api/v1/properties/{pnu}/summary` | 부동산 종합 요약 (필지+건물+거래) |

### 동네

| Method | Endpoint                                   | 설명           |
| ------ | ------------------------------------------ | -------------- |
| GET    | `/api/v1/neighborhoods`                    | 동네 목록      |
| GET    | `/api/v1/neighborhoods/{id}`               | 동네 상세      |
| POST   | `/api/v1/neighborhoods/search-by-location` | 위치 기반 검색 |

### 리포트

| Method | Endpoint                       | 설명          |
| ------ | ------------------------------ | ------------- |
| GET    | `/api/v1/reports`              | 리포트 목록   |
| GET    | `/api/v1/reports/published`    | 발행된 리포트 |
| POST   | `/api/v1/reports`              | 리포트 생성   |
| POST   | `/api/v1/reports/{id}/publish` | 리포트 발행   |

### 게시판

| Method | Endpoint                           | 설명        |
| ------ | ---------------------------------- | ----------- |
| GET    | `/api/v1/discussions`              | 게시글 목록 |
| POST   | `/api/v1/discussions`              | 게시글 작성 |
| POST   | `/api/v1/discussions/{id}/like`    | 좋아요 토글 |
| POST   | `/api/v1/discussions/{id}/replies` | 댓글 작성   |

### 알림

| Method | Endpoint                             | 설명              |
| ------ | ------------------------------------ | ----------------- |
| GET    | `/api/v1/notifications`              | 알림 목록         |
| GET    | `/api/v1/notifications/unread-count` | 읽지 않은 알림 수 |
| POST   | `/api/v1/notifications/read-all`     | 모두 읽음 처리    |

### Talk (Tool-calling Agent)
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/talk` | 실거래가/법정동코드/좌표 변환 도구를 사용하는 대화형 API |

**사용 예시:**

OpenAI GPT 사용:
```bash
curl -X POST "http://localhost:8000/api/v1/talk" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "판교 202401 아파트 매매 동별로 요약 해줘"}
    ],
    "context": {"provider": "gpt"},
    "options": {"model": "gpt-4o-mini", "temperature": 0.0}
  }'
```

Local LLM (Ollama) 사용:
```bash
curl -X POST "http://localhost:8000/api/v1/talk" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "판교 202401 아파트 매매 동별로 요약 해줘"}
    ],
    "context": {"provider": "local_llm"},
    "options": {"model": "llama3.2", "temperature": 0.0}
  }'
```

**사용 가능한 도구:**
- `lawd_resolve_code`: 지역명으로 법정동코드 조회
- `lawd_search`: 키워드로 법정동코드 후보 검색
- `rtms_apt_trade_detail`: 아파트 매매 상세 실거래가 조회
- `vworld_get_coord`: 주소를 좌표(위도/경도)로 변환

## 아키텍처 패턴

- **CRUD Factory**: `CRUDBase[ModelType]` 제네릭 클래스로 공통 CRUD 추상화
- **Dependency Injection**: FastAPI `Depends` 활용 (DBSession, get_current_user)
- **Async-first**: AsyncSession, async generators 전면 사용
- **Schema Validation**: Pydantic v2 + SQLModel 통합
- **Service Layer**: 비즈니스 로직 분리 (content, map)
- **Multi-Agent System**: LangGraph 수퍼바이저 → 서브 에이전트 (의도분석, 데이터수집, 콘텐츠생성, SEO)
- **Pipeline Pattern**: collect → transform → load (BaseProcessor 추상 클래스, 자동 등록 레지스트리)
- **Tool-calling Agent**: LangGraph 기반 대화형 API (`/api/v1/talk`)
  - 공공데이터 도구를 LLM이 자동으로 선택하여 호출
  - 실거래가 조회, 법정동코드 검색, 좌표 변환 등 지원

## 개발

```bash
# 린트
uv run ruff check .

# 린트 + 자동 수정
uv run ruff check . --fix

# 포맷
uv run ruff format .

# 타입 체크
uv run mypy app/

# 테스트
uv run pytest

# 테스트 + 커버리지
uv run pytest --cov=app
```

## 마이그레이션

```bash
# 마이그레이션 파일 생성
uv run alembic revision --autogenerate -m "마이그레이션 설명"

# 마이그레이션 실행
uv run alembic upgrade head

# 마이그레이션 롤백
uv run alembic downgrade -1
```
