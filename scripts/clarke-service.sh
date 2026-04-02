#!/usr/bin/env bash
#
# CLARKE service manager
#
# Usage:
#   clarke start        Start CLARKE (API + Docker services)
#   clarke stop         Stop CLARKE API server
#   clarke restart      Restart CLARKE API server
#   clarke status       Show service status
#   clarke logs         Tail API logs
#   clarke install-systemd   Install as systemd user service
#
# Environment:
#   CLARKE_HOME         CLARKE install directory (default: ~/.clarke)
#   CLARKE_PORT         API port (default: 8000)

set -euo pipefail

CLARKE_HOME="${CLARKE_HOME:-$HOME/.clarke}"
CLARKE_PORT="${CLARKE_PORT:-8000}"
PID_FILE="$CLARKE_HOME/.clarke.pid"
LOG_FILE="/tmp/clarke-api.log"
VENV_PYTHON="$CLARKE_HOME/.venv/bin/python"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

_get_pid() {
    local pid=""
    if [[ -f "$PID_FILE" ]]; then
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "$pid"
            return 0
        fi
        rm -f "$PID_FILE"
    fi
    # Fallback: find by port
    if command -v lsof &>/dev/null; then
        pid=$(lsof -ti ":$CLARKE_PORT" 2>/dev/null || true)
        echo "$pid"
        return 0
    fi
    echo ""
}

_is_running() {
    local pid
    pid=$(_get_pid)
    [[ -n "$pid" ]]
}

_docker_running() {
    cd "$CLARKE_HOME"
    docker compose ps --format "{{.Status}}" 2>/dev/null | grep -qi "up\|healthy" 2>/dev/null
}

cmd_start() {
    if _is_running; then
        echo -e "${YELLOW}CLARKE already running (PID $(_get_pid))${NC}"
        return 0
    fi

    echo -e "${GREEN}Starting CLARKE...${NC}"

    # Start Docker services if not running
    if ! _docker_running; then
        echo "  Starting Docker services..."
        cd "$CLARKE_HOME"
        docker compose up -d 2>&1 | grep -v "^$" | sed 's/^/  /'
        echo "  Waiting for health checks..."
        for _ in $(seq 1 30); do
            if _docker_running; then break; fi
            sleep 2
        done
    else
        echo "  Docker services already running"
    fi

    # Run migrations
    echo "  Running migrations..."
    cd "$CLARKE_HOME"
    "$VENV_PYTHON" -m alembic upgrade head 2>&1 | grep -E "Running|already" | sed 's/^/  /' || true

    # Start API server
    echo "  Starting API server on port $CLARKE_PORT..."
    cd "$CLARKE_HOME"
    setsid "$VENV_PYTHON" -m uvicorn clarke.api.app:create_app \
        --factory --host 0.0.0.0 --port "$CLARKE_PORT" \
        >> "$LOG_FILE" 2>&1 &
    disown
    echo $! > "$PID_FILE"

    # Wait for health
    for _ in $(seq 1 15); do
        if curl -sf "http://localhost:$CLARKE_PORT/health" &>/dev/null; then
            echo -e "${GREEN}CLARKE is running (PID $(cat "$PID_FILE"), port $CLARKE_PORT)${NC}"
            return 0
        fi
        sleep 1
    done

    echo -e "${RED}CLARKE failed to start. Check: $LOG_FILE${NC}"
    return 1
}

cmd_stop() {
    local pid
    pid=$(_get_pid)

    if [[ -z "$pid" ]]; then
        echo "CLARKE is not running"
        rm -f "$PID_FILE"
        return 0
    fi

    echo -e "Stopping CLARKE (PID $pid)..."
    kill "$pid" 2>/dev/null || true

    # Wait for shutdown
    for _ in $(seq 1 10); do
        if ! kill -0 "$pid" 2>/dev/null; then
            rm -f "$PID_FILE"
            echo -e "${GREEN}CLARKE stopped${NC}"
            return 0
        fi
        sleep 1
    done

    # Force kill
    kill -9 "$pid" 2>/dev/null || true
    rm -f "$PID_FILE"
    echo -e "${YELLOW}CLARKE force-killed${NC}"
}

cmd_restart() {
    cmd_stop
    sleep 1
    cmd_start
}

cmd_status() {
    local pid
    pid=$(_get_pid)

    if [[ -n "$pid" ]]; then
        echo -e "${GREEN}CLARKE API:    running (PID $pid, port $CLARKE_PORT)${NC}"
    else
        echo -e "${RED}CLARKE API:    stopped${NC}"
    fi

    if _docker_running; then
        echo -e "${GREEN}Docker:        running${NC}"
        cd "$CLARKE_HOME"
        docker compose ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null | sed 's/^/  /'
    else
        echo -e "${RED}Docker:        stopped${NC}"
    fi

    if curl -sf "http://localhost:$CLARKE_PORT/health" &>/dev/null; then
        local health
        health=$(curl -s "http://localhost:$CLARKE_PORT/health")
        echo -e "${GREEN}Health:        $(echo "$health" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'], '| v'+d.get('version','?'))" 2>/dev/null || echo "ok")${NC}"
    else
        echo -e "${RED}Health:        unreachable${NC}"
    fi

    echo "Log:           $LOG_FILE"
    echo "PID file:      $PID_FILE"
}

cmd_logs() {
    if [[ -f "$LOG_FILE" ]]; then
        tail -f "$LOG_FILE"
    else
        echo "No log file at $LOG_FILE"
    fi
}

cmd_docker_stop() {
    echo "Stopping Docker services..."
    cd "$CLARKE_HOME"
    docker compose down
    echo -e "${GREEN}Docker services stopped${NC}"
}

cmd_install_systemd() {
    local service_dir="$HOME/.config/systemd/user"
    mkdir -p "$service_dir"

    cat > "$service_dir/clarke.service" << UNIT
[Unit]
Description=CLARKE API Server
After=network.target docker.service

[Service]
Type=simple
WorkingDirectory=$CLARKE_HOME
ExecStartPre=$CLARKE_HOME/.venv/bin/python -m alembic upgrade head
ExecStart=$VENV_PYTHON -m uvicorn clarke.api.app:create_app --factory --host 0.0.0.0 --port $CLARKE_PORT
ExecStop=/bin/kill -TERM \$MAINPID
Restart=on-failure
RestartSec=5
Environment=PATH=$CLARKE_HOME/.venv/bin:/usr/local/bin:/usr/bin
EnvironmentFile=-$CLARKE_HOME/.env

[Install]
WantedBy=default.target
UNIT

    systemctl --user daemon-reload
    systemctl --user enable clarke.service

    echo -e "${GREEN}Installed systemd user service: clarke.service${NC}"
    echo ""
    echo "Usage:"
    echo "  systemctl --user start clarke     Start CLARKE"
    echo "  systemctl --user stop clarke      Stop CLARKE"
    echo "  systemctl --user restart clarke   Restart CLARKE"
    echo "  systemctl --user status clarke    Status"
    echo "  journalctl --user -u clarke -f    Follow logs"
    echo ""
    echo "To start now:"
    echo "  systemctl --user start clarke"
    echo ""
    echo "To auto-start on login:"
    echo "  loginctl enable-linger $(whoami)"
}

cmd_update() {
    echo -e "${GREEN}Updating CLARKE...${NC}"

    # Pull latest code
    cd "$CLARKE_HOME"
    info "Pulling latest..."
    git pull --ff-only origin main 2>&1 | sed 's/^/  /' || warn "Git pull failed — continuing with current version"

    # Rebuild Python
    info "Installing Python dependencies..."
    .venv/bin/pip install -e ".[dev]" --quiet 2>&1 | tail -1

    # Run migrations
    info "Running migrations..."
    "$VENV_PYTHON" -m alembic upgrade head 2>&1 | grep -E "Running|already" | sed 's/^/  /' || true

    # Rebuild TypeScript plugin
    if [[ -d "$CLARKE_HOME/openclaw" ]]; then
        info "Building OpenClaw plugin..."
        cd "$CLARKE_HOME/openclaw"
        npm install --quiet 2>&1 | tail -1
        npm run build 2>&1 | tail -1
    fi

    ok "Update complete"
    echo ""
    echo "Restart to apply: clarke restart"
}

cmd_plugin_sync() {
    local PLUGIN_SRC="$CLARKE_HOME/openclaw"
    local PLUGIN_DST="$HOME/.openclaw/extensions/openclaw-clarke"

    if [[ ! -d "$PLUGIN_SRC" ]]; then
        err "Plugin source not found at $PLUGIN_SRC"
        exit 1
    fi

    # Build first
    info "Building plugin..."
    cd "$PLUGIN_SRC"
    npm run build 2>&1 | tail -1

    if [[ ! -d "$PLUGIN_DST" ]]; then
        err "Plugin not installed. Run: openclaw plugins install openclaw-clarke"
        exit 1
    fi

    # Sync built files to installed location
    info "Syncing to $PLUGIN_DST..."
    cp -r "$PLUGIN_SRC/dist/"* "$PLUGIN_DST/dist/"
    cp "$PLUGIN_SRC/openclaw.plugin.json" "$PLUGIN_DST/"
    cp "$PLUGIN_SRC/package.json" "$PLUGIN_DST/"

    # Sync skills if present
    if [[ -d "$PLUGIN_SRC/skills" ]]; then
        cp -r "$PLUGIN_SRC/skills" "$PLUGIN_DST/"
    fi

    local version
    version=$(node -e "console.log(require('$PLUGIN_DST/package.json').version)" 2>/dev/null || echo "?")
    ok "Plugin synced (v$version)"
    echo ""
    echo "Restart OpenClaw to apply: openclaw gateway restart"
}

cmd_plugin_publish() {
    local PLUGIN_SRC="$CLARKE_HOME/openclaw"

    if [[ ! -d "$PLUGIN_SRC" ]]; then
        err "Plugin source not found at $PLUGIN_SRC"
        exit 1
    fi

    cd "$PLUGIN_SRC"
    info "Building..."
    npm run build 2>&1 | tail -1

    info "Publishing to npm..."
    npm publish 2>&1 | sed 's/^/  /'

    ok "Published. Install with: openclaw plugins install openclaw-clarke"
}

# ── Main ────────────────────────────────────────────────────────────

case "${1:-help}" in
    start)           cmd_start ;;
    stop)            cmd_stop ;;
    restart)         cmd_restart ;;
    status)          cmd_status ;;
    logs)            cmd_logs ;;
    update)          cmd_update ;;
    plugin-sync)     cmd_plugin_sync ;;
    plugin-publish)  cmd_plugin_publish ;;
    docker-stop)     cmd_docker_stop ;;
    install-systemd) cmd_install_systemd ;;
    help|--help|-h)
        echo "CLARKE service manager"
        echo ""
        echo "Usage: clarke <command>"
        echo ""
        echo "Commands:"
        echo "  start            Start CLARKE (Docker + API)"
        echo "  stop             Stop API server"
        echo "  restart          Restart API server"
        echo "  status           Show service status"
        echo "  logs             Tail API logs"
        echo "  update           Pull latest, rebuild, migrate"
        echo ""
        echo "OpenClaw Plugin:"
        echo "  plugin-sync      Build & sync plugin to OpenClaw extensions"
        echo "  plugin-publish   Build & publish plugin to npm"
        echo ""
        echo "Infrastructure:"
        echo "  docker-stop      Stop Docker services"
        echo "  install-systemd  Install as systemd user service"
        ;;
    *)
        echo "Unknown command: $1 (try: clarke help)"
        exit 1
        ;;
esac
