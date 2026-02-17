"""vworld CSV 공통 베이스 프로세서.

국가중점데이터(vworld) CSV 파일의 공통 처리 로직을 제공합니다.
CSV 파싱, 컬럼 매핑, 공통 변환 등을 담당합니다.

ZIP 파일 직접 처리 + sgg_prefix 필터링을 지원합니다.
"""

import csv
from pathlib import Path
from typing import Any

from InquirerPy import inquirer
from rich.console import Console

from app.pipeline.file_utils import (
    cleanup_temp_dir,
    extract_zip,
    find_csv_in_dir,
    read_csv_filtered,
)
from app.pipeline.parsing import safe_float, safe_int
from app.pipeline.processors.base import BaseProcessor

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
        """CSV 파일을 읽어 raw dict 리스트를 반환합니다.

        params에 file_path가 있으면 단일 파일 처리,
        zip_files가 있으면 ZIP 내 CSV를 추출하여 처리합니다.
        """
        # ZIP 파일 배치 처리
        zip_files: list[Path] = params.get("zip_files", [])
        sgg_prefixes: list[str] | None = params.get("sgg_prefixes")

        if zip_files:
            return self._collect_from_zips(zip_files, sgg_prefixes)

        # 단일 CSV 파일 처리 (기존 호환)
        file_path_str = params.get("file_path")
        if not file_path_str:
            return []

        file_path = Path(file_path_str)
        if not file_path.exists():
            console.print(f"[red]파일을 찾을 수 없습니다: {file_path}[/]")
            return []

        if file_path.suffix == ".zip":
            return self._collect_from_zips([file_path], sgg_prefixes)

        # CSV 직접 읽기
        if sgg_prefixes:
            rows = read_csv_filtered(file_path, sgg_prefixes)
        else:
            rows = self._read_csv_raw(file_path)

        if not rows:
            console.print("[yellow]파일에서 데이터를 읽을 수 없습니다.[/]")
            return []

        console.print(f"  CSV 읽기 완료: {len(rows)}행")
        return rows

    def _collect_from_zips(
        self, zip_files: list[Path], sgg_prefixes: list[str] | None = None
    ) -> list[dict]:
        """ZIP 파일 목록에서 CSV를 추출하여 읽습니다."""
        all_rows: list[dict] = []
        for zip_path in zip_files:
            console.print(f"  처리 중: {zip_path.name}")
            tmp_dir = extract_zip(zip_path)
            try:
                csv_path = find_csv_in_dir(tmp_dir)
                if not csv_path:
                    console.print("    [yellow]CSV 파일 없음[/]")
                    continue

                if sgg_prefixes:
                    rows = read_csv_filtered(csv_path, sgg_prefixes)
                else:
                    rows = self._read_csv_raw(csv_path)

                all_rows.extend(rows)
                console.print(f"    {len(rows)}건 읽기 완료")
            finally:
                cleanup_temp_dir(tmp_dir)

        console.print(f"  총 CSV 읽기 완료: {len(all_rows)}행")
        return all_rows

    @staticmethod
    def _read_csv_raw(csv_path: Path) -> list[dict]:
        """CSV 파일을 전체 읽습니다."""
        rows: list[dict] = []
        for encoding in ("cp949", "utf-8", "utf-8-sig"):
            try:
                with csv_path.open(encoding=encoding, newline="") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
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
        return mapped

    def get_params_interactive(self) -> dict[str, Any]:
        """CLI에서 파일 경로를 입력받습니다."""
        file_path = inquirer.filepath(
            message=f"{self.description} CSV 또는 ZIP 파일 경로:",
            validate=lambda p: Path(p).exists() and Path(p).suffix in (".csv", ".zip"),
            invalid_message="유효한 CSV 또는 ZIP 파일 경로를 입력하세요.",
        ).execute()

        return {"file_path": file_path}

    _safe_int = staticmethod(safe_int)
    _safe_float = staticmethod(safe_float)

    @staticmethod
    def _extract_pnu(row: dict) -> str | None:
        """고유번호에서 PNU(19자리)를 추출합니다."""
        for key in ("고유번호", "필지고유번호", "pnu"):
            value = row.get(key, "").strip()
            if value and len(value) >= 19:
                return value[:19]
        return None
