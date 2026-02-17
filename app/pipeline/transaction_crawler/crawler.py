"""실거래가 엑셀 데이터 크롤러.

국토교통부 실거래가공개시스템에서 월별 엑셀 데이터를 다운로드합니다.
https://rt.molit.go.kr/pt/xls/xls.do?mobileAt=

전국 단위 다운로드 시 계약일자 범위 최대 1개월(31일) 제한이 있어
월별로 분할하여 다운로드합니다.
"""

import time
from datetime import date, timedelta
from pathlib import Path

import httpx
from rich.console import Console

console = Console()

BASE_URL = "https://rt.molit.go.kr"
DOWNLOAD_URL = "/pt/xls/ptXlsExcelDown.do"
DATA_CHECK_URL = "/pt/xls/ptXlsDownDataCheck.do"
MAIN_PAGE_URL = "/pt/xls/xls.do?mobileAt="

OUTPUT_BASE_DIR = Path(__file__).parent.parent / "public_data"
SALE_OUTPUT_DIR = OUTPUT_BASE_DIR / "실거래가_매매"
RENTAL_OUTPUT_DIR = OUTPUT_BASE_DIR / "실거래가_전월세"

# 부동산 유형 코드
PROPERTY_TYPES: dict[str, dict] = {
    "A": {"name": "아파트", "has_rent": True},
    "B": {"name": "연립다세대", "has_rent": True},
    "C": {"name": "단독다가구", "has_rent": True},
    "D": {"name": "오피스텔", "has_rent": True},
    "G": {"name": "토지", "has_rent": False},
}

# 거래 유형 코드
TRANSACTION_TYPES: dict[str, str] = {
    "1": "매매",
    "2": "전월세",
}

# 다운로드 간 대기 시간 (초)
DEFAULT_DELAY = 3.0
# 최대 재시도 횟수
MAX_RETRIES = 3


def scan_existing_files(*dirs: Path) -> set[str]:
    """디렉토리에서 이미 다운로드된 파일명 세트를 반환합니다."""
    existing = set()
    for dir_path in dirs:
        if not dir_path.exists():
            continue
        for f in dir_path.iterdir():
            if f.name.endswith(".xlsx") and f.stat().st_size > 100:
                existing.add(f.name)
    return existing


def get_monthly_ranges(start_date: date, end_date: date) -> list[tuple[date, date]]:
    """날짜 범위를 월별로 분할합니다.

    전국 다운로드는 최대 31일 제한이 있어 1개월 단위로 분할합니다.
    예: 2025-02-16 ~ 2026-02-15 → [(2025-02-16, 2025-02-28), (2025-03-01, 2025-03-31), ...]
    """
    ranges = []
    current = start_date

    while current <= end_date:
        if current.month == 12:
            next_month_start = date(current.year + 1, 1, 1)
        else:
            next_month_start = date(current.year, current.month + 1, 1)

        month_end = next_month_start - timedelta(days=1)
        period_end = min(month_end, end_date)

        ranges.append((current, period_end))
        current = next_month_start

    return ranges


def build_form_data(
    thing_no: str,
    delng_secd: str,
    from_dt: date,
    to_dt: date,
    new_ron_secd: str = "",
) -> dict[str, str]:
    """다운로드 요청 폼 데이터를 생성합니다."""
    return {
        "srhThingNo": thing_no,
        "srhDelngSecd": delng_secd,
        "srhAddrGbn": "1",
        "srhLfstsSecd": "1",
        "srhFromDt": from_dt.strftime("%Y-%m-%d"),
        "srhToDt": to_dt.strftime("%Y-%m-%d"),
        "srhSidoCd": "",
        "srhSggCd": "",
        "srhEmdCd": "",
        "srhHsmpCd": "",
        "srhArea": "",
        "srhLrArea": "",
        "srhFromAmount": "",
        "srhToAmount": "",
        "srhNewRonSecd": new_ron_secd,
        "srhRoadNm": "",
        "srhLoadCd": "",
        "mobileAt": "",
        "sidoNm": "전체",
        "sggNm": "전체",
        "emdNm": "전체",
        "loadNm": "전체",
        "areaNm": "전체",
        "hsmpNm": "전체",
    }


class DailyLimitExceededError(Exception):
    """일일 다운로드 횟수 초과."""


def download_excel(
    client: httpx.Client,
    thing_no: str,
    delng_secd: str,
    from_dt: date,
    to_dt: date,
    output_path: Path,
    new_ron_secd: str = "",
    retries: int = MAX_RETRIES,
) -> str:
    """엑셀 파일을 다운로드합니다.

    Returns:
        "success", "no_data", "failed" 중 하나

    Raises:
        DailyLimitExceededError: 일일 다운로드 100건 제한 초과 시
    """
    form_data = build_form_data(thing_no, delng_secd, from_dt, to_dt, new_ron_secd)

    for attempt in range(1, retries + 1):
        try:
            # 엑셀 다운로드 (데이터 체크 생략하여 다운로드 횟수 절약)
            resp = client.post(DOWNLOAD_URL, data=form_data, timeout=180)

            if resp.status_code != 200:
                console.print(
                    f"    [red]HTTP {resp.status_code}"
                    f"{f' (재시도 {attempt}/{retries})' if attempt < retries else ''}[/]"
                )
                if attempt < retries:
                    time.sleep(5)
                    continue
                return "failed"

            content_type = resp.headers.get("content-type", "")
            content_disp = resp.headers.get("content-disposition", "")

            # 엑셀 파일인지 확인
            is_excel = (
                "application" in content_type
                or "octet-stream" in content_type
                or "spreadsheet" in content_type
                or ".xls" in content_disp
            )

            if not is_excel:
                # JSON 에러 응답인지 확인
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("error", "")
                    if "다운로드 횟수" in error_msg:
                        raise DailyLimitExceededError(error_msg)
                    if error_data.get("cnt") == 0:
                        console.print("    [yellow]데이터 없음[/]")
                        return "no_data"
                    console.print(f"    [red]서버 에러: {error_msg}[/]")
                except DailyLimitExceededError:
                    raise
                except Exception:
                    console.print(
                        f"    [red]예상치 못한 응답 (content-type: {content_type})[/]"
                    )

                if attempt < retries:
                    client.get(MAIN_PAGE_URL)
                    time.sleep(3)
                    continue
                return "failed"

            if len(resp.content) < 100:
                console.print(f"    [yellow]파일 크기가 너무 작음 ({len(resp.content)} bytes)[/]")
                return "no_data"

            # 파일 저장
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(resp.content)

            size_kb = len(resp.content) / 1024
            if size_kb > 1024:
                size_str = f"{size_kb / 1024:.1f} MB"
            else:
                size_str = f"{size_kb:.0f} KB"
            console.print(f"    [green]저장 완료 ({size_str})[/]")
            return "success"

        except DailyLimitExceededError:
            raise
        except httpx.TimeoutException:
            console.print(
                f"    [red]타임아웃"
                f"{f' (재시도 {attempt}/{retries})' if attempt < retries else ''}[/]"
            )
            if attempt < retries:
                time.sleep(10)
                continue
            return "failed"
        except Exception as e:
            console.print(
                f"    [red]{type(e).__name__}: {e}"
                f"{f' (재시도 {attempt}/{retries})' if attempt < retries else ''}[/]"
            )
            if attempt < retries:
                time.sleep(5)
                continue
            return "failed"

    return "failed"


def run_crawler(
    start_date: date | None = None,
    end_date: date | None = None,
    property_types: list[str] | None = None,
    include_rent: bool = True,
    delay: float = DEFAULT_DELAY,
    output_dir: Path | None = None,
) -> dict[str, int]:
    """크롤러를 실행합니다.

    Args:
        start_date: 시작일 (기본: 1년 전)
        end_date: 종료일 (기본: 오늘)
        property_types: 대상 부동산 유형 코드 목록 (기본: 전체)
        include_rent: 전월세 포함 여부 (기본: True)
        delay: 다운로드 간 대기 시간 (초)
        output_dir: 출력 디렉토리 (기본: app/pipeline/public_data/실거래가/)

    Returns:
        {"success": n, "no_data": n, "failed": n} 통계
    """
    today = date.today()
    if end_date is None:
        end_date = today
    if start_date is None:
        start_date = date(end_date.year - 1, end_date.month, end_date.day) + timedelta(days=1)

    if property_types is None:
        property_types = list(PROPERTY_TYPES.keys())

    dest_dir = output_dir  # output_dir이 지정되면 그대로 사용 (하위 분기 무시)

    monthly_ranges = get_monthly_ranges(start_date, end_date)

    # 이미 다운로드된 파일 스캔
    if dest_dir:
        existing_files = scan_existing_files(dest_dir)
    else:
        existing_files = scan_existing_files(SALE_OUTPUT_DIR, RENTAL_OUTPUT_DIR)

    # 총 다운로드 수 계산 (기존 파일 제외)
    total_all = 0
    total = 0
    download_plan: list[tuple[str, str, str]] = []  # (pt_code, tx_code, new_ron_secd)
    for pt_code in property_types:
        pt_config = PROPERTY_TYPES[pt_code]
        pt_name = pt_config["name"]
        # 매매
        download_plan.append((pt_code, "1", ""))
        for from_dt, _ in monthly_ranges:
            total_all += 1
            month_str = from_dt.strftime("%Y%m")
            if f"{pt_name}_매매_{month_str}.xlsx" not in existing_files:
                total += 1
        # 전월세 (신규만)
        if include_rent and pt_config["has_rent"]:
            download_plan.append((pt_code, "2", "1"))
            for from_dt, _ in monthly_ranges:
                total_all += 1
                month_str = from_dt.strftime("%Y%m")
                if f"{pt_name}_전월세_{month_str}.xlsx" not in existing_files:
                    total += 1

    console.print()
    console.print("[bold]━━━ 실거래가 크롤러 ━━━[/]")
    console.print(f"  기간: {start_date} ~ {end_date}")
    console.print(f"  월별 분할: {len(monthly_ranges)}개월")
    console.print(
        f"  대상: {', '.join(PROPERTY_TYPES[c]['name'] for c in property_types)}"
    )
    console.print(f"  전월세 포함: {'예 (신규만)' if include_rent else '아니오'}")
    skipped_count = total_all - total
    if skipped_count > 0:
        console.print(f"  신규 다운로드: {total}건 (기존 {skipped_count}건 스킵)")
    else:
        console.print(f"  총 다운로드: {total}건")
    if dest_dir:
        console.print(f"  출력 경로: {dest_dir}")
    else:
        console.print(f"  출력 경로: {SALE_OUTPUT_DIR} (매매)")
        console.print(f"             {RENTAL_OUTPUT_DIR} (전월세)")
    console.print()

    if total == 0:
        console.print("\n[green]모든 파일이 이미 다운로드되어 있습니다.[/]\n")
        return {"success": skipped_count, "no_data": 0, "failed": 0}

    stats: dict[str, int] = {"success": 0, "no_data": 0, "failed": 0}

    with httpx.Client(
        base_url=BASE_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Referer": f"{BASE_URL}{MAIN_PAGE_URL}",
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        },
        follow_redirects=True,
        timeout=120,
    ) as client:
        # 세션 초기화
        console.print("[dim]세션 초기화 중...[/]")
        init_resp = client.get(MAIN_PAGE_URL)
        if init_resp.status_code != 200:
            console.print(f"[red]세션 초기화 실패 (HTTP {init_resp.status_code})[/]")
            return stats
        console.print("[dim]세션 초기화 완료[/]\n")

        count = 0
        daily_limit_hit = False
        for pt_code, tx_code, new_ron_secd in download_plan:
            if daily_limit_hit:
                break

            pt_name = PROPERTY_TYPES[pt_code]["name"]
            tx_name = TRANSACTION_TYPES[tx_code]

            console.print(f"[bold cyan]▶ {pt_name} - {tx_name}[/]")

            for from_dt, to_dt in monthly_ranges:
                month_str = from_dt.strftime("%Y%m")

                filename = f"{pt_name}_{tx_name}_{month_str}.xlsx"
                if dest_dir:
                    file_dir = dest_dir
                elif tx_code == "1":
                    file_dir = SALE_OUTPUT_DIR
                else:
                    file_dir = RENTAL_OUTPUT_DIR
                output_path = file_dir / filename

                # 이미 다운로드된 파일 스킵
                if filename in existing_files:
                    continue

                count += 1
                console.print(
                    f"  [{count}/{total}] {filename} ({from_dt} ~ {to_dt})"
                )

                try:
                    result = download_excel(
                        client,
                        pt_code,
                        tx_code,
                        from_dt,
                        to_dt,
                        output_path,
                        new_ron_secd,
                    )
                    stats[result] += 1
                except DailyLimitExceededError:
                    remaining = total - count
                    console.print(
                        f"\n  [red bold]일일 다운로드 100건 제한 초과![/]"
                        f"\n  [yellow]나머지 {remaining}건은 다음에 다시 실행하세요."
                        f"\n  이미 다운로드된 파일은 자동 스킵됩니다.[/]\n"
                    )
                    daily_limit_hit = True
                    break

                # 다운로드 간 대기
                if count < total:
                    time.sleep(delay)

            console.print()

    console.print("[bold]━━━ 크롤링 완료 ━━━[/]")
    console.print(f"  성공: [green]{stats['success']}[/]건")
    console.print(f"  데이터없음: [yellow]{stats['no_data']}[/]건")
    console.print(f"  실패: [red]{stats['failed']}[/]건")
    if daily_limit_hit:
        console.print(
            "  [yellow]일일 제한 도달 — 재실행 시 기존 파일은 자동 스킵됩니다.[/]"
        )

    return stats
