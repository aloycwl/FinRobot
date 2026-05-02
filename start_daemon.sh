#!/bin/bash
# ============================================================================
# Trading Daemon Startup Script - IMPROVED VERSION
# ============================================================================
# This script starts the trading daemon with proper error handling,
# automatic restart, and health monitoring.
# ============================================================================

set -euo pipefail

# Configuration
PROJECT_DIR="/home/openclaw/FinRobot"
DAEMON_SCRIPT="daemon_service.py"
PID_FILE="${PROJECT_DIR}/daemon.pid"
LOG_FILE="${PROJECT_DIR}/trading_daemon.log"
ERROR_LOG="${PROJECT_DIR}/daemon_errors.log"
MAX_RESTARTS=10
RESTART_DELAY=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi
    
    # Check for required packages
    python3 -c "import psutil, pandas, numpy" 2>/dev/null || {
        log_warn "Installing required packages..."
        pip3 install psutil pandas numpy --quiet
    }
}

is_daemon_running() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$pid" ] && [ -d "/proc/$pid" ]; then
            return 0  # Running
        fi
    fi
    return 1  # Not running
}

get_daemon_status() {
    if is_daemon_running; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null)
        
        # Get memory and CPU info
        local mem_cpu
        mem_cpu=$(ps -p "$pid" -o %mem,%cpu 2>/dev/null | tail -1 || echo "N/A")
        
        log_info "Daemon is RUNNING (PID: $pid)"
        log_info "Resource usage: $mem_cpu"
        
        # Show recent log
        if [ -f "$LOG_FILE" ]; then
            log_info "Recent activity:"
            tail -3 "$LOG_FILE" | sed 's/^/  /'
        fi
    else
        log_warn "Daemon is NOT running"
        
        # Check for stale PID file
        if [ -f "$PID_FILE" ]; then
            log_warn "Stale PID file detected, removing..."
            rm -f "$PID_FILE"
        fi
    fi
}

start_daemon() {
    if is_daemon_running; then
        log_warn "Daemon is already running"
        get_daemon_status
        return 0
    fi
    
    log_info "Starting trading daemon..."
    
    # Change to project directory
    cd "$PROJECT_DIR"
    
    # Start daemon in background
    nohup python3 "$DAEMON_SCRIPT" start >> "$LOG_FILE" 2>&1 &
    
    # Wait a moment and check if it started
    sleep 2
    
    if is_daemon_running; then
        log_info "Daemon started successfully"
        get_daemon_status
        return 0
    else
        log_error "Failed to start daemon"
        if [ -f "$LOG_FILE" ]; then
            log_error "Recent log entries:"
            tail -10 "$LOG_FILE" | sed 's/^/  /'
        fi
        return 1
    fi
}

stop_daemon() {
    if ! is_daemon_running; then
        log_warn "Daemon is not running"
        
        # Clean up stale PID file
        if [ -f "$PID_FILE" ]; then
            rm -f "$PID_FILE"
            log_info "Removed stale PID file"
        fi
        return 0
    fi
    
    local pid
    pid=$(cat "$PID_FILE" 2>/dev/null)
    
    log_info "Stopping daemon (PID: $pid)..."
    
    # Try graceful shutdown first
    kill "$pid" 2>/dev/null || true
    
    # Wait for process to stop
    local count=0
    while [ -d "/proc/$pid" ] && [ $count -lt 10 ]; do
        sleep 1
        count=$((count + 1))
    done
    
    # Force kill if still running
    if [ -d "/proc/$pid" ]; then
        log_warn "Force killing daemon..."
        kill -9 "$pid" 2>/dev/null || true
    fi
    
    # Clean up PID file
    rm -f "$PID_FILE"
    
    log_info "Daemon stopped"
    return 0
}

restart_daemon() {
    log_info "Restarting daemon..."
    stop_daemon
    sleep 2
    start_daemon
}

run_monitor() {
    log_info "Starting daemon monitor (auto-restart enabled)..."
    
    local restart_count=0
    
    while true; do
        if ! is_daemon_running; then
            if [ $restart_count -lt $MAX_RESTARTS ]; then
                restart_count=$((restart_count + 1))
                log_warn "Daemon not running, restarting (attempt $restart_count/$MAX_RESTARTS)..."
                start_daemon
                sleep 5
            else
                log_error "Max restarts ($MAX_RESTARTS) reached, giving up."
                exit 1
            fi
        else
            # Reset restart count on successful check
            if [ $restart_count -gt 0 ]; then
                restart_count=0
                log_info "Daemon is stable again"
            fi
        fi
        
        # Check every 30 seconds
        sleep 30
    done
}

show_logs() {
    if [ -f "$LOG_FILE" ]; then
        log_info "Showing recent logs (Ctrl+C to exit)..."
        tail -f "$LOG_FILE"
    else
        log_error "Log file not found: $LOG_FILE"
    fi
}

# ============================================================================
# Main Script
# ============================================================================

case "${1:-}" in
    start)
        check_python
        start_daemon
        ;;
    stop)
        stop_daemon
        ;;
    restart)
        check_python
        restart_daemon
        ;;
    status)
        get_daemon_status
        ;;
    monitor)
        check_python
        run_monitor
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "Trading Daemon Management Script (IMPROVED VERSION)"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|monitor|logs}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the trading daemon"
        echo "  stop     - Stop the trading daemon"
        echo "  restart  - Restart the trading daemon"
        echo "  status   - Show daemon status and health"
        echo "  monitor  - Monitor daemon and auto-restart if needed"
        echo "  logs     - View daemon logs in real-time"
        echo ""
        exit 1
        ;;
esac
