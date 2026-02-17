"""DongneFit 공공데이터 관리 CLI.

사용법:
    uv run python -m pipeline.cli
"""

import sys
from collections.abc import Callable
from pathlib import Path

from InquirerPy import inquirer
from InquirerPy.separator import Separator
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pipeline.db_manager import DbManager

console = Console()


def get_db_manager() -> DbManager:
    """환경별 DB 설정을 로드하여 DbManager를 생성합니다."""
    # .env에서 로드 (dotenv 사용)
    from dotenv import dotenv_values

    env = dotenv_values(".env")
    environments: dict[str, str] = {}

    # 기본 DATABASE_URL → local
    if db_url := env.get("DATABASE_URL"):
        environments["local"] = db_url

    # 추가 환경 (설정된 경우만)
    if test_url := env.get("DATABASE_URL_TEST"):
        environments["test"] = test_url
    if prod_url := env.get("DATABASE_URL_PROD"):
        environments["prod"] = prod_url

    if not environments:
        console.print("[red]ERROR: .env에 DATABASE_URL이 설정되지 않았습니다.[/]")
        sys.exit(1)

    return DbManager(environments)


def select_env(db: DbManager, prompt: str = "환경을 선택하세요:") -> str:
    """환경 선택 프롬프트."""
    envs = list(db.environments.keys())
    if len(envs) == 1:
        console.print(f"  환경: [cyan]{envs[0]}[/] (단일 환경)")
        return envs[0]

    return inquirer.select(
        message=prompt,
        choices=envs,
    ).execute()


def select_tables(db: DbManager, env: str, multi: bool = True) -> list[str]:
    """테이블 선택 프롬프트."""
    tables = db.get_tables(env)
    if not tables:
        console.print(f"  [yellow]{env} 환경에 테이블이 없습니다.[/]")
        return []

    if multi:
        selected = inquirer.checkbox(
            message="테이블을 선택하세요 (Space로 선택, Enter로 확인):",
            choices=tables,
        ).execute()
    else:
        selected = inquirer.select(
            message="테이블을 선택하세요:",
            choices=tables,
        ).execute()
        selected = [selected]

    return selected


# ── 메인 메뉴 ──


def main_menu() -> None:
    """메인 메뉴."""
    console.print(
        Panel(
            "[bold cyan]DongneFit 공공데이터 관리 CLI[/]",
            subtitle="v0.1.0",
            expand=False,
        )
    )

    db = get_db_manager()

    while True:
        action = inquirer.select(
            message="작업을 선택하세요:",
            choices=[
                {"name": "데이터 수집 (API → DB)", "value": "collect"},
                {"name": "공공데이터 적재 (파일 → DB)", "value": "load_public"},
                {"name": "데이터 조회 / 통계", "value": "stats"},
                Separator(),
                {"name": "DB 테이블 조회", "value": "tables"},
                {"name": "DB 테이블 스왑", "value": "swap"},
                {"name": "DB 환경 간 복사", "value": "copy_env"},
                Separator(),
                {"name": "Bin 파일 추출 (pg_dump)", "value": "dump"},
                {"name": "Bin 파일 복원 (pg_restore)", "value": "restore"},
                {"name": "Bin 파일 목록", "value": "list_dumps"},
                Separator(),
                {"name": "테이블 데이터 초기화 (TRUNCATE)", "value": "truncate"},
                {"name": "테이블 삭제 (DROP)", "value": "drop"},
                Separator(),
                {"name": "종료", "value": "exit"},
            ],
        ).execute()

        if action == "exit":
            console.print("[dim]종료합니다.[/]")
            break

        try:
            ACTIONS[action](db)
        except KeyboardInterrupt:
            console.print("\n[dim]취소됨[/]")
        except Exception as e:
            console.print(f"\n[red]에러: {e}[/]")

        console.print()


# ── 데이터 수집 ──


def action_collect(db: DbManager) -> None:
    """데이터 수집 메뉴."""
    from app.models.enums import PublicDataType
    from pipeline.registry import Registry, auto_discover

    auto_discover()

    sources = Registry.list_all()
    if not sources:
        console.print("[yellow]등록된 데이터 소스가 없습니다.[/]")
        console.print()

        # 사용 가능한 데이터 타입 안내
        table = Table(title="구현 가능한 데이터 소스 (모델 정의 완료)")
        table.add_column("데이터 타입", style="cyan")
        table.add_column("값", style="dim")
        for dt in PublicDataType:
            table.add_row(dt.name, dt.value)
        console.print(table)

        console.print("\n[dim]pipeline/processors/ 에 프로세서를 추가하면 CLI 메뉴에 자동 노출됩니다.[/]")
        return

    choices = [{"name": f"{desc} ({name})", "value": name} for name, desc in sources]
    selected = inquirer.select(
        message="데이터 소스를 선택하세요:",
        choices=choices,
    ).execute()

    processor = Registry.get(selected)
    params = processor.get_params_interactive()

    import asyncio
    result = asyncio.run(processor.run(params))

    console.print(f"\n[green]완료[/]: {result.summary()}")


# ── 공공데이터 적재 (파일 → DB) ──


# 데이터 소스 레지스트리 (카테고리별 그룹핑)
DATA_SOURCES: dict[str, dict] = {
    # 토지
    "cadastral": {
        "name": "연속지적도",
        "category": "토지",
        "dir": "연속지적도",
        "processor": "cadastral",
        "file_type": "province_name",  # 파일명에 시도 이름 포함
    },
    "land_forest": {
        "name": "토지임야정보",
        "category": "토지",
        "dir": "토지임야정보",
        "processor": "land_forest",
        "file_type": "sido_code",  # 파일명에 시도코드 포함
    },
    "land_characteristic": {
        "name": "토지특성정보",
        "category": "토지",
        "dir": "토지특성정보",
        "processor": "land_characteristic",
        "file_type": "sido_code",
        "file_prefix": "AL_D195",  # AL_D194(SHP)와 혼재 → CSV만 선택
    },
    "land_use_plan": {
        "name": "토지이용계획정보",
        "category": "토지",
        "dir": "토지이용계획정보",
        "processor": "land_use_plan",
        "file_type": "sido_code",
    },
    "official_land_price": {
        "name": "개별공시지가",
        "category": "토지",
        "dir": "개발공시지가",
        "processor": "official_land_price",
        "file_type": "sido_code",
    },
    "land_ownership": {
        "name": "토지소유정보",
        "category": "토지",
        "dir": "토지소유정보",
        "processor": "land_ownership",
        "file_type": "sido_code",
    },
    # 건물
    "building_register_header": {
        "name": "건축물대장 표제부",
        "category": "건물",
        "dir": "건축물대장_표제부",
        "processor": "building_register_header",
        "file_type": "txt_single",  # 단일 TXT 파일
    },
    "building_register_general": {
        "name": "건축물대장 총괄표제부",
        "category": "건물",
        "dir": "건축물대장_총괄표제부",
        "processor": "building_register_general",
        "file_type": "txt_single",
    },
    "building_register_floor_detail": {
        "name": "건축물대장 층별개요",
        "category": "건물",
        "dir": "건축물대장_층별개요",
        "processor": "building_register_floor_detail",
        "file_type": "txt_single",
    },
    "building_register_area": {
        "name": "건축물대장 전유공용면적",
        "category": "건물",
        "dir": "건축물대장_전유공용면적",
        "processor": "building_register_area",
        "file_type": "txt_single",
    },
    "building_register_ancillary_lot": {
        "name": "건축물대장 부속지번",
        "category": "건물",
        "dir": "건축물대장_부속지번",
        "processor": "building_register_ancillary_lot",
        "file_type": "txt_single",
    },
    "gis_building_integrated": {
        "name": "GIS건물통합정보",
        "category": "건물",
        "dir": "GIS건물통합정보",
        "processor": "gis_building_integrated",
        "file_type": "sido_code",
    },
    # 공간
    "admin_boundary_sido": {
        "name": "행정경계 시도",
        "category": "공간",
        "dir": "행정경계_시도",
        "processor": "admin_boundary_sido",
        "file_type": "single",  # 단일 전국 파일
    },
    "admin_boundary_sigungu": {
        "name": "행정경계 시군구",
        "category": "공간",
        "dir": "행정경계_시군구",
        "processor": "admin_boundary_sigungu",
        "file_type": "single",
    },
    "admin_boundary_emd": {
        "name": "행정경계 읍면동",
        "category": "공간",
        "dir": "행정경계_읍면동",
        "processor": "admin_boundary_emd",
        "file_type": "single",
    },
    "road_center_line": {
        "name": "도로중심선",
        "category": "공간",
        "dir": "도로중심선",
        "processor": "road_center_line",
        "file_type": "province_name",
    },
    "use_region_district": {
        "name": "용도지역지구정보",
        "category": "공간",
        "dir": "용도지역지구정보",
        "processor": "use_region_district",
        "file_type": "single",
    },
    # 거래
    "real_estate_sale": {
        "name": "부동산 매매 실거래가",
        "category": "거래",
        "dir": "실거래가_매매",
        "processor": "real_estate_sale",
        "file_type": "excel",
    },
    "real_estate_rental": {
        "name": "부동산 전월세 실거래가",
        "category": "거래",
        "dir": "실거래가_전월세",
        "processor": "real_estate_rental",
        "file_type": "excel",
    },
}


def action_load_public(db: DbManager) -> None:
    """공공데이터 적재 메뉴 (파일 → DB)."""
    import asyncio

    from pipeline.registry import Registry, auto_discover

    auto_discover()

    # 1. 데이터 소스 선택 (카테고리별 Separator)
    source_choices = []
    current_category = None
    for key, src in DATA_SOURCES.items():
        if src["category"] != current_category:
            if current_category is not None:
                source_choices.append(Separator())
            source_choices.append(Separator(f"── {src['category']} ──"))
            current_category = src["category"]

        # 디렉토리 존재 여부 확인
        data_dir = Path(__file__).parent / "public_data" / src["dir"]
        exists = "✓" if data_dir.exists() else "✗"
        source_choices.append({
            "name": f"[{exists}] {src['name']}",
            "value": key,
            "enabled": False,
        })

    selected_sources = inquirer.checkbox(
        message="적재할 데이터 소스 선택 (Space 선택, Enter 확인):",
        choices=source_choices,
    ).execute()

    if not selected_sources:
        console.print("[dim]선택된 데이터 소스가 없습니다.[/]")
        return

    # 2. 지역 선택 (지역 필터링이 필요한 소스가 있는 경우)
    needs_region_filter = any(
        DATA_SOURCES[s]["file_type"] not in ("single",)
        for s in selected_sources
    )

    sgg_prefixes: list[str] | None = None
    sido_codes: set[str] | None = None
    province_names: set[str] | None = None

    if needs_region_filter:
        from pipeline.regions import (
            Region,
            get_province_file_names_for_regions,
            get_sgg_prefixes_for_regions,
            get_sido_codes_for_regions,
            load_regions,
        )

        regions = load_regions()

        # 시도별 그룹핑
        region_choices = []
        region_choices.append(Separator("── 특별시/광역시 ──"))
        for r in regions:
            if r.is_metro:
                region_choices.append({
                    "name": r.name,
                    "value": r,
                    "enabled": False,
                })

        region_choices.append(Separator("── 도 ──"))
        for r in regions:
            if not r.is_metro:
                label = f"{r.name} ({r.parent})" if r.parent else r.name
                region_choices.append({
                    "name": label,
                    "value": r,
                    "enabled": False,
                })

        selected_regions: list[Region] = inquirer.checkbox(
            message="지역 선택 (Space 선택, Enter 확인, 미선택시 전체):",
            choices=region_choices,
        ).execute()

        if selected_regions:
            sido_codes = get_sido_codes_for_regions(selected_regions)
            sgg_prefixes = get_sgg_prefixes_for_regions(selected_regions)
            province_names = get_province_file_names_for_regions(selected_regions)

    # 3. 적재 옵션
    truncate = inquirer.confirm(
        message="기존 데이터 삭제 후 적재? (TRUNCATE)",
        default=False,
    ).execute()

    # 4. 확인
    console.print("\n[bold]━━━ 적재 설정 확인 ━━━[/]")
    console.print(f"  데이터 소스: {len(selected_sources)}개")
    for s in selected_sources:
        console.print(f"    - {DATA_SOURCES[s]['name']}")
    if sgg_prefixes:
        console.print(f"  지역 필터: {len(sgg_prefixes)}개 시군구 prefix")
    else:
        console.print("  지역 필터: 전체")
    console.print(f"  TRUNCATE: {'예' if truncate else '아니오'}")

    confirm = inquirer.confirm(
        message="적재를 시작하시겠습니까?",
        default=True,
    ).execute()

    if not confirm:
        console.print("[dim]취소됨[/]")
        return

    # 5. 실행
    console.print("\n[bold]━━━ 공공데이터 적재 시작 ━━━[/]\n")

    for i, source_key in enumerate(selected_sources, 1):
        src = DATA_SOURCES[source_key]
        console.print(f"[bold cyan]▶ [{i}/{len(selected_sources)}] {src['name']}[/]")

        processor_name = src["processor"]
        try:
            processor = Registry.get(processor_name)
        except KeyError:
            console.print(f"  [red]프로세서 미등록: {processor_name}[/]")
            continue

        file_type = src["file_type"]
        file_prefix = src.get("file_prefix", "")
        zip_glob = f"{file_prefix}*.zip" if file_prefix else "*.zip"
        data_dir = Path(__file__).parent / "public_data" / src["dir"]

        if not data_dir.exists():
            console.print(f"  [yellow]디렉토리 없음: {data_dir}[/]")
            continue

        try:
            params: dict = {}

            if file_type == "sido_code":
                # 시도코드 기반 ZIP 파일
                from pipeline.file_utils import find_zip_files_by_sido_code
                if sido_codes:
                    zip_files = find_zip_files_by_sido_code(
                        data_dir, sido_codes, pattern=zip_glob,
                    )
                else:
                    zip_files = sorted(data_dir.glob(zip_glob))
                params["zip_files"] = zip_files
                params["sgg_prefixes"] = sgg_prefixes

            elif file_type == "sgg_code":
                # 시군구코드 기반 ZIP 파일
                from pipeline.file_utils import find_zip_files_by_sgg_code
                if sgg_prefixes:
                    zip_files = find_zip_files_by_sgg_code(
                        data_dir, sgg_prefixes, pattern=zip_glob,
                    )
                else:
                    zip_files = sorted(data_dir.glob(zip_glob))
                params["zip_files"] = zip_files
                params["sgg_prefixes"] = sgg_prefixes

            elif file_type == "province_name":
                # 시도 이름 기반 ZIP 파일
                params["province_names"] = list(province_names) if province_names else None
                params["sgg_prefixes"] = sgg_prefixes

            elif file_type == "txt_single":
                # 단일 TXT 파일
                txt_files = list(data_dir.glob("*.txt"))
                if not txt_files:
                    console.print("  [yellow]TXT 파일 없음[/]")
                    continue
                params["file_path"] = str(txt_files[0])
                params["sgg_prefixes"] = sgg_prefixes

            elif file_type == "single":
                # 단일 전국 파일 (행정경계 등)
                params["sgg_prefixes"] = sgg_prefixes

            elif file_type == "excel":
                # 엑셀 (실거래가) - 자체 run 로직
                params["truncate"] = truncate
                params["sgg_prefixes"] = sgg_prefixes

            if truncate and file_type != "excel":
                # TRUNCATE (excel은 자체 처리)
                from pipeline.loader import get_table_name
                table_name = get_table_name(processor.data_type)
                from sqlalchemy import text

                from app.database import async_session_maker

                async def do_truncate():
                    async with async_session_maker() as session:
                        await session.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
                        await session.commit()

                asyncio.run(do_truncate())
                console.print(f"  [yellow]{table_name} TRUNCATE 완료[/]")

            result = asyncio.run(processor.run(params))
            console.print(f"  [green]완료[/]: {result.summary()}\n")

        except Exception as e:
            console.print(f"  [red]에러: {e}[/]\n")
            import traceback
            traceback.print_exc()

    console.print("[bold]━━━ 공공데이터 적재 완료 ━━━[/]")


# ── 데이터 조회/통계 ──


def action_stats(db: DbManager) -> None:
    """공공데이터 통계 조회."""
    from pipeline.loader import get_all_public_tables

    env = select_env(db)
    config = db.get_config(env)
    public_tables = get_all_public_tables()
    all_tables = db.get_tables(env)

    # 공공데이터 테이블만 필터링
    matched = [t for t in all_tables if t in public_tables]

    if not matched:
        console.print("[yellow]공공데이터 테이블이 아직 생성되지 않았습니다.[/]")
        console.print("[dim]alembic upgrade head 를 먼저 실행하세요.[/]")
        return

    table = Table(title=f"[{env}] 공공데이터 현황 ({config.display_name})")
    table.add_column("#", style="dim")
    table.add_column("테이블", style="cyan")
    table.add_column("데이터 타입", style="magenta")
    table.add_column("행 수", style="green", justify="right")

    for i, tbl in enumerate(matched, 1):
        count = db._get_row_count(config, tbl)
        data_type = public_tables[tbl].value
        table.add_row(str(i), tbl, data_type, str(count))

    console.print(table)

    # 미생성 테이블 표시
    missing = [t for t in public_tables if t not in all_tables]
    if missing:
        console.print(f"\n[dim]미생성 테이블 ({len(missing)}개): {', '.join(missing)}[/]")


# ── DB 테이블 조회 ──


def action_tables(db: DbManager) -> None:
    """테이블 목록 조회."""
    env = select_env(db)
    db.show_tables(env)


# ── 테이블 스왑 ──


def action_swap(db: DbManager) -> None:
    """테이블 스왑."""
    env = select_env(db)
    tables = db.get_tables(env)

    if len(tables) < 2:
        console.print("[yellow]스왑하려면 최소 2개의 테이블이 필요합니다.[/]")
        return

    table_a = inquirer.select(message="첫 번째 테이블:", choices=tables).execute()
    remaining = [t for t in tables if t != table_a]
    table_b = inquirer.select(message="두 번째 테이블:", choices=remaining).execute()

    confirm = inquirer.confirm(
        message=f"{table_a} ↔ {table_b} 스왑하시겠습니까?",
        default=False,
    ).execute()

    if confirm:
        db.swap_table(env, table_a, table_b)


# ── 환경 간 복사 ──


def action_copy_env(db: DbManager) -> None:
    """환경 간 테이블 복사."""
    if len(db.environments) < 2:
        console.print("[yellow]환경 간 복사는 2개 이상의 DB 환경이 필요합니다.[/]")
        console.print("[dim].env에 DATABASE_URL_TEST 또는 DATABASE_URL_PROD를 설정하세요.[/]")
        return

    source_env = select_env(db, "소스 환경 (복사 원본):")
    target_choices = [e for e in db.environments if e != source_env]
    target_env = inquirer.select(message="타겟 환경 (복사 대상):", choices=target_choices).execute()

    tables = select_tables(db, source_env)
    if not tables:
        return

    clean = inquirer.confirm(
        message="타겟 환경의 기존 데이터를 삭제하고 복원할까요?",
        default=False,
    ).execute()

    # Production 보호
    if target_env == "prod":
        double_confirm = inquirer.confirm(
            message="[경고] Production DB에 복사합니다. 정말 진행하시겠습니까?",
            default=False,
        ).execute()
        if not double_confirm:
            console.print("[dim]취소됨[/]")
            return

    db.copy_table_cross_env(source_env, target_env, tables, clean=clean)


# ── Bin 파일 추출 ──


def action_dump(db: DbManager) -> None:
    """Bin 파일 추출."""
    env = select_env(db)

    scope = inquirer.select(
        message="추출 범위:",
        choices=[
            {"name": "선택한 테이블만", "value": "tables"},
            {"name": "전체 DB", "value": "full"},
        ],
    ).execute()

    if scope == "tables":
        tables = select_tables(db, env)
        if not tables:
            return
        db.dump_tables(env, tables)
    else:
        db.dump_all(env)


# ── Bin 파일 복원 ──


def action_restore(db: DbManager) -> None:
    """Bin 파일 복원."""
    dumps = db.list_dumps()
    if not dumps:
        console.print("[yellow]dumps/ 디렉토리에 bin 파일이 없습니다.[/]")
        return

    choices = [
        {
            "name": f"{p.name} ({p.stat().st_size / 1024 / 1024:.1f} MB)",
            "value": str(p),
        }
        for p in dumps
    ]

    dump_path = inquirer.select(message="복원할 파일:", choices=choices).execute()
    env = select_env(db, "복원 대상 환경:")

    clean = inquirer.confirm(
        message="기존 데이터를 삭제하고 복원할까요? (--clean)",
        default=False,
    ).execute()

    if env == "prod":
        confirm = inquirer.confirm(
            message="[경고] Production DB에 복원합니다. 정말 진행하시겠습니까?",
            default=False,
        ).execute()
        if not confirm:
            return

    db.restore(env, Path(dump_path), clean=clean)


# ── Bin 파일 목록 ──


def action_list_dumps(db: DbManager) -> None:
    """Bin 파일 목록."""
    dumps = db.list_dumps()
    if not dumps:
        console.print("[yellow]dumps/ 디렉토리에 bin 파일이 없습니다.[/]")
        return

    table = Table(title="Bin 파일 목록")
    table.add_column("#", style="dim")
    table.add_column("파일명", style="cyan")
    table.add_column("크기", style="green", justify="right")
    table.add_column("생성일", style="yellow")

    for i, p in enumerate(dumps, 1):
        size = p.stat().st_size / 1024 / 1024
        from datetime import datetime
        mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        table.add_row(str(i), p.name, f"{size:.1f} MB", mtime)

    console.print(table)


# ── 테이블 초기화 ──


def action_truncate(db: DbManager) -> None:
    """테이블 데이터 초기화."""
    env = select_env(db)
    tables = select_tables(db, env)
    if not tables:
        return

    confirm = inquirer.confirm(
        message=f"[주의] {', '.join(tables)} 테이블의 모든 데이터를 삭제합니다. 진행하시겠습니까?",
        default=False,
    ).execute()

    if confirm:
        db.truncate_tables(env, tables)


# ── 테이블 삭제 ──


def action_drop(db: DbManager) -> None:
    """테이블 삭제."""
    env = select_env(db)
    tables = select_tables(db, env)
    if not tables:
        return

    if env == "prod":
        console.print("[red bold]Production 환경에서 테이블 삭제는 허용되지 않습니다.[/]")
        return

    confirm = inquirer.confirm(
        message=f"[경고] {', '.join(tables)} 테이블을 완전히 삭제합니다. 진행하시겠습니까?",
        default=False,
    ).execute()

    if confirm:
        db.drop_tables(env, tables)


# ── 액션 매핑 ──

ACTIONS: dict[str, Callable[[DbManager], None]] = {
    "collect": action_collect,
    "load_public": action_load_public,
    "stats": action_stats,
    "tables": action_tables,
    "swap": action_swap,
    "copy_env": action_copy_env,
    "dump": action_dump,
    "restore": action_restore,
    "list_dumps": action_list_dumps,
    "truncate": action_truncate,
    "drop": action_drop,
}


if __name__ == "__main__":
    main_menu()
