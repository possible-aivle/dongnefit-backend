# 🤖 AI Agent 시스템 문서

부동산 호재/악재 분석 및 블로그 콘텐츠 자동 생성을 위한 AI Agent 시스템 문서입니다.

## 📚 목차

1.  [**시스템 구조 (Structure)**](structure.md)
    -   전체 디렉토리 구조
    -   주요 모듈 및 클래스 설명
2.  [**워크플로우 (Workflow)**](workflow.md)
    -   LangGraph 기반 실행 흐름
    -   Supervisor와 Worker 간의 상호작용
3.  [**서브 에이전트 (Sub-Agents)**](sub_agents.md)
    -   뉴스 수집기 (Collector)
    -   데이터 분류기 (Analyzer)
    -   콘텐츠 생성기 (Generator)
    -   SEO 최적화 에이전트
4.  [**도구 (Tools)**](tools.md)
    -   지오코딩 (Geocoding)
    -   티스토리 발행 (Publisher)
5.  [**실행 가이드 (Execution)**](execution.md)
    -   설치 및 환경 설정
    -   실행 방법 (CLI / API)

---

## 🚀 시스템 개요

이 프로젝트는 **LangGraph**를 활용한 Multi-Agent 시스템으로, 사용자의 자연어 쿼리를 분석하여 다음과 같은 작업을 자율적으로 수행합니다.

1.  **데이터 수집**: 네이버 뉴스 API 등을 통한 부동산 관련 뉴스 수집 및 본문 크롤링
2.  **데이터 분석**: LLM을 활용한 호재/악재 분류 및 핵심 정책 이슈 추출
3.  **콘텐츠 생성**: 분석된 데이터를 바탕으로 블로그용 콘텐츠(글 + 이미지) 생성
4.  **SEO 최적화**: 검색 엔진 노출을 위한 제목, 본문, 태그 최적화 (점수 기반 평가)
5.  **자동 발행**: 완성된 콘텐츠를 티스토리 블로그에 자동 업로드

## 🛠️ 기술 스택

-   **Framework**: FastAPI, LangGraph, LangChain
-   **LLM**: OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet
-   **Database**: PostgreSQL (SQLModel)
-   **Tools**: Selenium (발행), BeautifulSoup (크롤링)
