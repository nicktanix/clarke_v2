#!/usr/bin/env bash
#
# CLARKE for OpenClaw — One-Line Installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/nicktanix/clarke_v2/main/setup.sh | bash
#
#   # Or with options:
#   curl -fsSL https://raw.githubusercontent.com/nicktanix/clarke_v2/main/setup.sh | bash -s -- \
#       --workspace /path/to/openclaw/workspace \
#       --openai-key sk-...
#
# What this does:
#   1. Checks prerequisites (python3, docker, git)
#   2. Clones the CLARKE repository
#   3. Creates a Python virtual environment and installs CLARKE
#   4. Starts backend services (PostgreSQL, Qdrant, Neo4j)
#   5. Runs database migrations
#   6. Starts the CLARKE API server
#   7. Runs the OpenClaw installer (agent profiles, skills, hooks, MCP, context)
#
# Environment variables:
#   CLARKE_INSTALL_DIR   Where to clone CLARKE (default: ~/.clarke)
#   CLARKE_REPO_URL      Git repository URL (default: https://github.com/nicktanix/clarke_v2.git)
#   CLARKE_BRANCH        Git branch to clone (default: main)
#   OPENAI_API_KEY       Required for embeddings (can also pass --openai-key)
#

set -euo pipefail

# ── Colors ──────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${BLUE}[clarke]${NC} $*"; }
ok()    { echo -e "${GREEN}[clarke]${NC} $*"; }
warn()  { echo -e "${YELLOW}[clarke]${NC} $*"; }
err()   { echo -e "${RED}[clarke]${NC} $*" >&2; }
step()  { echo -e "\n${BOLD}── $* ──${NC}"; }

# ── Defaults ────────────────────────────────────────────────────────

INSTALL_DIR="${CLARKE_INSTALL_DIR:-$HOME/.clarke}"
REPO_URL="${CLARKE_REPO_URL:-https://github.com/nicktanix/clarke_v2.git}"
BRANCH="${CLARKE_BRANCH:-main}"
WORKSPACE=""
OPENAI_KEY="${OPENAI_API_KEY:-}"
SKIP_SUPERPOWERS=false
PORT=8000
DRY_RUN=false

# ── Parse Arguments ─────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --workspace)      WORKSPACE="$2"; shift 2 ;;
        --install-dir)    INSTALL_DIR="$2"; shift 2 ;;
        --openai-key)     OPENAI_KEY="$2"; shift 2 ;;
        --port)           PORT="$2"; shift 2 ;;
        --branch)         BRANCH="$2"; shift 2 ;;
        --skip-superpowers) SKIP_SUPERPOWERS=true; shift ;;
        --dry-run)        DRY_RUN=true; shift ;;
        --help|-h)
            echo "CLARKE for OpenClaw — One-Line Installer"
            echo ""
            echo "Usage: curl -fsSL <url>/setup.sh | bash -s -- [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --workspace PATH       OpenClaw workspace (default: auto-detect from cwd)"
            echo "  --install-dir PATH     Where to clone CLARKE (default: ~/.clarke)"
            echo "  --openai-key KEY       OpenAI API key for embeddings"
            echo "  --port PORT            CLARKE API port (default: 8000)"
            echo "  --branch BRANCH        Git branch (default: main)"
            echo "  --skip-superpowers     Skip cloning superpowers skills"
            echo "  --dry-run              Show what would be done"
            echo "  -h, --help             Show this help"
            exit 0
            ;;
        *) err "Unknown option: $1"; exit 1 ;;
    esac
done

ENDPOINT="http://localhost:${PORT}"

# ── Banner ──────────────────────────────────────────────────────────

echo -e "${BOLD}"
echo "   _____ _        _    ____  _  _______"
echo "  / ____| |      / \  |  _ \| |/ / ____|"
echo " | |    | |     / _ \ | |_) | ' /|  _|"
echo " | |    | |___ / ___ \|  _ <| . \| |___"
echo "  \____|_____/_/   \_\_| \_\_|\_\_____|"
echo ""
echo " Cognitive Learning Augmentation Retrieval Knowledge Engine"
echo -e "${NC}"
echo " Installing CLARKE for OpenClaw..."
echo ""

# ── Prerequisites ───────────────────────────────────────────────────

step "Checking prerequisites"

check_cmd() {
    if command -v "$1" &>/dev/null; then
        ok "$1 found: $(command -v "$1")"
        return 0
    else
        err "$1 not found"
        return 1
    fi
}

MISSING=0
check_cmd docker || MISSING=1
check_cmd git    || MISSING=1

# Check docker compose (v2 plugin or standalone)
if docker compose version &>/dev/null; then
    ok "docker compose found (plugin)"
    COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    ok "docker-compose found (standalone)"
    COMPOSE="docker-compose"
else
    err "docker compose not found (need docker compose v2 or docker-compose)"
    MISSING=1
fi

# ── Find a compatible Python (3.12 or 3.13) ────────────────────────
# python3.14+ is not supported (langchain/pydantic v1 compat).
# We check, in order of preference:
#   1. python3.13, python3.12 (explicit minor version binaries)
#   2. python3 (if it happens to be 3.12 or 3.13)
#   3. Scan common paths: /usr/bin, /usr/local/bin, homebrew, pyenv, asdf

PYTHON=""

check_python_bin() {
    local bin="$1"
    if [[ ! -x "$bin" ]] && ! command -v "$bin" &>/dev/null; then
        return 1
    fi
    local ver
    ver=$("$bin" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null) || return 1
    local major minor
    major=$(echo "$ver" | cut -d. -f1)
    minor=$(echo "$ver" | cut -d. -f2)
    if [[ "$major" -eq 3 && "$minor" -ge 12 && "$minor" -lt 14 ]]; then
        PYTHON="$bin"
        PYTHON_VERSION="$ver"
        return 0
    fi
    return 1
}

# Try explicit versioned binaries first (most reliable)
for candidate in python3.13 python3.12; do
    check_python_bin "$candidate" && break
done

# Fall back to python3 if no versioned binary found
if [[ -z "$PYTHON" ]]; then
    check_python_bin python3 || true
fi

# Scan common install locations
if [[ -z "$PYTHON" ]]; then
    SEARCH_DIRS=(
        /usr/bin
        /usr/local/bin
        /opt/homebrew/bin
        /home/linuxbrew/.linuxbrew/bin
        /home/linuxbrew/.linuxbrew/opt/python@3.13/bin
        /home/linuxbrew/.linuxbrew/opt/python@3.12/bin
        /opt/homebrew/opt/python@3.13/bin
        /opt/homebrew/opt/python@3.12/bin
        "$HOME/.pyenv/shims"
        "$HOME/.asdf/shims"
    )
    for dir in "${SEARCH_DIRS[@]}"; do
        [[ -d "$dir" ]] || continue
        for candidate in "$dir"/python3.13 "$dir"/python3.12; do
            check_python_bin "$candidate" && break 2
        done
    done
fi

if [[ -n "$PYTHON" ]]; then
    ok "Python $PYTHON_VERSION ($PYTHON)"
else
    # Show what was found for debugging
    DEFAULT_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "not found")
    err "No compatible Python found (need 3.12 or 3.13, found: $DEFAULT_VER)"
    err "Searched: python3.13, python3.12, python3, and common install paths"
    err "Install Python 3.12 or 3.13:"
    err "  Ubuntu/Debian: sudo apt install python3.13 python3.13-venv"
    err "  macOS:         brew install python@3.13"
    err "  pyenv:         pyenv install 3.13"
    MISSING=1
fi

if [[ $MISSING -eq 1 ]]; then
    echo ""
    err "Missing prerequisites. Install them and try again."
    exit 1
fi

# ── OpenAI Key ──────────────────────────────────────────────────────

if [[ -z "$OPENAI_KEY" ]]; then
    warn "No OpenAI API key provided."
    warn "CLARKE needs an embedding model. Set OPENAI_API_KEY or pass --openai-key."
    echo ""
    read -rp "Enter your OpenAI API key (or press Enter to skip): " OPENAI_KEY
    if [[ -z "$OPENAI_KEY" ]]; then
        warn "Continuing without API key — embeddings will fail until configured."
    fi
fi

if [[ "$DRY_RUN" == "true" ]]; then
    info "[dry-run] Would install to: $INSTALL_DIR"
    info "[dry-run] Would use endpoint: $ENDPOINT"
    [[ -n "$WORKSPACE" ]] && info "[dry-run] Would configure workspace: $WORKSPACE"
    exit 0
fi

# ── Clone Repository ────────────────────────────────────────────────

step "Installing CLARKE"

if [[ -d "$INSTALL_DIR" ]]; then
    info "CLARKE already installed at $INSTALL_DIR"
    info "Updating..."
    cd "$INSTALL_DIR"
    git pull --ff-only origin "$BRANCH" 2>/dev/null || warn "Could not update — using existing version"
else
    info "Cloning CLARKE to $INSTALL_DIR..."
    git clone --depth=1 --branch="$BRANCH" "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

ok "CLARKE source ready at $INSTALL_DIR"

# ── Virtual Environment ─────────────────────────────────────────────

step "Setting up Python environment"

if [[ ! -d ".venv" ]]; then
    info "Creating virtual environment with $PYTHON ($PYTHON_VERSION)..."
    "$PYTHON" -m venv .venv
elif [[ -n "$PYTHON" ]]; then
    # Verify existing venv uses a compatible Python
    VENV_VER=$(.venv/bin/python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
    VENV_MINOR=$(echo "$VENV_VER" | cut -d. -f2)
    if [[ "$VENV_MINOR" -ge 14 ]] || [[ "$VENV_MINOR" -lt 12 ]]; then
        warn "Existing venv uses Python $VENV_VER — recreating with $PYTHON_VERSION"
        rm -rf .venv
        "$PYTHON" -m venv .venv
    fi
fi

source .venv/bin/activate
info "Installing CLARKE and dependencies..."
pip install -e ".[dev]" --quiet 2>&1 | tail -1 || pip install -e ".[dev]" 2>&1 | tail -5
ok "Python environment ready"

# ── Environment File ────────────────────────────────────────────────

step "Configuring environment"

if [[ ! -f ".env" ]]; then
    cp .env.example .env
    info "Created .env from .env.example"
fi

# Ensure .env ends with a newline before appending anything
[[ -s .env && "$(tail -c1 .env)" != "" ]] && echo "" >> .env

# Set the OpenAI key if provided
if [[ -n "$OPENAI_KEY" ]]; then
    if grep -q "^OPENAI_API_KEY=" .env; then
        sed -i "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=$OPENAI_KEY|" .env
    else
        echo "OPENAI_API_KEY=$OPENAI_KEY" >> .env
    fi
    ok "OpenAI API key configured"
fi

# Enable features
if ! grep -q "CLARKE_SESSION_CONTEXT_ENABLED" .env; then
    echo "CLARKE_SESSION_CONTEXT_ENABLED=true" >> .env
fi
if ! grep -q "CLARKE_SELF_IMPROVEMENT_ENABLED" .env; then
    echo "CLARKE_SELF_IMPROVEMENT_ENABLED=true" >> .env
fi
ok "Dynamic context and self-improvement enabled"

# ── Backend Services ────────────────────────────────────────────────

step "Starting backend services"

# Check if already running
if curl -sf "$ENDPOINT/health" &>/dev/null; then
    ok "CLARKE backend already running at $ENDPOINT"
else
    info "Starting Docker services..."
    $COMPOSE up -d

    info "Waiting for services..."
    for i in $(seq 1 30); do
        if $COMPOSE ps --format "{{.Status}}" 2>/dev/null | grep -q "healthy"; then
            break
        fi
        sleep 2
        echo -n "."
    done
    echo ""
    ok "Docker services ready"

    # Run migrations
    info "Running database migrations..."
    .venv/bin/python -m alembic upgrade head 2>&1 | grep -E "^INFO|Running" || true
    ok "Migrations complete"

    # Start API server
    info "Starting CLARKE API server on port $PORT..."
    nohup .venv/bin/python -m uvicorn clarke.api.app:create_app \
        --factory --host 0.0.0.0 --port "$PORT" \
        > /tmp/clarke-api.log 2>&1 &
    CLARKE_PID=$!
    echo "$CLARKE_PID" > "$INSTALL_DIR/.clarke.pid"

    # Wait for API
    for i in $(seq 1 15); do
        if curl -sf "$ENDPOINT/health" &>/dev/null; then
            break
        fi
        sleep 1
    done

    if curl -sf "$ENDPOINT/health" &>/dev/null; then
        ok "CLARKE API running (PID $CLARKE_PID)"
    else
        err "CLARKE API failed to start. Check /tmp/clarke-api.log"
        exit 1
    fi
fi

# ── OpenClaw Integration ────────────────────────────────────────────

step "Installing into OpenClaw"

INSTALL_ARGS=(
    --endpoint "$ENDPOINT"
)

if [[ -n "$WORKSPACE" ]]; then
    INSTALL_ARGS+=(--workspace "$WORKSPACE")
fi

if [[ "$SKIP_SUPERPOWERS" == "true" ]]; then
    INSTALL_ARGS+=(--skip-superpowers)
fi

.venv/bin/python openclaw/install.py "${INSTALL_ARGS[@]}"

# ── Summary ─────────────────────────────────────────────────────────

step "Installation complete"

echo ""
echo -e "${GREEN}${BOLD}CLARKE is ready!${NC}"
echo ""
echo "  Install dir:  $INSTALL_DIR"
echo "  API endpoint: $ENDPOINT"
echo "  API docs:     $ENDPOINT/docs"
echo ""
echo -e "${BOLD}Quick start:${NC}"
echo "  /clarke          — system dashboard"
echo "  /clarke-teach    — record decisions and corrections"
echo "  /clarke-recall   — query CLARKE's memory"
echo "  /clarke-review   — approve self-improvement proposals"
echo ""
echo -e "${BOLD}Manage CLARKE:${NC}"
echo "  cd $INSTALL_DIR"
echo "  source .venv/bin/activate"
echo "  make dev         — restart services"
echo "  make test        — run tests"
echo ""
if [[ -f "$INSTALL_DIR/.clarke.pid" ]]; then
    echo -e "${BOLD}Stop CLARKE:${NC}"
    echo "  kill \$(cat $INSTALL_DIR/.clarke.pid)"
    echo "  cd $INSTALL_DIR && docker compose down"
    echo ""
fi
echo -e "License: Polyform Noncommercial 1.0.0"
echo -e "Enterprise: ${BLUE}nick@neill.cloud${NC}"
echo ""
