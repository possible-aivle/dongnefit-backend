"""프로세서 베이스 클래스."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.models.enums import PublicDataType


@dataclass
class ProcessResult:
    """처리 결과."""

    collected: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0

    def summary(self) -> str:
        parts = []
        if self.collected:
            parts.append(f"수집: {self.collected}건")
        if self.inserted:
            parts.append(f"신규: {self.inserted}건")
        if self.updated:
            parts.append(f"업데이트: {self.updated}건")
        if self.skipped:
            parts.append(f"스킵: {self.skipped}건")
        if self.errors:
            parts.append(f"에러: {self.errors}건")
        return " | ".join(parts) if parts else "처리된 데이터 없음"


class BaseProcessor(ABC):
    """데이터 프로세서 베이스 클래스.

    각 공공데이터 소스별로 이 클래스를 상속하여 구현합니다.
    수집(collect) → 변환(transform) → 적재(load)를 하나의 클래스에서 관리합니다.

    구현 예시:
        class CadastralProcessor(BaseProcessor):
            name = "cadastral"
            description = "연속지적도"
            data_type = PublicDataType.CONTINUOUS_CADASTRAL

            async def collect(self, params):
                # shp 파일 읽기 또는 API 호출
                ...

            def transform(self, raw_data):
                # raw → dict 리스트 (DB 컬럼에 맞게)
                ...

            def get_params_interactive(self):
                # CLI에서 사용자 입력
                ...
    """

    name: str  # 예: "cadastral"
    description: str  # 예: "연속지적도 (vworld)"
    data_type: PublicDataType  # 예: PublicDataType.CONTINUOUS_CADASTRAL

    @abstractmethod
    async def collect(self, params: dict[str, Any]) -> list[dict]:
        """외부 소스에서 원본 데이터를 수집합니다.

        Returns:
            raw dict 리스트
        """
        ...

    @abstractmethod
    def transform(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """수집된 원본 데이터를 DB 컬럼에 맞게 변환합니다.

        Returns:
            DB insert/upsert용 dict 리스트
        """
        ...

    @abstractmethod
    def get_params_interactive(self) -> dict[str, Any]:
        """CLI에서 사용자에게 파라미터를 입력받습니다.

        Returns:
            수집에 필요한 파라미터 dict (지역, 기간 등)
        """
        ...

    async def run(self, params: dict[str, Any] | None = None) -> ProcessResult:
        """수집 → 변환 → 적재 전체 파이프라인을 실행합니다."""
        if params is None:
            params = self.get_params_interactive()

        raw = await self.collect(params)
        if not raw:
            return ProcessResult()

        records = self.transform(raw)
        result = await self.load(records)
        result.collected = len(raw)
        return result

    async def load(self, records: list[dict[str, Any]]) -> ProcessResult:
        """변환된 데이터를 DB에 적재합니다.

        기본 구현은 pipeline.loader의 bulk_upsert를 사용합니다.
        소스별로 오버라이드할 수 있습니다.
        """
        from app.database import async_session_maker
        from pipeline.loader import bulk_upsert

        async with async_session_maker() as session:
            result = await bulk_upsert(session, self.data_type, records)

        return result
