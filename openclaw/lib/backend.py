"""CLARKE backend orchestration — docker, migrations, API server, tenant setup."""

import subprocess
import sys
import time
from pathlib import Path

import httpx

DEFAULT_ENDPOINT = "http://localhost:8000"


def check_clarke_health(endpoint: str = DEFAULT_ENDPOINT) -> bool:
    """Check if CLARKE API is healthy."""
    try:
        resp = httpx.get(f"{endpoint}/health", timeout=5.0)
        return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def find_clarke_repo() -> Path:
    """Find the CLARKE repository root (where docker-compose.yml lives)."""
    # Check if we're inside the CLARKE repo
    candidates = [
        Path(__file__).resolve().parent.parent.parent,  # openclaw/lib/ -> clarke_v2/
        Path.cwd(),
    ]
    for candidate in candidates:
        if (candidate / "docker-compose.yml").exists() and (candidate / "clarke").is_dir():
            return candidate
    raise FileNotFoundError(
        "Cannot find CLARKE repository. Run from the clarke_v2 directory "
        "or set CLARKE_REPO environment variable."
    )


def start_backend(clarke_repo: Path | None = None, timeout: int = 60) -> bool:
    """Start CLARKE backend services via docker compose."""
    repo = clarke_repo or find_clarke_repo()
    print("  Starting docker compose services...")
    try:
        subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"  docker compose failed: {e.stderr}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("  docker not found on PATH", file=sys.stderr)
        return False

    # Wait for health checks
    print("  Waiting for services to be healthy...", end="", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and "unhealthy" not in result.stdout:
            print(" ready")
            return True
        print(".", end="", flush=True)
        time.sleep(2)

    print(" timeout", file=sys.stderr)
    return False


def run_migrations(clarke_repo: Path | None = None) -> bool:
    """Run alembic migrations."""
    repo = clarke_repo or find_clarke_repo()
    print("  Running database migrations...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("  Migrations complete")
            return True
        # Check if it's a "nothing to do" case
        if "already" in result.stdout.lower() or result.returncode == 0:
            print("  Migrations already up to date")
            return True
        print(f"  Migration failed: {result.stderr[:200]}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  Migration error: {e}", file=sys.stderr)
        return False


def start_api_server(clarke_repo: Path | None = None, endpoint: str = DEFAULT_ENDPOINT) -> bool:
    """Start the CLARKE API server in the background if not already running."""
    if check_clarke_health(endpoint):
        print("  CLARKE API already running")
        return True

    repo = clarke_repo or find_clarke_repo()
    print("  Starting CLARKE API server...")
    try:
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "clarke.api.app:create_app",
                "--factory",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
            ],
            cwd=repo,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"  Failed to start API server: {e}", file=sys.stderr)
        return False

    # Wait for it to come up
    for _ in range(30):
        time.sleep(1)
        if check_clarke_health(endpoint):
            print("  CLARKE API started")
            return True

    print("  CLARKE API did not start in time", file=sys.stderr)
    return False


def ensure_tenant_project(
    endpoint: str,
    tenant_name: str = "default",
    project_name: str = "default",
) -> tuple[str, str]:
    """Create tenant + project via the admin setup endpoint. Returns (tenant_id, project_id)."""
    resp = httpx.post(
        f"{endpoint}/admin/setup",
        json={"tenant_name": tenant_name, "project_name": project_name},
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["tenant_id"], data["project_id"]
