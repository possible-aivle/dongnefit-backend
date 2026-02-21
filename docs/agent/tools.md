# 🛠️ 유틸리티 도구 (Tools)

## 1. GeocodingService — 주소 변환

> **파일**: `tools/geocoding.py`

### 개요

사용자의 입력 주소를 파싱하여 행정구역 정보(시/도, 시/군/구, 읍/면/동)로 변환하고, 뉴스 검색에 사용할 키워드를 생성합니다.

### 주요 기능

1.  **주소 파싱**:
    -   정규식 패턴을 사용하여 다양한 주소 형식 인식
    -   예: "서울시 강남구 역삼동", "경기 성남 분당", "강원도 춘천" 등

2.  **검색 키워드 생성** (`generate_search_keywords`):
    -   지역명을 조합하여 다양한 검색어 자동 생성
    -   예: "강남구 역삼동 부동산 호재", "역삼동 재개발", "강남구 교통 분석"

3.  **좌표 변환 (미구현)**:
    -   필요 시 Google Maps 또는 Naver Maps API 연동 가능 구조

---

## 2. TistoryWriter — 티스토리 발행

> **파일**: `tools/tistory_publisher.py` (구 `tistory_writer.py`)

### 개요

Selenium을 사용하여 생성된 콘텐츠를 티스토리 블로그에 자동으로 포스팅합니다. 카카오 계정 로그인을 지원합니다.

### 주요 기능

1.  **로그인 (`login`)**:
    -   `TISTORY_ID`, `TISTORY_PASSWORD` 환경 변수 사용
    -   카카오 로그인 페이지 자동 처리

2.  **글 작성 (`write_post`)**:
    -   제목, 본문(HTML/Markdown), 카테고리, 태그 설정
    -   이미지 업로드 지원

3.  **발행 완료 처리**:
    -   "발행" 버튼 클릭 및 완료 URL 반환

### 주의사항

-   **2단계 인증(2FA)**: 카카오 계정에 2FA가 설정된 경우 자동 로그인이 막힐 수 있습니다. 실행 시 브라우저에서 수동으로 승인해야 할 수 있습니다.
-   **헤드리스 모드**: 현재 디버깅을 위해 브라우저가 보이도록 설정되어 있습니다 (`headless=False`). 배포 시 변경 가능합니다.

---

## 3. 생활편의시설 도구 (ConvenienceToolService)

> **파일**: `app/core/agent/tools/convenience.py`

### 개요

생활편의시설(대규모점포, 골프장, 목욕장업, 미용업, 세탁업, 수영장업, 이용업, 체력단련장업, 세차장) 데이터를 검색하고 주변 시설을 조회하는 도구입니다.

### 데이터 소스

-   **방식**: 로컬 CSV 파일
-   **위치**: `app/core/api_data/convenience/`
-   **파일 목록**:
    -   `생활_대규모점포_전처리.csv`
    -   `생활_골프장_전처리.csv`
    -   `생활_목욕장업_전처리.csv`
    -   `생활_미용업_전처리.csv`
    -   `생활_세탁업_전처리.csv`
    -   `생활_수영장업_전처리.csv`
    -   `생활_이용업_전처리.csv`
    -   `생활_체력단련장업_전처리.csv`
    -   `세차장정보_전처리.csv`
-   **좌표계**: EPSG:5174 → WGS84 변환 (pyproj 사용)

### 주요 기능

1.  **이름 검색** (`search`):
    -   사업장명/주소 키워드로 검색
    -   카테고리별로 그룹핑하여 반환
    -   예: "이마트", "강남 헬스장"

2.  **주변 검색** (`near`):
    -   좌표(위도/경도) 기준 반경 내 시설 검색
    -   Haversine 공식으로 직선거리 계산
    -   거리순 정렬 및 도보시간 추정

### Flow

1.  `ConvenienceToolService` 초기화 → `ConvenienceRepository` 생성
2.  첫 호출 시 CSV 파일들을 로드하여 DataFrame으로 변환 (lazy loading)
3.  EPSG:5174 좌표를 WGS84로 변환
4.  검색/주변 검색 수행
5.  결과를 카테고리별로 그룹핑하여 반환

### Talk API Response

-   **Tool 이름**: `convenience_search`, `convenience_near`
-   **Response 구조**:
    -   `convenience_near` 호출 시 `_extract_convenience_json()` 함수가 trace에서 결과 추출
    -   최종 `answer` 필드에 다음 구조의 JSON 문자열 반환:
    ```json
    {
      "property_name": "주소명",
      "property_lat": 위도,
      "property_lng": 경도,
      "facilities": {
        "카테고리명": [
          {
            "name": "시설명",
            "category": "카테고리",
            "lat": 위도,
            "lng": 경도,
            "phone": "전화번호" // 선택적
          }
        ]
      }
    }
    ```

---

## 4. 식품점 도구 (GroceryToolService)

> **파일**: `app/core/agent/tools/grocery.py`

### 개요

식품점(일반음식점, 제과점영업, 휴게음식점) 데이터를 검색하고 주변 식당을 조회하는 도구입니다.

### 데이터 소스

-   **방식**: 로컬 CSV 파일
-   **위치**: `app/core/api_data/grocery/`
-   **파일 목록**:
    -   `식품_일반음식점_전처리.csv`
    -   `식품_제과점영업_전처리.csv`
    -   `식품_휴게음식점_전처리.csv`
-   **좌표계**: EPSG:5174 → WGS84 변환 (pyproj 사용)

### 주요 기능

1.  **이름 검색** (`search`):
    -   사업장명/주소 키워드로 검색
    -   업종구분별로 그룹핑하여 반환

2.  **주변 검색** (`near`):
    -   좌표 기준 반경 내 식품점 검색
    -   거리순 정렬 및 도보시간 추정

### Flow

1.  `GroceryToolService` 초기화 → `GroceryRepository` 생성
2.  첫 호출 시 CSV 파일들을 로드하여 DataFrame으로 변환
3.  EPSG:5174 좌표를 WGS84로 변환
4.  검색/주변 검색 수행
5.  결과를 업종구분별로 그룹핑하여 반환

### Talk API Response

-   **Tool 이름**: `grocery_search`, `grocery_near`
-   **Response 구조**:
    -   `grocery_near` 호출 시 `_extract_grocery_json()` 함수가 trace에서 결과 추출
    -   최종 `answer` 필드에 다음 구조의 JSON 문자열 반환:
    ```json
    {
      "property_name": "주소명",
      "property_lat": 위도,
      "property_lng": 경도,
      "restaurants": {
        "업종구분": [
          {
            "name": "식당명",
            "category": "카테고리",
            "lat": 위도,
            "lng": 경도,
            "phone": "전화번호", // 선택적
            "website": "홈페이지" // 선택적
          }
        ]
      }
    }
    ```

---

## 5. 의료시설 도구 (HospitalToolService)

> **파일**: `app/core/agent/tools/hospital.py`

### 개요

의료시설(병원, 의원, 약국, 부속의료기관, 산후조리업, 응급환자이송업) 데이터를 검색하고 주변 의료시설을 조회하는 도구입니다.

### 데이터 소스

-   **방식**: 로컬 CSV 파일
-   **위치**: `app/core/api_data/hospital/`
-   **파일 목록**:
    -   `건강_병원_전처리.csv`
    -   `건강_의원_전처리.csv`
    -   `건강_약국_전처리.csv`
    -   `건강_부속의료기관_전처리.csv`
    -   `건강_산후조리업_전처리.csv`
    -   `건강_응급환자이송업_전처리.csv`
-   **좌표계**: EPSG:5174 → WGS84 변환 (pyproj 사용)

### 주요 기능

1.  **이름 검색** (`search`):
    -   사업장명/주소 키워드로 검색
    -   업태구분명별로 그룹핑하여 반환

2.  **주변 검색** (`near`):
    -   좌표 기준 반경 내 의료시설 검색
    -   거리순 정렬 및 도보시간 추정
    -   병원/의원의 경우 진료과목, 병상수, 입원실수 정보 포함

### Flow

1.  `HospitalToolService` 초기화 → `HospitalRepository` 생성
2.  첫 호출 시 CSV 파일들을 로드하여 DataFrame으로 변환
3.  EPSG:5174 좌표를 WGS84로 변환
4.  검색/주변 검색 수행
5.  결과를 업태구분명별로 그룹핑하여 반환

### Talk API Response

-   **Tool 이름**: `hospital_search`, `hospital_near`
-   **Response 구조**:
    -   `hospital_near` 호출 시 `_extract_hospital_json()` 함수가 trace에서 결과 추출
    -   최종 `answer` 필드에 다음 구조의 JSON 문자열 반환:
    ```json
    {
      "property_name": "주소명",
      "property_lat": 위도,
      "property_lng": 경도,
      "hospitals": {
        "업태구분명": [
          {
            "name": "의료시설명",
            "category": "의료기관종별명",
            "lat": 위도,
            "lng": 경도,
            "phone": "전화번호", // 선택적
            "specialty": "진료과목", // 선택적 (병원/의원)
            "beds": 병상수, // 선택적 (병원/의원)
            "rooms": 입원실수 // 선택적 (병원/의원)
          }
        ]
      }
    }
    ```

---

## 6. 동물 관련 시설 도구 (AnimalHospitalToolService)

> **파일**: `app/core/agent/tools/hospital_animal.py`

### 개요

동물 관련 시설(동물병원, 동물약국, 동물미용업) 데이터를 검색하고 주변 시설을 조회하는 도구입니다.

### 데이터 소스

-   **방식**: 로컬 CSV 파일
-   **위치**: `app/core/api_data/hospital_animal/`
-   **파일 목록**:
    -   `동물_동물병원_전처리.csv`
    -   `동물_동물약국_전처리.csv`
    -   `동물_동물미용업_전처리.csv`
-   **좌표계**: EPSG:5174 → WGS84 변환 (pyproj 사용)

### 주요 기능

1.  **이름 검색** (`search`):
    -   사업장명/주소 키워드로 검색
    -   업태구분명별로 그룹핑하여 반환

2.  **주변 검색** (`near`):
    -   좌표 기준 반경 내 동물 관련 시설 검색
    -   거리순 정렬 및 도보시간 추정

### Flow

1.  `AnimalHospitalToolService` 초기화 → `AnimalHospitalRepository` 생성
2.  첫 호출 시 CSV 파일들을 로드하여 DataFrame으로 변환
3.  EPSG:5174 좌표를 WGS84로 변환
4.  검색/주변 검색 수행
5.  결과를 업태구분명별로 그룹핑하여 반환

### Talk API Response

-   **Tool 이름**: `animal_search`, `animal_near`
-   **Response 구조**:
    -   `animal_near` 호출 시 `_extract_animal_json()` 함수가 trace에서 결과 추출
    -   최종 `answer` 필드에 다음 구조의 JSON 문자열 반환:
    ```json
    {
      "property_name": "주소명",
      "property_lat": 위도,
      "property_lng": 경도,
      "animals": {
        "업태구분명": [
          {
            "name": "시설명",
            "category": "카테고리",
            "lat": 위도,
            "lng": 경도,
            "phone": "전화번호" // 선택적
          }
        ]
      }
    }
    ```

---

## 7. 공원 도구 (ParkToolService)

> **파일**: `app/core/agent/tools/park.py`

### 개요

도시공원 데이터를 검색하고 주변 공원을 조회하는 도구입니다.

### 데이터 소스

-   **방식**: 로컬 JSON 파일
-   **위치**: `app/core/api_data/etc/`
-   **파일명**: `전국도시공원정보표준데이터.json`
-   **좌표계**: WGS84 (이미 변환된 데이터)

### 주요 기능

1.  **이름 검색** (`search`):
    -   공원명/주소 키워드로 검색
    -   지역 필터 옵션 지원

2.  **주변 검색** (`near`):
    -   좌표 기준 반경 내 공원 검색
    -   Haversine 공식으로 직선거리 계산
    -   거리순 정렬 및 도보시간 추정

### Flow

1.  `ParkToolService` 초기화 → `ParkRepository` 생성
2.  첫 호출 시 JSON 파일을 로드하여 DataFrame으로 변환 (lazy loading)
3.  검색/주변 검색 수행
4.  결과를 리스트로 반환

### Talk API Response

-   **Tool 이름**: `park_search`, `park_near`
-   **Response 구조**:
    -   `park_near` 호출 시 `_extract_park_json()` 함수가 trace에서 결과 추출
    -   최종 `answer` 필드에 다음 구조의 JSON 문자열 반환:
    ```json
    {
      "property_name": "주소명",
      "property_lat": 위도,
      "property_lng": 경도,
      "parks": [
        {
          "name": "공원명",
          "type": "공원구분",
          "lat": 위도,
          "lng": 경도
        }
      ]
    }
    ```

---

## 8. 하천 도구 (RiverToolService)

> **파일**: `app/core/agent/tools/river.py`

### 개요

하천 데이터를 검색하고 주변 하천을 조회하는 도구입니다. 이름 검색은 로컬 데이터를 사용하고, 주변 검색은 VWorld API를 사용합니다.

### 데이터 소스

#### 이름 검색 (search)

-   **방식**: 로컬 JSON 파일
-   **위치**: `app/core/api_data/etc/`
-   **파일명**: `전국하천표준데이터.json`

#### 주변 검색 (near)

-   **방식**: VWorld 하천망 API
-   **API 엔드포인트**: VWorld 하천망 API (`VWorldClient.get_rivers_near()`)
-   **특징**: 실제 하천 경로(LineString) 기준 최단 거리 계산

### 주요 기능

1.  **이름 검색** (`search`):
    -   하천명(제1/2지류 포함)으로 검색
    -   로컬 JSON 파일에서 검색

2.  **주변 검색** (`near`):
    -   좌표 기준 반경 내 하천 검색
    -   VWorld API로 하천망 데이터 조회
    -   LineString/Polygon 등 다양한 지오메트리 타입 지원
    -   실제 경로 기준 최단 거리 계산 (직선거리 아님)
    -   하천 중심점(lat, lng) 계산

### Flow

1.  `RiverToolService` 초기화 → `RiverRepository` 생성
2.  **이름 검색**:
    -   첫 호출 시 JSON 파일을 로드하여 DataFrame으로 변환
    -   하천명/제1지류명/제2지류명으로 검색
3.  **주변 검색**:
    -   `VWorldClient` 인스턴스 생성
    -   `get_rivers_near()` API 호출
    -   반환된 Feature들을 `feature_to_river_dict()`로 변환
    -   LineString에서 점까지의 최단 거리 계산
    -   거리순 정렬 후 반환

### Talk API Response

-   **Tool 이름**: `river_search`, `river_near`
-   **Response 구조**:
    -   `river_near` 호출 시 `_extract_river_json()` 함수가 trace에서 결과 추출
    -   최종 `answer` 필드에 다음 구조의 JSON 문자열 반환:
    ```json
    {
      "property_name": "주소명",
      "property_lat": 위도,
      "property_lng": 경도,
      "rivers": [
        {
          "name": "하천명",
          "type": "하천구분명",
          "lat": 중심점_위도,
          "lng": 중심점_경도
        }
      ]
    }
    ```

---

## 9. 학교 도구 (SchoolToolService)

> **파일**: `app/core/agent/tools/school.py`

### 개요

학교 위치 및 학구 데이터를 검색하고 주변 학교를 조회하는 도구입니다.

### 데이터 소스

-   **방식**: 로컬 JSON 파일
-   **위치**: `app/core/api_data/school/`
-   **파일 목록**:
    -   `전국초중등학교위치표준데이터.json` (학교 위치)
    -   `전국초등학교통학구역표준데이터.json` (초등학교 학구)
    -   `전국중학교학교군표준데이터.json` (중학교 학교군)
    -   `전국고등학교학교군표준데이터.json` (고등학교 학교군)
    -   `전국고등학교비평준화지역표준데이터.json` (고등학교 비평준화)
    -   `전국교육행정구역표준데이터.json` (교육행정구역)
    -   `전국학교학구도연계정보표준데이터.json` (학교-학구 연계)
-   **좌표계**: WGS84 (이미 변환된 데이터)

### 주요 기능

1.  **지역 검색** (`search`):
    -   지역명으로 학교 검색
    -   학교 유형 필터 지원 (초등학교/중학교/고등학교)

2.  **이름 검색** (`get_latlng`, `get_address`):
    -   학교명으로 위치/주소 조회

3.  **주변 검색** (`near`):
    -   좌표 기준 반경 내 학교 검색
    -   Haversine 공식으로 직선거리 계산
    -   거리순 정렬 및 도보시간 추정

4.  **그룹핑 주변 검색** (`near_grouped`):
    -   초등학교/중학교/고등학교를 각각 거리순으로 조회
    -   각 유형별로 limit_per_type개씩 반환

5.  **학구 검색** (`zone_search`, `zone_by_school`):
    -   학구/학교군 데이터 검색 (좌표 없음)

### Flow

1.  `SchoolToolService` 초기화 → `SchoolRepository` 생성
2.  첫 호출 시 JSON 파일들을 로드하여 DataFrame으로 변환 (lazy loading)
3.  검색/주변 검색 수행
4.  결과를 리스트 또는 그룹핑된 딕셔너리로 반환

### Talk API Response

-   **Tool 이름**: `school_search`, `school_near`, `school_near_grouped`, `school_zone_search`, `school_zone_by_school`
-   **Response 구조**:
    -   `school_near_grouped` 호출 시 `_extract_school_json()` 함수가 trace에서 결과 추출
    -   최종 `answer` 필드에 다음 구조의 JSON 문자열 반환:
    ```json
    {
      "property_name": "주소명",
      "property_lat": 위도,
      "property_lng": 경도,
      "elementary_schools": [
        {
          "name": "학교명",
          "lat": 위도,
          "lng": 경도
        }
      ],
      "middle_schools": [...],
      "high_schools": [...]
    }
    ```

---

## 공통 Flow (Talk API)

모든 도구는 다음과 같은 공통 흐름으로 Talk API에 통합됩니다:

1.  **Tool 등록** (`talk_agent.py`의 `build_tools()`):
    -   각 ToolService 인스턴스 생성
    -   `@tool` 데코레이터로 LangChain tool로 등록
    -   tool 이름: `{category}_search`, `{category}_near` 형식

2.  **Agent 실행** (`run_talk()`):
    -   LangGraph의 `create_react_agent`로 agent 생성
    -   사용자 메시지 처리 및 tool 호출
    -   tool 호출 결과를 trace에 저장

3.  **Response 생성**:
    -   trace에서 tool 호출 결과 추출
    -   `_extract_{category}_json()` 함수로 구조화된 JSON 생성
    -   `vworld_get_coord` 결과와 결합하여 property 정보 포함
    -   최종 `answer` 필드에 JSON 문자열로 반환

4.  **Response 구조**:
    ```json
    {
      "answer": "JSON 문자열 또는 텍스트",
      "messages": [...],
      "trace": [
        {
          "name": "tool_name",
          "content": {...},
          "tool_call_id": "..."
        }
      ]
    }
    ```
