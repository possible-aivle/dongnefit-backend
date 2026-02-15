"""vworld CSV 공통 베이스 프로세서.

국가중점데이터(vworld) CSV 파일의 공통 처리 로직을 제공합니다.
CSV 파싱, 컬럼 매핑, 공통 변환 등을 담당합니다.
"""

import csv
from pathlib import Path
from typing import Any

from InquirerPy import inquirer
from rich.console import Console

from pipeline.processors.base import BaseProcessor

console = Console()


class VworldCsvProcessor(BaseProcessor):
    """vworld CSV 파일 기반 프로세서 베이스 클래스.

    서브클래스에서 다음을 정의해야 합니다:
        - name: str - 프로세서 이름
        - description: str - 설명
        - data_type: PublicDataType - 데이터 타입
        - COLUMN_MAP: dict[str, str] - 한글 CSV 컬럼명 → DB 컬럼명 매핑

    선택적으로 오버라이드할 수 있는 메서드:
        - transform_row(row: dict) -> dict | None - 행별 추가 변환
    """

    COLUMN_MAP: dict[str, str] = {}

    async def collect(self, params: dict[str, Any]) -> list[dict]:
        """CSV 파일을 읽어 raw dict 리스트를 반환합니다."""
        file_path = Path(params["file_path"])
        if not file_path.exists():
            console.print(f"[red]파일을 찾을 수 없습니다: {file_path}[/]")
            return []

        rows: list[dict] = []
        # cp949 먼저 시도, 실패하면 utf-8
        for encoding in ("cp949", "utf-8", "utf-8-sig"):
            try:
                with file_path.open(encoding=encoding, newline="") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if not rows:
            console.print("[yellow]파일에서 데이터를 읽을 수 없습니다.[/]")
            return []

        console.print(f"  CSV 읽기 완료: {len(rows)}행")
        return rows

    def transform(self, raw_data: list[dict]) -> list[dict[str, Any]]:
        """CSV raw 데이터를 DB 컬럼에 맞게 변환합니다."""
        records: list[dict[str, Any]] = []

        for row in raw_data:
            mapped = self._map_columns(row)
            if mapped is None:
                continue

            # 서브클래스의 추가 변환
            transformed = self.transform_row(mapped, row)
            if transformed is not None:
                records.append(transformed)

        console.print(f"  변환 완료: {len(records)}건")
        return records

    def _map_columns(self, row: dict) -> dict[str, Any] | None:
        """한글 CSV 컬럼을 DB 컬럼으로 매핑합니다."""
        mapped: dict[str, Any] = {}

        for csv_col, db_col in self.COLUMN_MAP.items():
            value = row.get(csv_col, "").strip()
            mapped[db_col] = value if value else None

        return mapped

    def transform_row(self, mapped: dict[str, Any], raw_row: dict) -> dict[str, Any] | None:
        """행별 추가 변환 (서브클래스에서 오버라이드).

        Args:
            mapped: COLUMN_MAP 적용된 딕셔너리
            raw_row: 원본 CSV 행

        Returns:
            변환된 딕셔너리 또는 스킵할 경우 None
        """
        # raw_data 보존
        mapped["raw_data"] = raw_row
        return mapped

    def get_params_interactive(self) -> dict[str, Any]:
        """CLI에서 파일 경로를 입력받습니다."""
        file_path = inquirer.filepath(
            message=f"{self.description} CSV 파일 경로:",
            validate=lambda p: Path(p).exists() and Path(p).suffix == ".csv",
            invalid_message="유효한 CSV 파일 경로를 입력하세요.",
        ).execute()

        return {"file_path": file_path}

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        """안전한 int 변환."""
        if value is None or value == "":
            return None
        try:
            return int(float(str(value).replace(",", "")))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        """안전한 float 변환."""
        if value is None or value == "":
            return None
        try:
            return float(str(value).replace(",", ""))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _extract_pnu(row: dict) -> str | None:
        """고유번호에서 PNU(19자리)를 추출합니다."""
        for key in ("고유번호", "필지고유번호", "pnu"):
            value = row.get(key, "").strip()
            if value and len(value) >= 19:
                return value[:19]
        return None
