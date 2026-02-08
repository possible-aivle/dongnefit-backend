import os
from dataclasses import dataclass

from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


# 인증 정보 데이터 클래스
@dataclass
class Credentials:
    openai_api_key: str
    tistory_id: str
    tistory_password: str


# 인증 정보 가져오기
def get_credentials() -> Credentials:
    # 환경 변수에서 API 키와 티스토리 인증 정보 가져오기
    openai_api_key = os.getenv("OPENAI_API_KEY")
    tistory_id = os.getenv("TISTORY_ID")
    tistory_password = os.getenv("TISTORY_PASSWORD")

    # 필수 환경 변수가 설정되지 않았을 경우 ValueError 발생
    if not all([openai_api_key, tistory_id, tistory_password]):
        raise ValueError(
            "필수 환경 변수가 설정되지 않았습니다. .env 파일을 확인해주세요."
        )

    # 인증 정보 반환
    return Credentials(openai_api_key, tistory_id, tistory_password)
