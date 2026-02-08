## tistory 디렉토리 설명

1. `config.py`: 환경 변수와 인증 정보 관리
2. `content_generator.py`: ChatGPT를 사용한 콘텐츠 생성
3. `keyword_extractor.py`: 키워드 추출 기능
4. `tistory_poster.py`: 티스토리 포스팅 관련 기능
5. `main.py`: 메인 실행 파일

각 파일의 역할은 다음과 같습니다:

1. `config.py`
   - 환경 변수 로드
   - 인증 정보 관리 클래스 및 함수 정의

2. `content_generator.py`
   - ChatGPT API 연동
   - 블로그 제목 및 본문 생성 함수

3. `keyword_extractor.py`
   - krwordrank를 사용한 키워드 추출 기능

4. `tistory_poster.py`
   - Selenium을 사용한 티스토리 자동 포스팅
   - 로그인, 글쓰기, 발행 기능

5. `main.py`
   - 전체 프로세스 실행
   - 예외 처리

