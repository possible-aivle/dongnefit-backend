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
    "31": "울산광역시",
    "36": "세종특별자치시",
    "41": "경기도",
    "42": "강원특별자치도",
    "43": "충청북도",
    "44": "충청남도",
    "45": "전북특별자치도",
    "46": "전라남도",
    "47": "경상북도",
    "48": "경상남도",
    "50": "제주특별자치도",
    "51": "강원특별자치도",  # 일부 데이터에서 사용하는 신코드
    "52": "전북특별자치도",  # 일부 데이터에서 사용하는 신코드
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
    import shutil

    import fiona

    regions: list[Region] = []
    tmp_dirs: list[Path] = []

    try:
        # 시도 SHP
        sido_dir = PUBLIC_DATA_DIR / "행정경계_시도"
        sido_shp, sido_tmp = _find_shp_in_zip_dir(sido_dir)
        if sido_tmp:
            tmp_dirs.append(sido_tmp)
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
        sgg_shp, sgg_tmp = _find_shp_in_zip_dir(sgg_dir)
        if sgg_tmp:
            tmp_dirs.append(sgg_tmp)

        sgg_by_sido: dict[str, list[tuple[str, str]]] = {}
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
    finally:
        for tmp_dir in tmp_dirs:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def _find_shp_in_zip_dir(dir_path: Path) -> tuple[Path | None, Path | None]:
    """디렉토리에서 ZIP 안의 SHP 파일을 찾습니다.

    Returns:
        (shp_path, tmp_dir) 튜플. 사용 후 tmp_dir을 정리해야 합니다.
    """
    import tempfile
    import zipfile

    for zip_path in dir_path.glob("*.zip"):
        tmp_dir = Path(tempfile.mkdtemp(prefix="shp_"))
        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(tmp_dir)
            for shp in tmp_dir.rglob("*.shp"):
                return shp, tmp_dir
        except Exception:
            import shutil

            shutil.rmtree(tmp_dir, ignore_errors=True)
            continue
    return None, None


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


@functools.lru_cache(maxsize=1)
def build_sigungu_to_sgg_map() -> dict[str, str]:
    """엑셀 '시군구' 텍스트 prefix → 5자리 시군구코드 매핑을 생성합니다.

    행정경계 SHP에서 시도/시군구 정보를 읽어 매핑을 구축합니다.
    키 예시: "서울특별시 종로구" → "11010"
             "경기도 수원시 장안구" → "41135"

    SHP 파일이 없으면 빈 dict를 반환합니다.
    """
    try:
        return _build_sigungu_map_from_shp()
    except Exception:
        return {}


def _build_sigungu_map_from_shp() -> dict[str, str]:
    """SHP 파일에서 시군구 텍스트 → 코드 매핑을 구축합니다.

    SHP에서 시군구는 "종로구"(11110), "성남시"(41130), "분당구"(41135) 등으로 분리되어 있지만,
    실거래가 엑셀에서는 "서울특별시 종로구 ...", "경기도 성남시 분당구 ..." 형태입니다.
    따라서 "시도 시 구" 형태의 compound 키도 생성합니다.
    """
    import shutil

    import fiona

    result: dict[str, str] = {}
    tmp_dirs: list[Path] = []

    try:
        # 시도 SHP → {sido_code: sido_name}
        sido_dir = PUBLIC_DATA_DIR / "행정경계_시도"
        sido_shp, sido_tmp = _find_shp_in_zip_dir(sido_dir)
        if sido_tmp:
            tmp_dirs.append(sido_tmp)
        if not sido_shp:
            return {}

        sido_names: dict[str, str] = {}
        with fiona.open(sido_shp) as src:
            for feat in src:
                props = feat.get("properties", {})
                bjcd = str(props.get("BJCD", props.get("ADM_CD", props.get("CTPRVN_CD", ""))))
                name = str(props.get("NAME", props.get("CTP_KOR_NM", props.get("CTPRVN_NM", ""))))
                if bjcd and name:
                    code = bjcd[:2]
                    sido_names[code] = name

        # 시군구 SHP → sgg_code: sgg_name (sido별 그룹핑)
        sgg_dir = PUBLIC_DATA_DIR / "행정경계_시군구"
        sgg_shp, sgg_tmp = _find_shp_in_zip_dir(sgg_dir)
        if sgg_tmp:
            tmp_dirs.append(sgg_tmp)
        if not sgg_shp:
            return {}

        # 1단계: SHP에서 모든 시군구 엔트리 수집
        sgg_entries: dict[str, str] = {}  # sgg_code → sgg_name
        sgg_by_sido: dict[str, list[tuple[str, str]]] = {}

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
                    sgg_entries[sgg_code] = name
                    sgg_by_sido.setdefault(sido_code, []).append((sgg_code, name))

        # 2단계: 매핑 구축
        for sido_code, entries in sgg_by_sido.items():
            sido_name = sido_names.get(sido_code, "")
            if not sido_name:
                continue

            # 시 → 구 관계 파악: 코드 앞 4자리가 같으면 같은 시 소속
            # 예: 성남시(41130), 수정구(41131), 중원구(41133), 분당구(41135)
            # 5번째 자리가 0인 것이 시 레벨, 나머지가 구 레벨
            parent_cities: dict[str, str] = {}  # code_prefix(4자리) → city_name
            child_gus: list[tuple[str, str, str]] = []  # (sgg_code, gu_name, code_prefix)

            for sgg_code, sgg_name in entries:
                code_prefix = sgg_code[:4]
                if sgg_code[4] == "0" and sgg_name.endswith("시"):
                    # 시 레벨 엔트리 (예: 성남시 41130)
                    parent_cities[code_prefix] = sgg_name
                elif sgg_name.endswith("구") and code_prefix in parent_cities or sgg_code[4] != "0":
                    # 구 레벨일 수 있음 — 나중에 parent 체크
                    child_gus.append((sgg_code, sgg_name, code_prefix))

            # 모든 엔트리에 대해 기본 매핑 추가: "시도 시군구명" → code
            for sgg_code, sgg_name in entries:
                full_key = f"{sido_name} {sgg_name}"
                result[full_key] = sgg_code

            # 구가 시 하위에 있는 경우 compound 키 추가: "시도 시이름 구이름" → 구code
            for sgg_code, gu_name, code_prefix in child_gus:
                city_name = parent_cities.get(code_prefix)
                if city_name and gu_name.endswith("구"):
                    compound_key = f"{sido_name} {city_name} {gu_name}"
                    result[compound_key] = sgg_code

        return result
    finally:
        for tmp_dir in tmp_dirs:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def extract_sgg_code(sigungu_text: str, sigungu_map: dict[str, str] | None = None) -> str | None:
    """엑셀 '시군구' 텍스트에서 5자리 시군구코드를 추출합니다.

    longest-prefix 매칭을 사용하여 가장 구체적인 시군구코드를 반환합니다.

    Args:
        sigungu_text: 엑셀 시군구 컬럼 값 (예: "서울특별시 종로구 숭인동")
        sigungu_map: 시군구 텍스트→코드 매핑. None이면 자동 로드.

    Returns:
        5자리 시군구코드 (예: "11110") 또는 None
    """
    if not sigungu_text:
        return None

    if sigungu_map is None:
        sigungu_map = build_sigungu_to_sgg_map()

    if not sigungu_map:
        return None

    # longest-prefix 매칭: 가장 긴 매칭 키를 우선 사용
    best_code: str | None = None
    best_len = 0

    for prefix, code in sigungu_map.items():
        if sigungu_text.startswith(prefix) and len(prefix) > best_len:
            best_code = code
            best_len = len(prefix)

    return best_code


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
