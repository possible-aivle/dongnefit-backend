"""DB 관리 모듈.

환경별 DB 연결, 테이블 스왑, bin 파일 추출/복원을 담당합니다.
"""

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from rich.table import Table

from app.pipeline import console

DUMP_DIR = Path("dumps")
DOCKER_CONTAINER = "realestate-db"
SWAP_TABLE_PREFIXES = ("_swap_tmp_", "_old_", "_new_")


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
    def docker_conn_args(self) -> list[str]:
        """Docker 컨테이너 내부용 연결 인자 (host 불필요)."""
        return ["-U", self.user, "-d", self.dbname]

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

    def _use_docker(self, config: DbConfig) -> bool:
        """localhost DB가 Docker 컨테이너에서 실행 중이면 True를 반환합니다."""
        if config.host not in ("localhost", "127.0.0.1"):
            return False
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", DOCKER_CONTAINER],
                capture_output=True, text=True, check=False,
            )
            return result.returncode == 0 and "true" in result.stdout.strip()
        except FileNotFoundError:
            return False

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
        row_counts = self._get_all_row_counts(config)

        table = Table(title=f"[{env}] 테이블 목록 ({config.display_name})")
        table.add_column("#", style="dim")
        table.add_column("테이블", style="cyan")
        table.add_column("행 수", style="green", justify="right")

        for i, (tbl, count) in enumerate(sorted(row_counts.items()), 1):
            table.add_row(str(i), tbl, f"{count:,}")

        console.print(table)

    def _get_all_row_counts(self, config: DbConfig) -> dict[str, int]:
        """모든 public 테이블의 행 수를 단일 쿼리로 반환합니다."""
        result = subprocess.run(
            [
                "psql",
                *config.conn_args,
                "-t", "-A",
                "-c",
                "SELECT relname, n_live_tup::bigint "
                "FROM pg_stat_user_tables "
                "WHERE schemaname = 'public' "
                "ORDER BY relname;",
            ],
            capture_output=True,
            text=True,
            env=dict(os.environ) | config.env_dict,
            check=False,
        )
        counts: dict[str, int] = {}
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if "|" in line:
                    parts = line.split("|")
                    counts[parts[0].strip()] = int(parts[1].strip())
        return counts

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

        table_args: list[str] = []
        for tbl in tables:
            table_args.extend(["-t", tbl])

        console.print(f"  추출 중: {', '.join(tables)} → {output_path}")

        if self._use_docker(config):
            cmd = [
                "docker", "exec", DOCKER_CONTAINER,
                "pg_dump", *config.docker_conn_args, "-Fc", *table_args,
            ]
            with open(output_path, "wb") as f:
                subprocess.run(cmd, stdout=f, check=True)
        else:
            cmd = [
                "pg_dump", *config.conn_args, "-Fc", *table_args,
                "-f", str(output_path),
            ]
            subprocess.run(cmd, env=dict(os.environ) | config.env_dict, check=True)

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

        console.print(f"  전체 DB 추출 중 → {output_path}")

        if self._use_docker(config):
            cmd = [
                "docker", "exec", DOCKER_CONTAINER,
                "pg_dump", *config.docker_conn_args, "-Fc",
            ]
            with open(output_path, "wb") as f:
                subprocess.run(cmd, stdout=f, check=True)
        else:
            cmd = ["pg_dump", *config.conn_args, "-Fc", "-f", str(output_path)]
            subprocess.run(cmd, env=dict(os.environ) | config.env_dict, check=True)

        size_mb = output_path.stat().st_size / 1024 / 1024
        console.print(f"  [green]완료[/]: {output_path} ({size_mb:.1f} MB)")
        return output_path

    def _list_tables_in_dump(self, dump_path: Path) -> list[str]:
        """덤프 파일에 포함된 테이블 목록을 반환합니다."""
        if self._use_docker(self.get_config(list(self.environments.keys())[0])):
            cmd = ["docker", "exec", "-i", DOCKER_CONTAINER, "pg_restore", "--list"]
            with open(dump_path, "rb") as f:
                result = subprocess.run(cmd, stdin=f, capture_output=True, text=True, check=False)
        else:
            cmd = ["pg_restore", "--list", str(dump_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        tables: list[str] = []
        for line in result.stdout.split("\n"):
            # "NNN; NNNN NNNNN TABLE DATA public tablename owner" 형식
            if "TABLE DATA" in line and "public" in line:
                parts = line.split()
                try:
                    public_idx = parts.index("public")
                    tables.append(parts[public_idx + 1])
                except (ValueError, IndexError):
                    continue
        return tables

    def restore(self, env: str, dump_path: Path, clean: bool = False) -> None:
        """bin 파일을 지정 환경 DB에 복원합니다.

        --data-only 모드로 복원하여 Alembic 관리 스키마(PostGIS geometry 타입,
        spatial index 등)를 보존합니다.
        clean=True이면 대상 테이블을 TRUNCATE 후 데이터만 복원합니다.

        Args:
            env: 대상 환경
            dump_path: .bin 파일 경로
            clean: True면 기존 데이터 삭제 후 복원
        """
        config = self.get_config(env)

        if not dump_path.exists():
            raise FileNotFoundError(f"파일이 없습니다: {dump_path}")

        console.print(f"  복원 중: {dump_path} → [{env}] {config.display_name}")

        # clean 모드: 덤프에 포함된 테이블을 TRUNCATE
        if clean:
            tables = self._list_tables_in_dump(dump_path)
            if tables:
                # alembic_version은 TRUNCATE 대상에서 제외
                tables = [t for t in tables if t != "alembic_version"]
                table_list = ", ".join(f'"{t}"' for t in tables)
                console.print(f"  TRUNCATE: {len(tables)}개 테이블")
                subprocess.run(
                    [
                        "psql", *config.conn_args,
                        "-c", f"TRUNCATE TABLE {table_list} CASCADE;",
                    ],
                    env=dict(os.environ) | config.env_dict,
                    capture_output=True,
                    check=True,
                )

        # --data-only: 스키마(테이블 구조, 인덱스, geometry 타입)를 보존하고 데이터만 복원
        if self._use_docker(config):
            cmd = [
                "docker", "exec", "-i", DOCKER_CONTAINER,
                "pg_restore", *config.docker_conn_args,
                "--no-owner", "--no-privileges",
                "--data-only",
            ]
            with open(dump_path, "rb") as f:
                result = subprocess.run(
                    cmd, stdin=f, capture_output=True, text=False, check=False,
                )
            stderr_text = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
        else:
            cmd = [
                "pg_restore", *config.conn_args,
                "--no-owner", "--no-privileges",
                "--data-only",
                str(dump_path),
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                env=dict(os.environ) | config.env_dict, check=False,
            )
            stderr_text = result.stderr or ""

        if result.returncode != 0 and stderr_text:
            # pg_restore는 경고도 stderr로 출력하므로 에러만 필터링
            errors = [line for line in stderr_text.split("\n") if "ERROR" in line]
            if errors:
                console.print("  [red]에러 발생:[/]")
                for e in errors:
                    console.print(f"    {e}")
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

        console.print(f"  스왑 중: {table_a} ↔ {table_b}")
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
        console.print(f"\n[bold]테이블 복사: [{source_env}] → [{target_env}][/]")
        console.print(f"  대상 테이블: {', '.join(tables)}")

        dump_path = self.dump_tables(source_env, tables)
        self.restore(target_env, dump_path, clean=clean)

        console.print("  [green]환경 간 복사 완료[/]")

    # ── 테이블 초기화 ──

    def truncate_tables(self, env: str, tables: list[str]) -> None:
        """지정 테이블의 데이터를 삭제합니다 (CASCADE)."""
        config = self.get_config(env)

        table_list = ", ".join(f'"{t}"' for t in tables)
        sql = f"TRUNCATE TABLE {table_list} CASCADE;"

        console.print(f"  초기화 중: {', '.join(tables)}")
        subprocess.run(
            ["psql", *config.conn_args, "-c", sql],
            env=dict(os.environ) | config.env_dict,
            check=True,
        )
        console.print("  [green]초기화 완료[/]")

    def get_swap_tables(self, env: str) -> list[str]:
        """스왑 접두어가 붙은 테이블 목록을 반환합니다."""
        return [t for t in self.get_tables(env) if t.startswith(SWAP_TABLE_PREFIXES)]

    def drop_tables(self, env: str, tables: list[str]) -> None:
        """스왑용 임시 테이블을 삭제합니다 (CASCADE).

        Alembic 관리 테이블 보호를 위해 스왑 접두어(_swap_tmp_, _old_, _new_)가
        붙은 테이블만 삭제할 수 있습니다.
        """
        blocked = [t for t in tables if not t.startswith(SWAP_TABLE_PREFIXES)]
        if blocked:
            raise ValueError(
                f"Alembic 관리 테이블은 삭제할 수 없습니다: {', '.join(blocked)}\n"
                f"허용 접두어: {', '.join(SWAP_TABLE_PREFIXES)}"
            )

        config = self.get_config(env)
        table_list = ", ".join(f'"{t}"' for t in tables)
        sql = f"DROP TABLE IF EXISTS {table_list} CASCADE;"

        console.print(f"  삭제 중: {', '.join(tables)}")
        subprocess.run(
            ["psql", *config.conn_args, "-c", sql],
            env=dict(os.environ) | config.env_dict,
            check=True,
        )
        console.print("  [green]삭제 완료[/]")
