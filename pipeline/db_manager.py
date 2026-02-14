"""DB 관리 모듈.

환경별 DB 연결, 테이블 스왑, bin 파일 추출/복원을 담당합니다.
"""

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from rich.console import Console
from rich.table import Table

console = Console()

DUMP_DIR = Path("dumps")


@dataclass
class DbConfig:
    """DB 연결 정보."""

    host: str
    port: int
    dbname: str
    user: str
    password: str

    @classmethod
    def from_url(cls, url: str) -> "DbConfig":
        """DATABASE_URL 형식에서 파싱합니다.

        postgresql+asyncpg://user:pass@host:port/dbname 형태를 지원합니다.
        """
        clean = url.replace("+asyncpg", "").replace("+psycopg", "")
        parsed = urlparse(clean)
        return cls(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            dbname=parsed.path.lstrip("/"),
            user=parsed.username or "postgres",
            password=parsed.password or "",
        )

    @property
    def env_dict(self) -> dict[str, str]:
        """pg_dump/pg_restore용 환경변수."""
        return {"PGPASSWORD": self.password}

    @property
    def conn_args(self) -> list[str]:
        """pg_dump/pg_restore용 공통 인자."""
        return [
            "-h", self.host,
            "-p", str(self.port),
            "-U", self.user,
            "-d", self.dbname,
        ]

    @property
    def display_name(self) -> str:
        return f"{self.user}@{self.host}:{self.port}/{self.dbname}"


class DbManager:
    """DB 관리 매니저."""

    def __init__(self, environments: dict[str, str]):
        """environments: {"local": "postgresql+asyncpg://...", "test": "...", "prod": "..."}"""
        self.environments = {
            name: DbConfig.from_url(url) for name, url in environments.items()
        }

    def get_config(self, env: str) -> DbConfig:
        if env not in self.environments:
            raise KeyError(f"등록되지 않은 환경: {env} (가능: {list(self.environments.keys())})")
        return self.environments[env]

    def list_environments(self) -> None:
        """등록된 환경 목록을 출력합니다."""
        table = Table(title="등록된 DB 환경")
        table.add_column("환경", style="cyan")
        table.add_column("호스트", style="green")
        table.add_column("포트", style="green")
        table.add_column("DB", style="yellow")
        table.add_column("사용자", style="white")

        for name, config in self.environments.items():
            table.add_row(name, config.host, str(config.port), config.dbname, config.user)

        console.print(table)

    # ── 테이블 목록 조회 ──

    def get_tables(self, env: str) -> list[str]:
        """지정 환경의 public 스키마 테이블 목록을 반환합니다."""
        config = self.get_config(env)
        result = subprocess.run(
            [
                "psql",
                *config.conn_args,
                "-t", "-A",
                "-c", "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;",
            ],
            capture_output=True,
            text=True,
            env=dict(os.environ) | config.env_dict,
            check=True,
        )
        return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]

    def show_tables(self, env: str) -> None:
        """테이블 목록과 행 수를 출력합니다."""
        config = self.get_config(env)
        tables = self.get_tables(env)

        table = Table(title=f"[{env}] 테이블 목록 ({config.display_name})")
        table.add_column("#", style="dim")
        table.add_column("테이블", style="cyan")
        table.add_column("행 수", style="green", justify="right")

        for i, tbl in enumerate(tables, 1):
            count = self._get_row_count(config, tbl)
            table.add_row(str(i), tbl, str(count))

        console.print(table)

    def _get_row_count(self, config: DbConfig, table_name: str) -> int:
        result = subprocess.run(
            [
                "psql",
                *config.conn_args,
                "-t", "-A",
                "-c", f"SELECT COUNT(*) FROM \"{table_name}\";",
            ],
            capture_output=True,
            text=True,
            env=dict(os.environ) | config.env_dict,
            check=False,
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
        return -1

    # ── Bin 파일 (pg_dump custom format) 추출/복원 ──

    def dump_tables(
        self,
        env: str,
        tables: list[str],
        output_path: Path | None = None,
    ) -> Path:
        """지정 테이블들을 pg_dump custom format(.bin)으로 추출합니다."""
        config = self.get_config(env)
        DUMP_DIR.mkdir(parents=True, exist_ok=True)

        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            table_label = tables[0] if len(tables) == 1 else f"{len(tables)}tables"
            output_path = DUMP_DIR / f"{env}_{table_label}_{timestamp}.bin"

        cmd = [
            "pg_dump",
            *config.conn_args,
            "-Fc",  # custom format (binary)
        ]
        for tbl in tables:
            cmd.extend(["-t", tbl])
        cmd.extend(["-f", str(output_path)])

        console.print(f"  추출 중: {', '.join(tables)} → {output_path}")
        subprocess.run(
            cmd,
            env=dict(os.environ) | config.env_dict,
            check=True,
        )
        size_mb = output_path.stat().st_size / 1024 / 1024
        console.print(f"  [green]완료[/]: {output_path} ({size_mb:.1f} MB)")
        return output_path

    def dump_all(self, env: str, output_path: Path | None = None) -> Path:
        """전체 DB를 pg_dump custom format으로 추출합니다."""
        config = self.get_config(env)
        DUMP_DIR.mkdir(parents=True, exist_ok=True)

        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = DUMP_DIR / f"{env}_full_{timestamp}.bin"

        cmd = ["pg_dump", *config.conn_args, "-Fc", "-f", str(output_path)]

        console.print(f"  전체 DB 추출 중 → {output_path}")
        subprocess.run(
            cmd,
            env=dict(os.environ) | config.env_dict,
            check=True,
        )
        size_mb = output_path.stat().st_size / 1024 / 1024
        console.print(f"  [green]완료[/]: {output_path} ({size_mb:.1f} MB)")
        return output_path

    def restore(self, env: str, dump_path: Path, clean: bool = False) -> None:
        """bin 파일을 지정 환경 DB에 복원합니다.

        Args:
            env: 대상 환경
            dump_path: .bin 파일 경로
            clean: True면 기존 데이터 삭제 후 복원
        """
        config = self.get_config(env)

        if not dump_path.exists():
            raise FileNotFoundError(f"파일이 없습니다: {dump_path}")

        cmd = [
            "pg_restore",
            *config.conn_args,
            "--no-owner",
            "--no-privileges",
        ]
        if clean:
            cmd.append("--clean")
        cmd.append(str(dump_path))

        console.print(f"  복원 중: {dump_path} → [{env}] {config.display_name}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=dict(os.environ) | config.env_dict,
            check=False,
        )
        if result.returncode != 0 and result.stderr:
            # pg_restore는 경고도 stderr로 출력하므로 에러만 필터링
            errors = [line for line in result.stderr.split("\n") if "ERROR" in line]
            if errors:
                console.print("  [red]에러 발생:[/]")
                for e in errors:
                    console.print("    {e}")
            else:
                console.print("  [green]복원 완료[/] (경고 있음, 정상)")
        else:
            console.print("  [green]복원 완료[/]")

    def list_dumps(self) -> list[Path]:
        """dumps/ 디렉토리의 bin 파일 목록을 반환합니다."""
        if not DUMP_DIR.exists():
            return []
        return sorted(DUMP_DIR.glob("*.bin"), key=lambda p: p.stat().st_mtime, reverse=True)

    # ── 테이블 스왑 ──

    def swap_table(self, env: str, table_a: str, table_b: str) -> None:
        """같은 환경 내에서 두 테이블 이름을 스왑합니다.

        임시 테이블명을 활용한 3단계 rename입니다.
        """
        config = self.get_config(env)
        tmp = f"_swap_tmp_{table_a}"

        sql = f"""
        ALTER TABLE "{table_a}" RENAME TO "{tmp}";
        ALTER TABLE "{table_b}" RENAME TO "{table_a}";
        ALTER TABLE "{tmp}" RENAME TO "{table_b}";
        """

        console.print("  스왑 중: {table_a} ↔ {table_b}")
        subprocess.run(
            ["psql", *config.conn_args, "-c", sql],
            env=dict(os.environ) | config.env_dict,
            check=True,
        )
        console.print("  [green]스왑 완료[/]")

    def copy_table_cross_env(
        self,
        source_env: str,
        target_env: str,
        tables: list[str],
        clean: bool = False,
    ) -> None:
        """소스 환경에서 테이블을 추출하여 타겟 환경에 복원합니다.

        local → test, test → prod 등 환경 간 데이터 이동에 사용합니다.
        """
        console.print("\n[bold]테이블 복사: [{source_env}] → [{target_env}][/]")
        console.print("  대상 테이블: {', '.join(tables)}")

        dump_path = self.dump_tables(source_env, tables)
        self.restore(target_env, dump_path, clean=clean)

        console.print("  [green]환경 간 복사 완료[/]")

    # ── 테이블 초기화 ──

    def truncate_tables(self, env: str, tables: list[str]) -> None:
        """지정 테이블의 데이터를 삭제합니다 (CASCADE)."""
        config = self.get_config(env)

        table_list = ", ".join(f'"{t}"' for t in tables)
        sql = f"TRUNCATE TABLE {table_list} CASCADE;"

        console.print("  초기화 중: {', '.join(tables)}")
        subprocess.run(
            ["psql", *config.conn_args, "-c", sql],
            env=dict(os.environ) | config.env_dict,
            check=True,
        )
        console.print("  [green]초기화 완료[/]")

    def drop_tables(self, env: str, tables: list[str]) -> None:
        """지정 테이블을 삭제합니다 (CASCADE)."""
        config = self.get_config(env)

        table_list = ", ".join(f'"{t}"' for t in tables)
        sql = f"DROP TABLE IF EXISTS {table_list} CASCADE;"

        console.print("  삭제 중: {', '.join(tables)}")
        subprocess.run(
            ["psql", *config.conn_args, "-c", sql],
            env=dict(os.environ) | config.env_dict,
            check=True,
        )
        console.print("  [green]삭제 완료[/]")
