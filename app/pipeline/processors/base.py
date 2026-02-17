"""프로세서 베이스 클래스."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.models.enums import PublicDataType


@dataclass
class ProcessResult:
    """처리 결과.

    Note: upsert 연산 시 inserted는 실제 삽입+업데이트 합계입니다.
    PostgreSQL ON CONFLICT DO UPDATE의 rowcount는 둘을 구분하지 않습니다.
    """

    collected: int = 0
    inserted: int = 0
    skipped: int = 0
    errors: int = 0

    def summary(self) -> str:
        parts = []
        if self.collected:
            parts.append(f"수집: {self.collected}건")
        if self.inserted:
            parts.append(f"적재: {self.inserted}건")
        if self.skipped:
            parts.append(f"스킵: {self.skipped}건")
        if self.errors:
            parts.append(f"에러: {self.errors}건")
        return " | ".join(parts) if parts else "처리된 데이터 없음"


class BaseProcessor(ABC):
    """데이터 프로세서 베이스 클래스.

    각 공공데이터 소스별로 이 클래스를 상속하여 구현합니다.
    수집(collect) → 변환(transform) → 적재(load)를 하나의 클래스에서 관리합니다.
    """

    name: str  # 예: "cadastral"
    description: str  # 예: "연속지적도 (vworld)"
    data_type: PublicDataType  # 예: PublicDataType.CONTINUOUS_CADASTRAL
    simplify_tolerance: float | None = None  # geometry 단순화 허용 오차 (도 단위)

    @staticmethod
    def _aggregate_jsonb(
        records: list[dict[str, Any]], jsonb_column: str
    ) -> list[dict[str, Any]]:
        """1:N 레코드를 PNU별로 그룹핑하여 JSONB 배열로 집계합니다.

        입력: [{pnu: "X", a: 1, b: 2}, {pnu: "X", a: 3, b: 4}]
        출력: [{pnu: "X", <jsonb_column>: [{a: 1, b: 2}, {a: 3, b: 4}]}]
        """
        from collections import defaultdict

        groups: dict[str, list[dict]] = defaultdict(list)
        for rec in records:
            pnu = rec.get("pnu")
            if not pnu:
                continue
            item = {k: v for k, v in rec.items() if k != "pnu"}
            groups[pnu].append(item)

        return [
            {"pnu": pnu, jsonb_column: items}
            for pnu, items in groups.items()
        ]

    @abstractmethod
    async def collect(self, params: dict[str, Any]) -> list[dict]:
        """외부 소스에서 원본 데이터를 수집합니다."""
        ...

    @abstractmethod
    def transform(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """수집된 원본 데이터를 DB 컬럼에 맞게 변환합니다."""
        ...

    @abstractmethod
    def get_params_interactive(self) -> dict[str, Any]:
        """CLI에서 사용자에게 파라미터를 입력받습니다."""
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

        기본 구현은 app.pipeline.loader의 bulk_upsert를 사용합니다.
        소스별로 오버라이드할 수 있습니다.
        """
        from app.database import async_session_maker
        from app.pipeline.loader import bulk_upsert

        async with async_session_maker() as session:
            result = await bulk_upsert(
                session, self.data_type, records,
                simplify_tolerance=self.simplify_tolerance,
            )

        return result


# ── 공공데이터 파일 기반 프로세서 ──

PUBLIC_DATA_DIR = Path(__file__).parent.parent / "public_data"


class BaseFileProcessor(BaseProcessor):
    """파일 기반 공공데이터 프로세서 베이스 클래스.

    public_data/ 디렉토리의 ZIP/CSV/TXT/SHP 파일을 직접 적재하는
    프로세서의 공통 베이스입니다.

    서브클래스에서 정의:
        - data_dir_name: str - public_data 하위 디렉토리명
        - file_pattern: str - ZIP 파일 패턴 (기본 "*.zip")
    """

    data_dir_name: str = ""
    file_pattern: str = "*.zip"

    @property
    def data_dir(self) -> Path:
        return PUBLIC_DATA_DIR / self.data_dir_name

    async def run_batch(
        self,
        sgg_prefixes: list[str] | None = None,
        sido_codes: set[str] | None = None,
        province_names: set[str] | None = None,
        truncate: bool = False,
    ) -> ProcessResult:
        """배치 적재 메서드.

        CLI 공공데이터 적재 플로우에서 호출됩니다.
        기본 구현은 sgg_prefixes를 params에 넣어 run()을 호출합니다.
        """
        params: dict[str, Any] = {}
        if sgg_prefixes:
            params["sgg_prefixes"] = sgg_prefixes
        if sido_codes:
            params["sido_codes"] = sido_codes
        if province_names:
            params["province_names"] = list(province_names)
        if truncate:
            params["truncate"] = truncate

        return await self.run(params)
