# SEO AI Agent 가이드

SEO AI Agent는 LangGraph 기반의 블로그 콘텐츠 분석 및 최적화 도구입니다. 이 문서는 SEO Agent의 구조, 파일별 역할, 점수 계산 방식 수정 방법, 그리고 사용법을 상세히 설명합니다.

## 1. 파일 구조 및 역할 (`app/core/seo_agent/`)

SEO Agent는 모듈화된 설계를 따르며, 각 파일은 명확한 역할을 가집니다.

| 파일명 | 역할 및 설명 |
| :--- | :--- |
| `agent.py` | **메인 진입점 (Entry Point)**<br>- 외부에서 SEO 기능을 사용할 때 호출하는 인터페이스입니다.<br>- `SEOAgent` 클래스를 정의하며, 워크플로우를 실행하고 결과를 반환합니다. |
| `workflow.py` | **워크플로우 정의 (LangGraph)**<br>- 분석 및 개선 프로세스의 순서를 정의합니다.<br>- `build_seo_workflow` 함수에서 노드(작업)와 엣지(흐름)를 연결합니다.<br>- 주요 흐름: `입력 검증` → `점수 계산` → `이슈 분석` → `콘텐츠 개선` → `재점수 계산` |
| `tools.py` | **개별 기능 구현 (Tools)**<br>- 워크플로우의 각 단계에서 실제로 수행되는 작업을 정의합니다.<br>- `analyze_seo_score` (점수 계산), `improve_content` (LLM을 이용한 본문 수정) 등의 핵심 함수가 포함됩니다. |
| `scoring.py` | **SEO 점수 계산 엔진**<br>- 결정적 알고리즘(수식)을 기반으로 SEO 점수를 계산합니다.<br>- LLM을 사용하지 않고, 텍스트 분석(길이, 키워드 밀도, 헤딩 개수 등)을 통해 빠르고 일관된 점수를 제공합니다. |
| `models.py` | **데이터 모델 (Pydantic)**<br>- 시스템에서 사용하는 데이터의 구조를 정의합니다.<br>- `BlogDraft` (초안), `SEOScoreBreakdown` (점수표), `SEOIssue` (발견된 문제점) 등의 클래스가 있습니다. |
| `__init__.py` | **패키지 초기화**<br>- 외부에서 모듈을 쉽게 import 할 수 있도록 주요 클래스를 노출합니다. |

---

## 2. SEO 점수 기준 수정 방법

SEO 점수 계산은 `scoring.py` 파일 내부의 **상수(Constants)**와 **로직**에 의해 결정됩니다.

### 2.1 가중치 수정 (Weight)
각 영역이 총점에서 차지하는 비중을 변경하려면 `WEIGHTS` 딕셔너리를 수정하세요.
(단, 총합이 100이 되도록 맞춰야 합니다.)

```python
# app/core/seo_agent/scoring.py

class SEOScorer:
    WEIGHTS = {
        "title": 20,              # 제목 (20점)
        "content_structure": 25,  # 본문 구조 (25점)
        "keyword": 20,            # 키워드 최적화 (20점)
        "readability": 15,        # 가독성 (15점)
        "metadata": 20,           # 메타데이터 (20점)
    }
```

### 2.2 세부 기준값 수정 (Thresholds)
각 항목의 "최적 범위"를 변경하려면 클래스 상수를 수정하세요.

```python
# app/core/seo_agent/scoring.py

    # 예: 제목 길이의 최적 범위를 25-60자에서 20-50자로 변경하고 싶다면:
    OPTIMAL_TITLE_LENGTH_MIN = 20  # 기존 25
    OPTIMAL_TITLE_LENGTH_MAX = 50  # 기존 60

    # 예: 적정 키워드 밀도를 1.0-3.0%에서 0.5-2.0%로 낮추고 싶다면:
    OPTIMAL_KEYWORD_DENSITY_MIN = 0.5
    OPTIMAL_KEYWORD_DENSITY_MAX = 2.0
```

---

## 3. 상세 기능 설명

### 3.1 분석 단계 (Analysis)
1.  **점수 계산 (`scoring.py`)**: 제출된 초안을 분석하여 5가지 영역별로 점수를 매깁니다.
2.  **이슈 추출 (`tools.py`)**: 점수가 깎인 항목에 대해 LLM이 구체적인 문제가 무엇인지, 어떻게 고쳐야 하는지 진단합니다.

### 3.2 개선 단계 (Improvement)
1.  **선택적 개선**: 사용자가 선택한 항목(예: 제목, 구조)만 집중적으로 개선합니다.
2.  **최소 수정 원칙**: 원본의 스타일과 내용은 최대한 유지하면서, SEO 기준에 미달하는 부분만 부분적으로 수정합니다.
3.  **검증**: 수정된 내용으로 다시 점수를 계산하여 실제로 점수가 올랐는지 확인합니다.

---