# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["pgserver>=0.1.4"]
# ///
"""Local development database: PostgreSQL 16 + pgvector, no Docker or admin rights needed.

Usage (from backend/):
    uv run scripts/dev_db.py start    # init on first run, then start
    uv run scripts/dev_db.py stop
    uv run scripts/dev_db.py status

Dev only: the server listens on localhost and trusts local connections.
"""

import subprocess
import sys
from pathlib import Path

import pgserver

PORT = 5433
DB_NAME = "clauselens"
TEST_DB_NAME = "clauselens_test"  # used by the integration tests
DB_USER = "clauselens"
DB_PASSWORD = "clauselens"

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / ".pgdata"
LOG_FILE = BACKEND_DIR / ".pgdata.log"
BIN_DIR = Path(pgserver.__file__).parent / "pginstall" / "bin"


def run(tool: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(BIN_DIR / tool), *args], check=check, capture_output=True, text=True)


def psql(sql: str, database: str = "postgres") -> str:
    result = run(
        "psql", "-h", "localhost", "-p", str(PORT), "-U", "postgres", "-d", database, "-tAc", sql
    )
    return result.stdout.strip()


def is_running() -> bool:
    return run("pg_ctl", "status", "-D", str(DATA_DIR), check=False).returncode == 0


def init_cluster() -> None:
    print(f"Creating database cluster in {DATA_DIR} ...")
    run("initdb", "-D", str(DATA_DIR), "-U", "postgres", "-A", "trust", "-E", "UTF8", "--no-locale")
    with (DATA_DIR / "postgresql.conf").open("a", encoding="utf-8") as conf:
        conf.write(f"\nport = {PORT}\nlisten_addresses = 'localhost'\n")


def ensure_database() -> None:
    if psql(f"SELECT 1 FROM pg_roles WHERE rolname = '{DB_USER}'") != "1":
        psql(f"CREATE ROLE {DB_USER} LOGIN PASSWORD '{DB_PASSWORD}'")
    for name in (DB_NAME, TEST_DB_NAME):
        if psql(f"SELECT 1 FROM pg_database WHERE datname = '{name}'") != "1":
            psql(f"CREATE DATABASE {name} OWNER {DB_USER}")
        psql("CREATE EXTENSION IF NOT EXISTS vector", database=name)


def start() -> None:
    if not (DATA_DIR / "PG_VERSION").exists():
        init_cluster()
    if is_running():
        print("Database already running.")
    else:
        # Not captured: the server inherits pg_ctl's handles, so a pipe would never close.
        subprocess.run(
            [str(BIN_DIR / "pg_ctl"), "start", "-D", str(DATA_DIR), "-l", str(LOG_FILE), "-w"],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"Database started on localhost:{PORT}.")
    ensure_database()
    version = psql("SELECT extversion FROM pg_extension WHERE extname = 'vector'", DB_NAME)
    print(f"pgvector {version} ready in database '{DB_NAME}'.")
    print(f"DATABASE_URL=postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@localhost:{PORT}/{DB_NAME}")


def stop() -> None:
    if is_running():
        run("pg_ctl", "stop", "-D", str(DATA_DIR), "-m", "fast", "-w")
        print("Database stopped.")
    else:
        print("Database is not running.")


def status() -> None:
    print(f"Database is {'running' if is_running() else 'stopped'} (localhost:{PORT}).")


COMMANDS = {"start": start, "stop": stop, "status": status}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    try:
        COMMANDS[sys.argv[1]]()
    except subprocess.CalledProcessError as error:
        print(f"Command failed: {' '.join(error.cmd)}\n{error.stderr}", file=sys.stderr)
        print(f"See the server log for details: {LOG_FILE}", file=sys.stderr)
        sys.exit(1)
