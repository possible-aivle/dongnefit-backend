"""실거래가 크롤러 CLI.

사용법:
    # 전체 다운로드 (기본: 최근 1년, 모든 부동산 유형)
    uv --directory backend run python -m app.pipeline.transaction_crawler

    # 기간 지정
    uv --directory backend run python -m app.pipeline.transaction_crawler \
        --start 2025-01-01 --end 2025-12-31

    # 특정 부동산 유형만
    uv --directory backend run python -m app.pipeline.transaction_crawler --types A B

    # 매매만 (전월세 제외)
    uv --directory backend run python -m app.pipeline.transaction_crawler --no-rent

    # 테스트 모드 (아파트 매매 1개월만)
    uv --directory backend run python -m app.pipeline.transaction_crawler --test

부동산 유형 코드:
    A = 아파트
    B = 연립/다세대
    C = 단독/다가구
    D = 오피스텔
    G = 토지
"""

import argparse
import sys
from datetime import date

from app.pipeline.transaction_crawler.crawler import PROPERTY_TYPES, run_crawler


def parse_date(s: str) -> date:
    """YYYY-MM-DD 형식의 날짜를 파싱합니다."""
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"날짜 형식이 올바르지 않습니다: {s} (YYYY-MM-DD)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="국토교통부 실거래가 엑셀 데이터 크롤러",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--start",
        type=parse_date,
        default=None,
        help="시작일 (YYYY-MM-DD, 기본: 1년 전)",
    )
    parser.add_argument(
        "--end",
        type=parse_date,
        default=None,
        help="종료일 (YYYY-MM-DD, 기본: 오늘)",
    )
    parser.add_argument(
        "--types",
        nargs="+",
        choices=list(PROPERTY_TYPES.keys()),
        default=None,
        help="부동산 유형 코드 (A B C D G, 기본: 전체)",
    )
    parser.add_argument(
        "--no-rent",
        action="store_true",
        help="전월세 제외 (매매만 다운로드)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="다운로드 간 대기 시간 (초, 기본: 3)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="테스트 모드 (아파트 매매 최근 1개월만)",
    )

    args = parser.parse_args()

    if args.test:
        today = date.today()
        start = date(today.year, today.month, 1)
        stats = run_crawler(
            start_date=start,
            end_date=today,
            property_types=["A"],
            include_rent=False,
            delay=args.delay,
        )
    else:
        stats = run_crawler(
            start_date=args.start,
            end_date=args.end,
            property_types=args.types,
            include_rent=not args.no_rent,
            delay=args.delay,
        )

    if stats["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
