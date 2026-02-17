"""PNU(필지고유번호) 유틸리티 함수.

PNU는 19자리 숫자 문자열로 아래 구조를 가짐:
  시도(2) + 시군구(3) + 읍면동(3) + 리(2) + 산구분(1) + 본번(4) + 부번(4)
"""


def sido_code(pnu: str) -> str:
    """PNU에서 시도코드(2자리)를 추출합니다."""
    return pnu[:2]


def sgg_code(pnu: str) -> str:
    """PNU에서 시군구코드(5자리: 시도+시군구)를 추출합니다."""
    return pnu[:5]


def emd_code(pnu: str) -> str:
    """PNU에서 읍면동코드(8자리: 시도+시군구+읍면동)를 추출합니다."""
    return pnu[:8]


def ri_code(pnu: str) -> str:
    """PNU에서 리코드(10자리: 시도+시군구+읍면동+리)를 추출합니다."""
    return pnu[:10]


def is_mountain(pnu: str) -> bool:
    """PNU에서 산 여부를 확인합니다 (11번째 자리가 '2'이면 산)."""
    return pnu[10] == "2"


def main_number(pnu: str) -> str:
    """PNU에서 본번(4자리)을 추출합니다."""
    return pnu[11:15]


def sub_number(pnu: str) -> str:
    """PNU에서 부번(4자리)을 추출합니다."""
    return pnu[15:19]
