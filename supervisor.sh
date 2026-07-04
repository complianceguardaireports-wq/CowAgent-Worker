#!/bin/bash

# CowAgent-Worker Supervisor Script
# Manages all services: OmniRoute, 9Router, OpenHands, CowAgent

set -e

# ============================================================
# Configuration
# ============================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
PID_DIR="$PROJECT_DIR/pids"

# Service definitions: name, port, command, working_dir
declare -A SERVICE_PORTS
declare -A SERVICE_COMMANDS
declare -A SERVICE_DIRS

# Unique ports - no conflicts
SERVICE_PORTS[omniroute]=3000
SERVICE_PORTS[9router]=8081
SERVICE_PORTS[openhands]=3001
SERVICE_PORTS[cowagent]=8080

SERVICE_COMMANDS[omniroute]="node dev/run-standalone.mjs"
SERVICE_COMMANDS[9router]="node custom-server.js"
SERVICE_COMMANDS[openhands]="python -m openhands --port 3001"
SERVICE_COMMANDS[cowagent]="python app.py"

SERVICE_DIRS[omniroute]="$PROJECT_DIR/omniroute"
SERVICE_DIRS[9router]="$PROJECT_DIR/9router"
SERVICE_DIRS[openhands]="$PROJECT_DIR/openhands"
SERVICE_DIRS[cowagent]="$PROJECT_DIR/cowagent"

# ============================================================
# Setup
# ============================================================

mkdir -p "$LOG_DIR" "$PID_DIR"

# ============================================================
# Functions
# ============================================================

log() {
    local service=$1
    local message=$2
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$service] $message" | tee -a "$LOG_DIR/supervisor.log"
}

start_service() {
    local service=$1
    local port=${SERVICE_PORTS[$service]}
    local command=${SERVICE_COMMANDS[$service]}
    local dir=${SERVICE_DIRS[$service]}

    # Check if already running
    if [ -f "$PID_DIR/$service.pid" ]; then
        local pid=$(cat "$PID_DIR/$service.pid")
        if kill -0 "$pid" 2>/dev/null; then
            log "$service" "Already running (PID: $pid)"
            return 0
        fi
        rm -f "$PID_DIR/$service.pid"
    fi

    # Check if port is in use
    if lsof -Pi ":$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
        log "$service" "ERROR: Port $port is already in use"
        return 1
    fi

    log "$service" "Starting on port $port..."

    # Start the service
    cd "$dir"
    nohup $command > "$LOG_DIR/$service.log" 2>&1 &
    local pid=$!
    echo $pid > "$PID_DIR/$service.pid"

    log "$service" "Started (PID: $pid, Port: $port)"
}

stop_service() {
    local service=$1

    if [ ! -f "$PID_DIR/$service.pid" ]; then
        log "$service" "Not running"
        return 0
    fi

    local pid=$(cat "$PID_DIR/$service.pid")
    if kill -0 "$pid" 2>/dev/null; then
        log "$service" "Stopping (PID: $pid)..."
        kill "$pid"
        sleep 2
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid"
        fi
        log "$service" "Stopped"
    fi
    rm -f "$PID_DIR/$service.pid"
}

health_check() {
    local service=$1
    local port=${SERVICE_PORTS[$service]}

    if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        log "$service" "Health check passed"
        return 0
    elif curl -s "http://localhost:$port/" > /dev/null 2>&1; then
        log "$service" "Health check passed (root endpoint)"
        return 0
    else
        log "$service" "Health check failed"
        return 1
    fi
}

show_status() {
    echo "============================================"
    echo "CowAgent-Worker Service Status"
    echo "============================================"
    for service in omniroute 9router openhands cowagent; do
        local port=${SERVICE_PORTS[$service]}
        local status="STOPPED"
        local pid="-"

        if [ -f "$PID_DIR/$service.pid" ]; then
            local pid_val=$(cat "$PID_DIR/$service.pid")
            if kill -0 "$pid_val" 2>/dev/null; then
                status="RUNNING"
                pid=$pid_val
            fi
        fi

        printf "%-12s | Port: %-5s | PID: %-8s | %s\n" "$service" "$port" "$pid" "$status"
    done
    echo "============================================"
}

# ============================================================
# Main
# ============================================================

case "${1:-}" in
    start)
        log "supervisor" "Starting all services..."
        start_service omniroute
        start_service 9router
        start_service openhands
        start_service cowagent
        log "supervisor" "All services started"
        show_status
        ;;
    stop)
        log "supervisor" "Stopping all services..."
        stop_service cowagent
        stop_service openhands
        stop_service 9router
        stop_service omniroute
        log "supervisor" "All services stopped"
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        show_status
        ;;
    health)
        echo "Running health checks..."
        health_check omniroute
        health_check 9router
        health_check openhands
        health_check cowagent
        ;;
    logs)
        local_service=${2:-supervisor}
        tail -f "$LOG_DIR/$local_service.log"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|health|logs [service]}"
        echo ""
        echo "Services:"
        echo "  omniroute  - Port 3000"
        echo "  9router    - Port 8081"
        echo "  openhands  - Port 3001"
        echo "  cowagent   - Port 8080"
        exit 1
        ;;
esac
