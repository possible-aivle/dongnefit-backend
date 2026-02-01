# DongneFit Backend

커뮤니티 기반 부동산 정보 플랫폼 백엔드

## 기술 스택

| 카테고리 | 패키지 |
|---------|--------|
| Package Manager | uv |
| Web Framework | FastAPI, Uvicorn |
| Database | PostgreSQL, SQLAlchemy 2.0, Alembic, asyncpg |
| Authentication | OAuth2 (Google, Kakao), Session-based |
| Payment | Toss Payments |
| AI/LLM | LangGraph, LangChain |
| Web Scraping | Selenium |

## 프로젝트 구조

```
app/
├── main.py              # FastAPI 앱 진입점
├── config.py            # 환경설정
├── database.py          # DB 연결
│
├── api/v1/endpoints/    # API 엔드포인트
│   ├── users.py         # 사용자 관리
│   ├── neighborhoods.py # 동네 정보
│   ├── reports.py       # 부동산 리포트
│   ├── discussions.py   # 커뮤니티 게시판
│   ├── payments.py      # 결제 (Toss)
│   └── notifications.py # 알림
│
├── auth/                # 인증
│   ├── deps.py          # 의존성 (get_current_user 등)
│   └── oauth.py         # OAuth (Google, Kakao)
│
├── models/              # SQLAlchemy 모델
│   ├── user.py
│   ├── neighborhood.py
│   ├── report.py
│   ├── discussion.py
│   ├── payment.py
│   └── ...
│
├── schemas/             # Pydantic 스키마
│   ├── user.py
│   ├── neighborhood.py
│   └── ...
│
├── crud/                # 데이터베이스 CRUD
│   ├── user.py
│   ├── neighborhood.py
│   └── ...
│
└── services/            # 비즈니스 로직
    ├── map/             # 지도 서비스
    └── content/         # 콘텐츠 생성 (LangGraph)
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

`.env` 파일 수정:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/dongnefit

# Session
SECRET_KEY=your-secret-key

# OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
KAKAO_CLIENT_ID=...
KAKAO_CLIENT_SECRET=...

# Toss Payments
TOSS_CLIENT_KEY=...
TOSS_SECRET_KEY=...
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

## API 문서

서버 실행 후:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API 엔드포인트

### 인증
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/auth/google` | Google OAuth 로그인 |
| GET | `/api/auth/kakao` | Kakao OAuth 로그인 |
| POST | `/api/auth/logout` | 로그아웃 |
| GET | `/api/auth/me` | 현재 사용자 정보 |

### 사용자 (Admin)
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/users` | 사용자 목록 |
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

### 결제
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/payments/products` | 상품 목록 |
| POST | `/api/v1/payments/orders` | 주문 생성 |
| POST | `/api/v1/payments/request` | 결제 요청 |
| POST | `/api/v1/payments/confirm` | 결제 확인 |

### 알림
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/notifications` | 알림 목록 |
| GET | `/api/v1/notifications/unread-count` | 읽지 않은 알림 수 |
| POST | `/api/v1/notifications/read-all` | 모두 읽음 처리 |

## 개발

```bash
# 린트
uv run ruff check app/

# 린트 + 자동 수정
uv run ruff check app/ --fix

# 테스트
uv run pytest
```
