# DongneFit Backend

부동산 콘텐츠 생성 및 지도 서비스 백엔드

## 기술 스택

| 카테고리 | 패키지 |
|---------|--------|
| Package Manager | uv |
| Web Framework | FastAPI, Uvicorn |
| Database | PostgreSQL, SQLAlchemy 2.0, Alembic, asyncpg |
| AI/LLM | LangGraph, LangChain, OpenAI, Anthropic |
| Web Scraping | Selenium, webdriver-manager |
| Image Generation | Pillow, DALL-E API |

## 프로젝트 구조

dongnefit-backend/
├── app/
│   ├── api/                 # Presentation Layer (요청/응답 처리)
│   │   ├── deps.py/         # 공통 의존성 (DB 세션 등)
│   │   └── v1/endpoints/
│   ├── core/                # Core (핵심 모듈)
│   │   └── langgraph/       # LangGraph 워크플로우
│   ├── models/              # Data Layer (DB 테이블 정의), SQLAlchemy 모델 (Property, GeneratedContent)
│   ├── schemas/             # DTO (Data Transfer Object), Pydantic 스키마
│   ├── services/            # Business Layer (비즈니스 로직)
│   │
│   ├── config.py            # 환경설정 (환경변수 로드)
│   ├── database.py          # DB 연결 설정
│   └── main.py              # 진입점 (앱 생성, 미들웨어, 라우터 연결)
│
├── alembic/                 # DB 마이그레이션
├── tests/                   # 테스트
├── pyproject.toml
└── .env.example

## 요청 흐름

```
HTTP 요청
    ↓
[api/endpoints] ─── 요청 검증, 라우팅
    ↓
[schemas] ─── 데이터 유효성 검사 (Pydantic)
    ↓
[services] ─── 비즈니스 로직 실행
    ↓
[models] ─── DB 조회/저장
    ↓
HTTP 응답
```

## 각 레이어의 역할
┌──────────────┬───────────┬──────────────────────────┬───────────────────┐
│    layer     │ directory │           role           │     dependency    │
├──────────────┼───────────┼──────────────────────────┼───────────────────┤
│ Presentation │ api/      │ HTTP req/res.            │ schemas, services │
├──────────────┼───────────┼──────────────────────────┼───────────────────┤
│ Schema       │ schemas/  │ data def, validation     │ none              │
├──────────────┼───────────┼──────────────────────────┼───────────────────┤
│ Business     │ services/ │ main logic               │ models, API       │
├──────────────┼───────────┼──────────────────────────┼───────────────────┤
│ Data         │ models/   │ DB table mapping         │ database          │
├──────────────┼───────────┼──────────────────────────┼───────────────────┤
│ Core         │ core/     │ shared modules           │ external libs     │
└──────────────┴───────────┴──────────────────────────┴───────────────────┘

## 핵심 원칙

1. 단방향 의존성: api → services → models (역방향 금지)
2. 관심사 분리: 각 레이어는 한 가지 역할만 담당
3. 버전 관리: api/v1/, api/v2/로 API 버전 분리 가능

## 시작하기

### 1. 의존성 설치

```bash
uv sync
```

### 2. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 API 키를 설정합니다:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/dongnefit

# OpenAI (콘텐츠 생성, 이미지 생성)
OPENAI_API_KEY=your-openai-api-key

# Anthropic (선택사항)
ANTHROPIC_API_KEY=your-anthropic-api-key

# Map API (Naver)
MAP_PROVIDER=naver
MAP_API_KEY=your-map-api-key
```

### 3. 데이터베이스 설정

```bash
# PostgreSQL 데이터베이스 생성
createdb dongnefit

# 마이그레이션 생성 및 실행
uv run alembic revision --autogenerate -m "Initial migration"
uv run alembic upgrade head
```

### 4. 서버 실행

```bash
uv run uvicorn app.main:app --reload
```

서버가 시작되면 http://localhost:8000 에서 접속할 수 있습니다.

## API 엔드포인트

### 헬스체크

```
GET /health
```

### 지도 서비스

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/map/search` | 위치 검색 |
| GET | `/api/v1/map/geocode?address=` | 주소 → 좌표 변환 |
| GET | `/api/v1/map/reverse-geocode?lat=&lng=` | 좌표 → 주소 변환 |

### 콘텐츠 생성

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/content/generate` | 마크다운 콘텐츠 생성 |
| POST | `/api/v1/content/generate-with-image` | 콘텐츠 + 이미지 생성 |

#### 콘텐츠 생성 요청 예시

```json
{
  "content_type": "neighborhood_guide",
  "location": "서울시 강남구 역삼동",
  "keywords": ["직장인", "교통", "맛집"],
  "include_image": true
}
```

#### 콘텐츠 타입

- `property_listing` - 매물 소개
- `neighborhood_guide` - 동네 가이드
- `market_analysis` - 시장 분석
- `investment_insight` - 투자 인사이트

## API 문서

서버 실행 후 아래 URL에서 API 문서를 확인할 수 있습니다:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 개발

### 린트 실행

```bash
uv run ruff check app/
uv run ruff check app/ --fix  # 자동 수정
```

### 타입 체크

```bash
uv run mypy app/
```

### 테스트 실행

```bash
uv run pytest
```

## 시작 방법

1. 환경변수 설정
cp .env.example .env
.env 파일에 API 키 입력

2. PostgreSQL DB 생성
createdb dongnefit

3. 마이그레이션 실행
uv run alembic revision --autogenerate -m "Initial"
uv run alembic upgrade head

4. 서버 실행
uv run uvicorn app.main:app --reload