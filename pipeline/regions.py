"""지역 매핑 모듈.

행정경계 SHP에서 시도/시군구 목록을 동적으로 구축합니다.
CLI에서 지역 선택 시 사용됩니다.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from pathlib import Path

PUBLIC_DATA_DIR = Path(__file__).parent / "public_data"

# 시도 코드 → 시도명 매핑
SIDO_CODE_MAP: dict[str, str] = {
    "11": "서울특별시",
    "26": "부산광역시",
    "27": "대구광역시",
    "28": "인천광역시",
    "29": "광주광역시",
    "30": "대전광역시",
    "31": "세종특별자치시",
    "36": "세종특별자치시",  # 일부 데이터에서 36 사용
    "41": "경기도",
    "42": "강원특별자치도",
    "43": "충청북도",
    "44": "충청남도",
    "46": "전라남도",
    "47": "경상북도",
    "48": "경상남도",
    "50": "제주특별자치도",
    "51": "충청북도",  # 일부 데이터
    "52": "충청남도",  # 일부 데이터
}

# 시도명 → 시도코드 역매핑 (정식 매핑만)
SIDO_NAME_MAP: dict[str, str] = {
    "서울특별시": "11",
    "서울": "11",
    "부산광역시": "26",
    "부산": "26",
    "대구광역시": "27",
    "대구": "27",
    "인천광역시": "28",
    "인천": "28",
    "광주광역시": "29",
    "광주": "29",
    "대전광역시": "30",
    "대전": "30",
    "울산광역시": "31",
    "울산": "31",
    "세종특별자치시": "36",
    "세종시": "36",
    "세종": "36",
    "경기도": "41",
    "경기": "41",
    "강원특별자치도": "42",
    "강원도": "42",
    "강원": "42",
    "충청북도": "43",
    "충북": "43",
    "충청남도": "44",
    "충남": "44",
    "전북특별자치도": "45",
    "전라북도": "45",
    "전북": "45",
    "전라남도": "46",
    "전남": "46",
    "경상북도": "47",
    "경북": "47",
    "경상남도": "48",
    "경남": "48",
    "제주특별자치도": "50",
    "제주": "50",
}

# 특별시/광역시/특별자치시 코드 (단일 시 단위로 취급)
METRO_CODES = {"11", "26", "27", "28", "29", "30", "31", "36"}

# 연속지적도/도로중심선 파일명에서 사용하는 시도 약칭 → 시도코드
PROVINCE_FILE_NAME_MAP: dict[str, str] = {
    "서울": "11",
    "부산": "26",
    "대구": "27",
    "인천": "28",
    "광주": "29",
    "대전": "30",
    "울산": "31",
    "세종": "36",
    "세종시": "36",
    "경기": "41",
    "강원특별자치도": "42",
    "충북": "43",
    "충남": "44",
    "전북특별자치도": "45",
    "전남": "46",
    "경북": "47",
    "경남": "48",
    "제주": "50",
}


@dataclass
class Region:
    """지역 정보."""

    name: str  # "서울특별시" or "수원시"
    sido_code: str  # "11" or "41"
    sgg_prefixes: list[str] = field(default_factory=list)  # ["11"] or ["41111","41113",...]
    parent: str | None = None  # None or "경기도"
    is_metro: bool = False  # 특별시/광역시 여부


@functools.lru_cache(maxsize=1)
def load_regions() -> list[Region]:
    """행정경계 SHP에서 지역 목록을 로드합니다.

    SHP 파일이 없으면 하드코딩된 기본 목록을 반환합니다.
    """
    try:
        return _load_regions_from_shp()
    except Exception:
        return _get_default_regions()


def _load_regions_from_shp() -> list[Region]:
    """행정경계 SHP에서 시도/시군구를 읽어 Region 목록을 생성합니다."""
    import fiona

    regions: list[Region] = []

    # 시도 SHP
    sido_dir = PUBLIC_DATA_DIR / "행정경계_시도"
    sido_shp = _find_shp_in_zip_dir(sido_dir)
    if not sido_shp:
        return _get_default_regions()

    sido_names: dict[str, str] = {}  # code -> name
    with fiona.open(sido_shp) as src:
        for feat in src:
            props = feat.get("properties", {})
            bjcd = str(props.get("BJCD", props.get("ADM_CD", props.get("CTPRVN_CD", ""))))
            name = str(props.get("NAME", props.get("CTP_KOR_NM", props.get("CTPRVN_NM", ""))))
            if bjcd and name:
                code = bjcd[:2]
                sido_names[code] = name

    # 시군구 SHP
    sgg_dir = PUBLIC_DATA_DIR / "행정경계_시군구"
    sgg_shp = _find_shp_in_zip_dir(sgg_dir)

    sgg_by_sido: dict[str, list[tuple[str, str]]] = {}  # sido_code -> [(sgg_code, sgg_name)]
    if sgg_shp:
        with fiona.open(sgg_shp) as src:
            for feat in src:
                props = feat.get("properties", {})
                bjcd = str(
                    props.get("BJCD", props.get("ADM_CD", props.get("SIG_CD", "")))
                )
                name = str(
                    props.get("NAME", props.get("SIG_KOR_NM", props.get("SIGUNGU_NM", "")))
                )
                if bjcd and name and len(bjcd) >= 5:
                    sido_code = bjcd[:2]
                    sgg_code = bjcd[:5]
                    sgg_by_sido.setdefault(sido_code, []).append((sgg_code, name))

    # 특별시/광역시 → 시 단위 Region
    for code in sorted(sido_names):
        name = sido_names[code]
        is_metro = code in METRO_CODES

        if is_metro:
            regions.append(Region(
                name=name,
                sido_code=code,
                sgg_prefixes=[code],
                parent=None,
                is_metro=True,
            ))
        else:
            # 도 내 시/군 → 개별 Region
            sgus = sgg_by_sido.get(code, [])
            if sgus:
                # 시 단위로 그룹핑 (같은 시 이름의 구가 여러 개 있을 수 있음)
                city_groups: dict[str, list[str]] = {}
                for sgg_code, sgg_name in sgus:
                    # "수원시 장안구" → "수원시"
                    base_name = sgg_name.split()[0] if " " in sgg_name else sgg_name
                    city_groups.setdefault(base_name, []).append(sgg_code)

                for city_name, sgg_codes in sorted(city_groups.items()):
                    regions.append(Region(
                        name=city_name,
                        sido_code=code,
                        sgg_prefixes=sorted(sgg_codes),
                        parent=name,
                        is_metro=False,
                    ))
            else:
                # 시군구 SHP 없으면 시도 단위
                regions.append(Region(
                    name=name,
                    sido_code=code,
                    sgg_prefixes=[code],
                    parent=None,
                    is_metro=False,
                ))

    return regions if regions else _get_default_regions()


def _find_shp_in_zip_dir(dir_path: Path) -> Path | None:
    """디렉토리에서 ZIP 안의 SHP 파일을 찾습니다."""
    import tempfile
    import zipfile

    for zip_path in dir_path.glob("*.zip"):
        tmp_dir = Path(tempfile.mkdtemp(prefix="shp_"))
        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(tmp_dir)
            for shp in tmp_dir.rglob("*.shp"):
                return shp
        except Exception:
            continue
    return None


def _get_default_regions() -> list[Region]:
    """SHP 없을 때 기본 지역 목록."""
    regions = [
        Region("서울특별시", "11", ["11"], is_metro=True),
        Region("부산광역시", "26", ["26"], is_metro=True),
        Region("대구광역시", "27", ["27"], is_metro=True),
        Region("인천광역시", "28", ["28"], is_metro=True),
        Region("광주광역시", "29", ["29"], is_metro=True),
        Region("대전광역시", "30", ["30"], is_metro=True),
        Region("울산광역시", "31", ["31"], is_metro=True),
        Region("세종특별자치시", "36", ["36"], is_metro=True),
        Region("경기도", "41", ["41"], parent=None),
        Region("강원특별자치도", "42", ["42"], parent=None),
        Region("충청북도", "43", ["43"], parent=None),
        Region("충청남도", "44", ["44"], parent=None),
        Region("전북특별자치도", "45", ["45"], parent=None),
        Region("전라남도", "46", ["46"], parent=None),
        Region("경상북도", "47", ["47"], parent=None),
        Region("경상남도", "48", ["48"], parent=None),
        Region("제주특별자치도", "50", ["50"], parent=None),
    ]
    return regions


def get_sido_codes_for_regions(regions: list[Region]) -> set[str]:
    """선택된 Region 목록에서 시도코드 set을 반환합니다."""
    return {r.sido_code for r in regions}


def get_sgg_prefixes_for_regions(regions: list[Region]) -> list[str]:
    """선택된 Region 목록에서 시군구 prefix 목록을 반환합니다."""
    prefixes: list[str] = []
    for r in regions:
        prefixes.extend(r.sgg_prefixes)
    return sorted(set(prefixes))


def get_province_file_names_for_regions(regions: list[Region]) -> set[str]:
    """Region 목록에서 파일명에 사용되는 시도 약칭을 반환합니다.

    연속지적도/도로중심선처럼 시도 이름이 파일명에 포함된 경우 사용.
    """
    # 시도코드 → 파일명에서 사용하는 약칭 역매핑
    code_to_file_names: dict[str, set[str]] = {}
    for fname, code in PROVINCE_FILE_NAME_MAP.items():
        code_to_file_names.setdefault(code, set()).add(fname)

    result: set[str] = set()
    for r in regions:
        if r.sido_code in code_to_file_names:
            result.update(code_to_file_names[r.sido_code])
    return result
