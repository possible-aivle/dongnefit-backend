# DongneFit Backend

부동산 콘텐츠 자동 생성 SaaS 플랫폼 백엔드

## 기술 스택

| 카테고리 | 패키지 |
|---------|--------|
| Package Manager | uv |
| Web Framework | FastAPI, Uvicorn |
| ORM | SQLAlchemy 2.0 (async), SQLModel |
| Database | PostgreSQL 17, asyncpg, Alembic |
| Validation | Pydantic v2 (+ email) |
| Authentication | OAuth2 (Google, Kakao), Session-based |
| AI/LLM | LangGraph, LangChain, OpenAI, Anthropic |
| Web Scraping | Selenium, krwordrank |
| Code Quality | Ruff (lint + format), mypy (strict) |
| Testing | pytest, pytest-asyncio, pytest-cov |

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
│   │       ├── reports.py       # 부동산 리포트
│   │       ├── discussions.py   # 커뮤니티 게시판
│   │       ├── notifications.py # 알림
│   │       └── talk.py           # Tool-calling agent API
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
│   │   ├── blog.py              # 블로그 포스트
│   │   ├── lot.py               # 필지 (토지대장)
│   │   ├── land.py              # 토지특성, 용도지역, 임야
│   │   ├── building.py          # 건축물대장 (표제부, 층별)
│   │   ├── administrative.py    # 행정구역 (시군구, 읍면동)
│   │   ├── transaction.py       # 공시지가, 실거래가
│   │   ├── spatial.py           # 도로중심선, 용도지역지구
│   │   └── file.py              # 파일 저장소
│   │
│   ├── schemas/                 # Pydantic 요청/응답 스키마
│   │   ├── base.py              # 공통 응답, 페이지네이션
│   │   ├── user.py              # UserCreate, UserUpdate, UserQuery
│   │   ├── report.py            # ReportCreate, ReportUpdate
│   │   ├── discussion.py        # DiscussionCreate, DiscussionUpdate
│   │   ├── content.py           # ContentRequest, ContentResponse
│   │   └── ...                  # neighborhood, notification, blog 등
│   │
│   ├── crud/                    # 데이터베이스 CRUD
│   │   ├── base.py              # CRUDBase[ModelType] (Generic CRUD)
│   │   ├── user.py              # 이메일 검색, 필터링, 역할 관리
│   │   ├── report.py            # 리포트 CRUD + 발행
│   │   ├── discussion.py        # 게시판 CRUD
│   │   ├── notification.py      # 알림 CRUD
│   │   └── neighborhood.py      # 동네 CRUD
│   │
│   ├── services/                # 비즈니스 로직
│   │   ├── content/             # 콘텐츠 생성
│   │   │   ├── generator.py     # ContentGenerator (LangGraph 워크플로우)
│   │   │   └── scraper.py       # RealEstateScraper (Selenium)
│   │   └── map/                 # 지도 서비스 (Naver/Google)
│   │
│   ├── core/                    # 핵심 기능
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
│   │   ├── langgraph/           # LangGraph 콘텐츠 생성 워크플로우
│   │   │   └── workflow.py      # ContentGenerationWorkflow
│   │   └── tistory/             # 티스토리 블로그 자동화
│   │       ├── config.py        # 티스토리 설정
│   │       ├── content_generator.py
│   │       ├── data_processor.py
│   │       ├── tistory_writer.py
│   │       └── main.py          # 오케스트레이션
│   │
│   └── scripts/                 # 유틸리티 스크립트
│       ├── seed_data.py         # 더미 데이터 시딩 (Faker)
│       └── clear_data.py        # 데이터 초기화 (admin 보존)
│
├── pipeline/                    # 공공데이터 수집 CLI
│   ├── __main__.py              # CLI 진입점
│   ├── cli.py                   # 인터랙티브 메뉴
│   ├── clients/                 # 데이터 소스 클라이언트
│   ├── processors/              # 데이터 변환 프로세서
│   ├── loader.py                # 동적 모듈 로더
│   ├── db_manager.py            # DB 매니저
│   └── registry.py              # 모듈 레지스트리
│
├── alembic/                     # DB 마이그레이션
│   ├── env.py
│   └── versions/
│
├── docs/                        # 문서
│   ├── public_data_erd.md       # 공공데이터 ERD
│   ├── tistory.md               # 티스토리 연동 문서
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
uv run python -m pipeline
```

## API 문서

서버 실행 후:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API 엔드포인트

### 인증
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/auth/google` | Google OAuth 로그인 |
| GET | `/api/auth/google/callback` | Google OAuth 콜백 |
| GET | `/api/auth/kakao` | Kakao OAuth 로그인 |
| GET | `/api/auth/kakao/callback` | Kakao OAuth 콜백 |
| POST | `/api/auth/logout` | 로그아웃 |
| GET | `/api/auth/me` | 현재 사용자 정보 |

### 사용자 (Admin)
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/users` | 사용자 목록 (필터링/정렬/페이지네이션) |
| GET | `/api/v1/users/me` | 내 정보 |
| POST | `/api/v1/users` | 사용자 생성 |
| PATCH | `/api/v1/users/{id}` | 사용자 수정 |

### 동네
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/neighborhoods` | 동네 목록 |
| GET | `/api/v1/neighborhoods/{id}` | 동네 상세 |
| POST | `/api/v1/neighborhoods/search-by-location` | 위치 기반 검색 |

### 리포트
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/reports` | 리포트 목록 |
| GET | `/api/v1/reports/published` | 발행된 리포트 |
| POST | `/api/v1/reports` | 리포트 생성 |
| POST | `/api/v1/reports/{id}/publish` | 리포트 발행 |

### 게시판
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/discussions` | 게시글 목록 |
| POST | `/api/v1/discussions` | 게시글 작성 |
| POST | `/api/v1/discussions/{id}/like` | 좋아요 토글 |
| POST | `/api/v1/discussions/{id}/replies` | 댓글 작성 |

### 알림
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/notifications` | 알림 목록 |
| GET | `/api/v1/notifications/unread-count` | 읽지 않은 알림 수 |
| POST | `/api/v1/notifications/read-all` | 모두 읽음 처리 |

### Talk (Tool-calling Agent)
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/talk` | 실거래가/법정동코드/좌표 변환 도구를 사용하는 대화형 API |

**사용 예시:**
```bash
curl -X POST "http://localhost:8000/api/v1/talk" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "판교 202401 아파트 매매 동별로 요약 해줘"}
    ],
    "context": {},
    "options": {"model": "gpt-4o-mini", "temperature": 0.0}
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
- **LangGraph Workflow**: 콘텐츠 생성 파이프라인 (research → outline → draft → final)
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
