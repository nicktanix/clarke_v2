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
check_cmd python3 || MISSING=1
check_cmd docker  || MISSING=1
check_cmd git     || MISSING=1

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

# Check Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [[ "$PYTHON_MAJOR" -lt 3 ]] || [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -lt 12 ]]; then
    err "Python 3.12+ required (found $PYTHON_VERSION)"
    MISSING=1
else
    ok "Python $PYTHON_VERSION"
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
    info "Creating virtual environment..."
    python3 -m venv .venv
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
