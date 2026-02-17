"""파일 유틸리티 모듈.

ZIP 추출, SHP/CSV/TXT 읽기, 필터링 등 공통 유틸리티.
"""

from __future__ import annotations

import csv
import tempfile
import unicodedata
import zipfile
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()

# WGS84 (EPSG:4326) - 네이버지도, 카카오맵, Google Maps 공통 좌표계
TARGET_CRS = "EPSG:4326"


def _make_crs_transformer(
    src_crs: Any,
) -> tuple[Any, bool]:
    """SHP 원본 CRS를 확인하고 WGS84 변환 함수를 생성합니다.

    Args:
        src_crs: fiona에서 읽은 source CRS (dict 또는 CRS 객체)

    Returns:
        (transformer, needs_transform) 튜플.
        needs_transform=False이면 이미 WGS84이므로 변환 불필요.
    """
    from pyproj import CRS, Transformer

    try:
        source = CRS(src_crs)
    except Exception:
        # CRS 파싱 실패 시 변환 없이 통과
        console.print("[yellow]  CRS 파싱 실패 → 좌표 변환 없이 진행[/]")
        return None, False

    target = CRS(TARGET_CRS)

    if source.equals(target):
        return None, False

    console.print(f"  [cyan]CRS 변환: {source.to_epsg() or source.name} → EPSG:4326[/]")
    transformer = Transformer.from_crs(source, target, always_xy=True)
    return transformer, True


def _transform_geojson(geojson: dict[str, Any], transformer: Any) -> dict[str, Any]:
    """GeoJSON geometry의 좌표를 변환합니다.

    Args:
        geojson: GeoJSON geometry dict (fiona feature["geometry"])
        transformer: pyproj Transformer

    Returns:
        좌표가 변환된 새 GeoJSON dict
    """
    from shapely.geometry import mapping, shape
    from shapely.ops import transform

    geom = shape(geojson)
    transformed = transform(transformer.transform, geom)
    return dict(mapping(transformed))


def geojson_to_wkt(geojson: dict[str, Any] | None) -> str | None:
    """GeoJSON dict를 WKT 문자열로 변환합니다.

    Args:
        geojson: fiona에서 읽은 GeoJSON geometry dict

    Returns:
        WKT 문자열 또는 None
    """
    if geojson is None:
        return None
    from shapely.geometry import shape as shapely_shape

    return shapely_shape(geojson).wkt


def extract_zip(zip_path: Path) -> Path:
    """ZIP 파일을 임시 디렉토리에 추출합니다.

    Returns:
        추출된 디렉토리 경로
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="pipeline_"))
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(tmp_dir)
    return tmp_dir


def find_shp_in_dir(dir_path: Path) -> Path | None:
    """디렉토리에서 첫 번째 .shp 파일을 찾습니다."""
    for shp in dir_path.rglob("*.shp"):
        return shp
    return None


def find_csv_in_dir(dir_path: Path) -> Path | None:
    """디렉토리에서 첫 번째 .csv 파일을 찾습니다."""
    for csv_file in dir_path.rglob("*.csv"):
        return csv_file
    return None


def read_shp_features(
    shp_path: Path,
    sgg_prefixes: list[str] | None = None,
    code_field: str = "PNU",
    encoding: str | None = None,
) -> list[dict[str, Any]]:
    """SHP 파일을 읽어 feature dict 리스트를 반환합니다.

    Args:
        shp_path: SHP 파일 경로
        sgg_prefixes: 필터링할 시군구 prefix 목록 (None이면 전체)
        code_field: 필터링에 사용할 속성 필드명
        encoding: DBF 파일 인코딩 (.cpg 없을 때 명시, 예: "cp949")

    Returns:
        [{properties..., __geometry__: geojson_dict}, ...]
    """
    import fiona

    rows: list[dict[str, Any]] = []
    open_kwargs: dict[str, Any] = {}
    if encoding:
        open_kwargs["encoding"] = encoding
    with fiona.open(shp_path, **open_kwargs) as src:
        # CRS 자동 감지 및 WGS84 변환 준비
        transformer, needs_transform = _make_crs_transformer(src.crs)

        for feature in src:
            props: dict[str, Any] = dict(feature.get("properties", {}))

            # 필터링
            if sgg_prefixes:
                code_val = str(props.get(code_field, ""))
                if not any(code_val.startswith(p) for p in sgg_prefixes):
                    continue

            geom = feature.get("geometry")
            if geom:
                geom_dict = dict(geom)
                if needs_transform and transformer is not None:
                    geom_dict = _transform_geojson(geom_dict, transformer)
                props["__geometry__"] = geom_dict

            rows.append(props)

    return rows


def read_csv_filtered(
    csv_path: Path,
    sgg_prefixes: list[str] | None = None,
    pnu_field: str = "고유번호",
) -> list[dict]:
    """CSV 파일을 읽으면서 PNU prefix로 필터링합니다.

    Args:
        csv_path: CSV 파일 경로
        sgg_prefixes: 필터링할 시군구 prefix 목록 (None이면 전체)
        pnu_field: PNU가 포함된 컬럼명

    Returns:
        매칭된 행의 dict 리스트
    """
    rows: list[dict] = []

    for encoding in ("cp949", "utf-8", "utf-8-sig"):
        try:
            with csv_path.open(encoding=encoding, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if sgg_prefixes:
                        pnu_val = row.get(pnu_field, "").strip()
                        if not any(pnu_val.startswith(p) for p in sgg_prefixes):
                            continue
                    rows.append(row)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    return rows


def read_txt_filtered(
    txt_path: Path,
    sgg_prefixes: list[str] | None = None,
    sgg_field_index: int = 0,
    delimiter: str = "|",
) -> list[list[str]]:
    """TXT 파일을 읽으면서 시군구 코드로 필터링합니다.

    Args:
        txt_path: TXT 파일 경로
        sgg_prefixes: 필터링할 시군구 prefix 목록 (None이면 전체)
        sgg_field_index: 시군구 코드가 포함된 필드 인덱스
        delimiter: 구분자

    Returns:
        매칭된 행의 필드 리스트
    """
    rows: list[list[str]] = []

    for encoding in ("cp949", "utf-8", "utf-8-sig"):
        try:
            with txt_path.open(encoding=encoding) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    fields = line.split(delimiter)
                    if sgg_prefixes and sgg_field_index < len(fields):
                        code_val = fields[sgg_field_index].strip()
                        if not any(code_val.startswith(p) for p in sgg_prefixes):
                            continue
                    rows.append(fields)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    return rows


def find_zip_files_by_sido_code(
    data_dir: Path,
    sido_codes: set[str],
    pattern: str = "*.zip",
) -> list[Path]:
    """시도코드에 맞는 ZIP 파일을 찾습니다.

    파일명에 시도코드가 포함된 경우 (예: AL_D003_11_20260212.zip).
    """
    matched: list[Path] = []
    for zip_path in sorted(data_dir.glob(pattern)):
        # 파일명에서 시도코드 추출 시도
        parts = zip_path.stem.split("_")
        for part in parts:
            if part in sido_codes:
                matched.append(zip_path)
                break
    return matched


def _nfc(s: str) -> str:
    """Unicode NFC 정규화.

    macOS(APFS/HFS+)는 파일명에 NFD를 사용하므로
    Python 문자열(NFC)과 비교 시 정규화가 필요합니다.
    """
    return unicodedata.normalize("NFC", s)


def find_zip_files_by_province_name(
    data_dir: Path,
    province_names: set[str],
    pattern: str = "*.zip",
) -> list[Path]:
    """시도 약칭이 파일명에 포함된 ZIP 파일을 찾습니다.

    파일명에 시도 이름이 포함된 경우 (예: LSMD_CONT_LDREG_서울.zip).
    """
    matched: list[Path] = []
    for zip_path in sorted(data_dir.glob(pattern)):
        name = _nfc(zip_path.stem)
        for pname in province_names:
            if _nfc(pname) in name:
                matched.append(zip_path)
                break
    return matched


def find_zip_files_by_sgg_code(
    data_dir: Path,
    sgg_prefixes: list[str],
    pattern: str = "*.zip",
) -> list[Path]:
    """시군구코드(5자리)에 맞는 ZIP 파일을 찾습니다.

    파일명에 시군구코드가 포함된 경우 (예: AL_D194_11110_20250814.zip).
    """
    matched: list[Path] = []
    for zip_path in sorted(data_dir.glob(pattern)):
        parts = zip_path.stem.split("_")
        for part in parts:
            if len(part) == 5 and any(part.startswith(p) for p in sgg_prefixes):
                matched.append(zip_path)
                break
    return matched


def cleanup_temp_dir(dir_path: Path) -> None:
    """임시 디렉토리를 정리합니다."""
    import shutil

    try:
        if dir_path.exists() and str(dir_path).startswith(tempfile.gettempdir()):
            shutil.rmtree(dir_path)
    except Exception:
        pass
