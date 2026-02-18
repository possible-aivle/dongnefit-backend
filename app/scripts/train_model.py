"""공시지가 예측 모델 훈련 CLI 스크립트.

사용법:
    uv run python -m app.scripts.train_model
    uv run python -m app.scripts.train_model --sgg-code 11110
    uv run python -m app.scripts.train_model --data-source csv --sgg-code 11110
    uv run python -m app.scripts.train_model --data-source csv --csv-dir ./data/개별공시지가
    uv run python -m app.scripts.train_model --n-trials 100 --model-dir ./ml_models
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="공시지가 예측 모델 훈련")
    parser.add_argument(
        "--sgg-code",
        type=str,
        default=None,
        help="특정 시군구코드(5자리)로 제한 (미지정시 전체)",
    )
    parser.add_argument(
        "--n-trials",
        type=int,
        default=50,
        help="Optuna 튜닝 trials 수 (기본: 50)",
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default="./ml_models",
        help="모델 저장 경로 (기본: ./ml_models)",
    )
    parser.add_argument(
        "--min-years",
        type=int,
        default=1,
        help="최소 공시지가 이력 연수 (기본: 1)",
    )
    parser.add_argument(
        "--data-source",
        type=str,
        choices=["csv", "db", "hybrid"],
        default="csv",
        help="학습 데이터 소스 (기본: csv)",
    )
    parser.add_argument(
        "--csv-dir",
        type=str,
        default=None,
        help="개별공시지가 CSV/ZIP 디렉토리 (기본: pipeline/public_data/개별공시지가/)",
    )
    return parser.parse_args()


async def _run_csv_mode(args: argparse.Namespace) -> None:
    """CSV 기반 학습 파이프라인."""
    from pathlib import Path

    from app.crud.prediction import (
        get_buildings_for_pnus,
        get_lots_by_pnus,
        get_sgg_growth_rates,
        get_sgg_price_stats,
        get_sgg_transaction_stats,
    )
    from app.database import async_session_maker
    from app.services.prediction.csv_reader import read_official_land_prices
    from app.services.prediction.training import ModelTrainer, merge_csv_prices_with_lots

    csv_dir = Path(args.csv_dir) if args.csv_dir else None

    # 1. CSV에서 가격 데이터 읽기
    console.print("[bold]1단계:[/bold] CSV에서 가격 데이터 읽기...")
    csv_prices = read_official_land_prices(
        data_dir=csv_dir,
        sgg_code=args.sgg_code,
    )
    if not csv_prices:
        console.print("[red]CSV 데이터가 없습니다.[/red]")
        sys.exit(1)
    console.print(f"  CSV PNU 수: [green]{len(csv_prices):,}[/green]개")

    pnus = list(csv_prices.keys())
    sgg_codes = list({pnu[:5] for pnu in pnus})
    console.print(f"  시군구 수: [green]{len(sgg_codes)}[/green]개")

    # 2. DB에서 토지 특성 + 건물 + 통계 조회
    console.print()
    console.print("[bold]2단계:[/bold] DB에서 보조 데이터 조회 중...")

    async with async_session_maker() as db:
        console.print("  필지 특성 조회 중...")
        lots = await get_lots_by_pnus(db, pnus)
        console.print(f"  매칭된 필지: [green]{len(lots):,}[/green]개")

        if not lots:
            console.print("[red]DB에 매칭되는 필지가 없습니다.[/red]")
            sys.exit(1)

        matched_pnus = [lot.pnu for lot in lots]

        console.print("  건물 정보 조회 중...")
        building_map = await get_buildings_for_pnus(db, matched_pnus)
        console.print(f"  건물 정보: [green]{len(building_map):,}[/green]건")

        console.print("  거래 통계 집계 중...")
        sgg_stats_map = await get_sgg_transaction_stats(db, sgg_codes)
        console.print(f"  거래 통계: [green]{len(sgg_stats_map)}[/green]개")

        console.print("  지역별 공시지가 통계 조회 중...")
        sgg_price_stats_map = await get_sgg_price_stats(db, sgg_codes)
        console.print(f"  공시지가 통계: [green]{len(sgg_price_stats_map)}[/green]개")

        console.print("  지역별 성장률 계산 중...")
        sgg_growth_rates = await get_sgg_growth_rates(db, sgg_codes)
        for code, rate in sorted(sgg_growth_rates.items()):
            console.print(f"    {code}: [cyan]{rate*100:.1f}%[/cyan]/년")

    # 3. CSV + DB 병합
    console.print()
    console.print("[bold]3단계:[/bold] CSV 가격 + DB 토지특성 병합...")
    lots_dicts = merge_csv_prices_with_lots(csv_prices, lots, db_supplement=True)
    console.print(f"  학습용 필지: [green]{len(lots_dicts):,}[/green]개")

    # 4. 모델 훈련
    console.print()
    console.print("[bold]4단계:[/bold] 모델 훈련 중 (시간이 걸릴 수 있습니다)...")
    trainer = ModelTrainer(
        model_dir=args.model_dir,
        n_trials=args.n_trials,
    )
    metadata = trainer.run(
        lots_dicts, building_map, sgg_stats_map,
        sgg_price_stats_map=sgg_price_stats_map,
        sgg_growth_rates=sgg_growth_rates,
    )

    _print_results(metadata)


async def _run_db_mode(args: argparse.Namespace) -> None:
    """기존 DB 기반 학습 파이프라인."""
    from app.crud.prediction import (
        get_buildings_for_pnus,
        get_lots_with_price_history,
        get_sgg_transaction_stats,
    )
    from app.database import async_session_maker
    from app.services.prediction.training import ModelTrainer

    console.print("[bold]1단계:[/bold] DB에서 훈련 데이터 추출 중...")

    async with async_session_maker() as db:
        lots = await get_lots_with_price_history(
            db,
            min_years=args.min_years,
            sgg_code=args.sgg_code,
        )
        if not lots:
            console.print("[red]훈련 가능한 필지가 없습니다.[/red]")
            sys.exit(1)

        console.print(f"  필지 수: [green]{len(lots):,}[/green]개")

        pnus = [lot.pnu for lot in lots]
        sgg_codes = list({pnu[:5] for pnu in pnus})

        console.print("  건물 정보 조회 중...")
        building_map = await get_buildings_for_pnus(db, pnus)
        console.print(f"  건물 정보: [green]{len(building_map):,}[/green]건")

        console.print("  거래 통계 집계 중...")
        sgg_stats_map = await get_sgg_transaction_stats(db, sgg_codes)
        console.print(f"  시군구 통계: [green]{len(sgg_stats_map)}[/green]개")

    lots_dicts = [
        {
            "pnu": lot.pnu,
            "area": lot.area,
            "jimok": lot.jimok,
            "use_zone": lot.use_zone,
            "ownership": lot.ownership,
            "owner_count": lot.owner_count,
            "official_prices": lot.official_prices,
        }
        for lot in lots
    ]

    console.print()
    console.print("[bold]2단계:[/bold] 모델 훈련 중 (시간이 걸릴 수 있습니다)...")
    trainer = ModelTrainer(
        model_dir=args.model_dir,
        n_trials=args.n_trials,
    )
    metadata = trainer.run(lots_dicts, building_map, sgg_stats_map)

    _print_results(metadata)


async def _run_hybrid_mode(args: argparse.Namespace) -> None:
    """CSV + DB 통합 학습: CSV 가격 + DB 가격을 모두 사용."""
    from pathlib import Path

    from app.crud.prediction import (
        get_buildings_for_pnus,
        get_lots_by_pnus,
        get_lots_with_price_history,
        get_sgg_growth_rates,
        get_sgg_price_stats,
        get_sgg_transaction_stats,
    )
    from app.database import async_session_maker
    from app.services.prediction.csv_reader import read_official_land_prices
    from app.services.prediction.training import ModelTrainer, merge_csv_prices_with_lots

    csv_dir = Path(args.csv_dir) if args.csv_dir else None

    console.print("[bold]1단계:[/bold] CSV + DB에서 가격 데이터 수집...")
    csv_prices = read_official_land_prices(
        data_dir=csv_dir,
        sgg_code=args.sgg_code,
    )
    console.print(f"  CSV PNU 수: [green]{len(csv_prices):,}[/green]개")

    async with async_session_maker() as db:
        # DB에서도 필지 조회 (CSV에 없는 필지 보충)
        db_lots = await get_lots_with_price_history(
            db, min_years=args.min_years, sgg_code=args.sgg_code,
        )
        console.print(f"  DB 필지 수: [green]{len(db_lots):,}[/green]개")

        # CSV PNU + DB PNU 합집합
        all_pnus = list(set(csv_prices.keys()) | {lot.pnu for lot in db_lots})
        sgg_codes = list({pnu[:5] for pnu in all_pnus})

        lots = await get_lots_by_pnus(db, all_pnus)
        console.print(f"  총 매칭 필지: [green]{len(lots):,}[/green]개")

        matched_pnus = [lot.pnu for lot in lots]
        building_map = await get_buildings_for_pnus(db, matched_pnus)
        sgg_stats_map = await get_sgg_transaction_stats(db, sgg_codes)
        sgg_price_stats_map = await get_sgg_price_stats(db, sgg_codes)
        sgg_growth_rates = await get_sgg_growth_rates(db, sgg_codes)

    lots_dicts = merge_csv_prices_with_lots(csv_prices, lots, db_supplement=True)

    console.print()
    console.print(f"[bold]2단계:[/bold] 모델 훈련 중 ({len(lots_dicts):,} 필지)...")
    trainer = ModelTrainer(model_dir=args.model_dir, n_trials=args.n_trials)
    metadata = trainer.run(
        lots_dicts, building_map, sgg_stats_map,
        sgg_price_stats_map=sgg_price_stats_map,
        sgg_growth_rates=sgg_growth_rates,
    )

    _print_results(metadata)


def _print_results(metadata: dict) -> None:
    """훈련 결과 출력."""
    console.print()
    console.rule("[bold green]훈련 완료[/bold green]")
    mode_label = metadata["mode"]
    if metadata.get("enhanced"):
        mode_label += " (enhanced)"
    console.print(f"  모드: [cyan]{mode_label}[/cyan]")
    console.print(f"  모델 버전: {metadata['version']}")
    console.print(f"  학습 샘플: {metadata['n_samples']:,}")
    console.print(f"  피쳐 수: {metadata['n_features']}")

    if "annual_growth_rate" in metadata:
        console.print(f"  평균 성장률: [cyan]{metadata['annual_growth_rate']*100:.1f}%[/cyan]/년")

    console.print()

    table = Table(title="모델 평가 지표")
    table.add_column("모델", justify="center")
    table.add_column("RMSE", justify="right")
    table.add_column("MAE", justify="right")
    table.add_column("R2", justify="right")
    table.add_column("MAPE (%)", justify="right")

    for key, m in metadata["metrics"].items():
        label = f"Year +{key}" if key.isdigit() else key
        table.add_row(
            label,
            f"{m['rmse']:,.0f}",
            f"{m['mae']:,.0f}",
            f"{m['r2']:.4f}",
            f"{m['mape']:.2f}",
        )

    console.print(table)


async def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )

    console.rule("[bold blue]공시지가 예측 모델 훈련[/bold blue]")
    console.print(f"  데이터 소스: [cyan]{args.data_source}[/cyan]")
    console.print(f"  시군구코드: {args.sgg_code or '전체'}")
    console.print(f"  Optuna trials: {args.n_trials}")
    console.print(f"  모델 저장: {args.model_dir}")
    if args.data_source in ("csv", "hybrid"):
        console.print(f"  CSV 경로: {args.csv_dir or '(기본 경로)'}")
    if args.data_source == "db":
        console.print(f"  최소 이력: {args.min_years}년")
    console.print()

    if args.data_source == "csv":
        await _run_csv_mode(args)
    elif args.data_source == "hybrid":
        await _run_hybrid_mode(args)
    else:
        await _run_db_mode(args)


if __name__ == "__main__":
    asyncio.run(main())
