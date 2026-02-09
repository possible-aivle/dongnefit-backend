## uv 세팅

### 설치법
1. uv 설치
   - macOS 또는 Linux
     - brew install uv
   - window
     - pip install uv
     - pipx install uv
2. uv init (디렉토리 위치, ex. uv init .)
   - 파이썬 프로젝트를 생성하는 명령어로, 실행하게 되면 pyproject.toml 파일을 생성합니다. 함께 활용하는 명령어는 다음과 같습니다.
3. uv python install 3.12 3.13 ...
   - 원하는 파이썬 버전으로 설치
4. uv venv --python 3.13
   - 현재 바라보고 있는 디렉토리 바로 아래에 .venv 디렉토리를 만들고 python 을 원하는 버전으로 설치
5. uv add <패키지명>
   - 가상환경에 특정 패키지 설치
6. uv sync
   - 종속성을 환경과 동기화함
7. 인터프리터를 .venv 바라보도록 수정

### 명령어들
- `uv init`: 새로운 파이썬 프로젝트를 생성함
- `uv add`: 프로젝트의 종속성을 추가함
- `uv remove`: 프로젝트의 종속성을 삭제함
- `uv sync`: 프로젝트의 종속성을 환경과 동기화함
- `uv lock`: 프로젝트의 종속성에 대한 잠금 파일을 생성함
- `uv run`: 프로젝트 환경에서 명령어를 실행함
- `uv tree`: 프로젝트의 종속성 트리를 확인할 수 있음
- `uv build`: 프로젝트를 배포 아카이브로 빌드함
- `uv publish`: 프로젝트를 패키지 인덱스에 게시함
