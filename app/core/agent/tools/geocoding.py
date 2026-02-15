"""Geocoding utilities for address to administrative region conversion."""

import re
from typing import Optional

from app.core.agent.models import AddressInput, AdminRegion


class GeocodingService:
    """주소를 행정구역으로 변환하는 서비스."""

    # 시/도 목록
    SIDO_LIST = [
        "서울특별시",
        "부산광역시",
        "대구광역시",
        "인천광역시",
        "광주광역시",
        "대전광역시",
        "울산광역시",
        "세종특별자치시",
        "경기도",
        "강원도",
        "충청북도",
        "충청남도",
        "전라북도",
        "전라남도",
        "경상북도",
        "경상남도",
        "제주특별자치도",
    ]

    # 약어 매핑
    SIDO_ABBR_MAP = {
        "서울": "서울특별시",
        "부산": "부산광역시",
        "대구": "대구광역시",
        "인천": "인천광역시",
        "광주": "광역시",
        "대전": "대전광역시",
        "울산": "울산광역시",
        "세종": "세종특별자치시",
        "경기": "경기도",
        "강원": "강원도",
        "충북": "충청북도",
        "충남": "충청남도",
        "전북": "전라북도",
        "전남": "전라남도",
        "경북": "경상북도",
        "경남": "경상남도",
        "제주": "제주특별자치도",
    }

    def parse_address(self, address_input: AddressInput) -> AdminRegion:
        """
        주소를 파싱하여 행정구역 정보를 추출합니다.

        현재는 간단한 정규식 기반 파싱을 사용합니다.
        추후 Kakao/Naver/공공데이터 Geocoding API로 교체 가능합니다.

        Args:
            address_input: 사용자 입력 주소

        Returns:
            AdminRegion: 파싱된 행정구역 정보

        Raises:
            ValueError: 주소 파싱 실패 시
        """
        address = address_input.address.strip()

        # 1. 시/도 추출
        sido = self._extract_sido(address)
        if not sido:
            raise ValueError(f"주소에서 시/도를 찾을 수 없습니다: {address}")

        # 2. 시/군/구 추출
        sigungu = self._extract_sigungu(address)
        if not sigungu:
            raise ValueError(f"주소에서 시/군/구를 찾을 수 없습니다: {address}")

        # 3. 읍/면/동 추출 (선택)
        dong = self._extract_dong(address)

        # 전체 주소 구성
        full_parts = [sido, sigungu]
        if dong:
            full_parts.append(dong)
        full_address = " ".join(full_parts)

        return AdminRegion(
            sido=sido, sigungu=sigungu, dong=dong, full_address=full_address
        )

    def _extract_sido(self, address: str) -> Optional[str]:
        """시/도 추출."""
        # 완전한 이름 먼저 확인
        for sido in self.SIDO_LIST:
            if sido in address:
                return sido

        # 약어 확인
        for abbr, full_name in self.SIDO_ABBR_MAP.items():
            if abbr in address:
                return full_name

        return None

    def _extract_sigungu(self, address: str) -> Optional[str]:
        """시/군/구 추출."""
        # 패턴: "OO시", "OO군", "OO구"
        pattern = r"([가-힣]+(?:시|군|구))"
        matches = re.findall(pattern, address)

        if matches:
            # 첫 번째가 시/도라면 두 번째 반환
            if len(matches) > 1:
                return matches[1]
            # 그렇지 않으면 첫 번째 반환
            return matches[0]

        return None

    def _extract_dong(self, address: str) -> Optional[str]:
        """읍/면/동 추출."""
        # 패턴: "OO동", "OO읍", "OO면"
        pattern = r"([가-힣]+(?:동|읍|면))"
        matches = re.findall(pattern, address)

        if matches:
            # 마지막 매치 반환 (가장 하위 행정구역)
            return matches[-1]

        return None

    def generate_search_keywords(self, admin_region: AdminRegion) -> list[str]:
        """
        행정구역 기반 검색 키워드 생성.

        Args:
            admin_region: 행정구역 정보

        Returns:
            검색 키워드 목록
        """
        keywords = []

        # 기본 검색어: "시/군/구" + 카테고리별 키워드
        base = admin_region.sigungu

        # 교통 관련
        keywords.extend(
            [
                f"{base} GTX",
                f"{base} 지하철",
                f"{base} 역세권",
                f"{base} 도로",
            ]
        )

        # 개발 관련
        keywords.extend(
            [
                f"{base} 재개발",
                f"{base} 재건축",
                f"{base} 개발",
                f"{base} 산업단지",
            ]
        )

        # 정책 관련
        keywords.extend(
            [
                f"{base} 토지거래허가구역",
                f"{base} 규제",
                f"{base} 정책",
            ]
        )

        # 동 단위가 있으면 더 구체적인 키워드 추가
        if admin_region.dong:
            dong_base = f"{admin_region.sigungu} {admin_region.dong}"
            keywords.extend(
                [
                    f"{dong_base} 개발",
                    f"{dong_base} 부동산",
                ]
            )

        return keywords
