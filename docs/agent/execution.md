# 🚀 실행 가이드 (Execution)

## 1. 환경 설정

### 1.1 필수 요구사항

-   Python 3.13+
-   Chrome Browser (티스토리 발행용)

### 1.2 의존성 설치

`pyproject.toml`에 명시된 의존성을 설치합니다.

```bash
# 가상환경 생성 (UV 권장)
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 패키지 설치
uv pip install -r pyproject.toml
```

### 1.3 환경 변수 설정 (.env)

`.env` 파일을 생성하고 다음 키를 입력하세요.

```ini
# OpenAI (필수)
OPENAI_API_KEY=sk-proj-...

# Anthropic (선택)
ANTHROPIC_API_KEY=sk-ant-...

# Naver News Search (필수)
NAVER_CLIENT_ID=your_client_id
NAVER_CLIENT_SECRET=your_client_secret

# Tistory Publishing (선택)
TISTORY_ID=your_email
TISTORY_PASSWORD=your_password
```

---

## 2. 실행 방법

### 2.1 대화형 인터페이스 (CLI)

가장 쉬운 실행 방법입니다. 터미널에서 채팅하듯이 에이전트와 대화할 수 있습니다.

```bash
python -m app.core.agent.main
```

**사용 예시**:

```
[Supervisor Agent] 안녕하세요! 부동산 호재/악재 분석 에이전트입니다.
궁금하신 지역이나 내용을 입력해주세요. (종료: quit)

User > 강남역 주변 호재 알려줘

... (에이전트 실행 로그 출력) ...

[OK] 완료! SEO 점수: 88점
[제목] 강남역 GTX-A 개통과 주변 상권 변화 분석
```

### 2.2 코드에서 실행

Python 코드 내에서 에이전트를 모듈로 사용할 수 있습니다.

```python
import asyncio
from app.core.agent import RegionalPolicyAgent

async def main():
    agent = RegionalPolicyAgent()

    # 1. 실행
    result = await agent.run("경기도 성남시 분당구 재건축 이슈")

    # 2. 결과 확인
    content = result.get("final_content")
    if content:
        print(f"제목: {content.blog_title}")
        print(f"URL: {result.get('post_url')}")

        # 딕셔너리로 변환 (DB 저장 등 활용)
        blog_data = agent.get_blog_content(content)
        print(blog_data)

if __name__ == "__main__":
    asyncio.run(main())
```
