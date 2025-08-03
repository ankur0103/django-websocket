#!/bin/bash

set -euo pipefail

# Monitoring script for the Django WebSocket service
# Tails container logs for ERROR messages and prints top-5 metrics every 10 seconds

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOCKER_COMPOSE_FILE="$PROJECT_DIR/docker/compose.yml"
METRICS_URL="http://localhost/metrics"
LOG_TAIL_LINES=100

# Logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Function to get top 5 metrics
get_top_metrics() {
    local metrics_data
    if metrics_data=$(curl -s "$METRICS_URL" 2>/dev/null); then
        echo "=== Top 5 Metrics ==="
        echo "$metrics_data" | grep -E '^(websocket_|http_|app_)' | head -5
        echo ""
    else
        warn "Failed to fetch metrics from $METRICS_URL"
    fi
}

# Function to get active connections
get_active_connections() {
    local blue_connections=0
    local green_connections=0
    
    if curl -s "http://localhost/status" >/dev/null 2>&1; then
        blue_connections=$(curl -s "http://localhost/status" | jq -r '.active_connections // 0' 2>/dev/null || echo "0")
        echo "Active connections: $blue_connections"
    else
        echo "Active connections: unknown"
    fi
}

# Function to check service health
check_service_health() {
    local health_status
    local ready_status
    
    if health_status=$(curl -s "http://localhost/healthz" 2>/dev/null); then
        echo "Health: $(echo "$health_status" | jq -r '.status // "unknown"')"
    else
        echo "Health: failed"
    fi
    
    if ready_status=$(curl -s "http://localhost/readyz" 2>/dev/null); then
        echo "Ready: $(echo "$ready_status" | jq -r '.status // "unknown"')"
    else
        echo "Ready: failed"
    fi
}

# Function to tail logs for errors
tail_error_logs() {
    log "Tailing logs for ERROR messages..."
    
    # Start background process to tail logs
    docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f --tail="$LOG_TAIL_LINES" | \
    while IFS= read -r line; do
        if echo "$line" | grep -q "ERROR"; then
            error "LOG ERROR: $line"
        fi
    done &
    
    local tail_pid=$!
    trap "kill $tail_pid 2>/dev/null" EXIT
}

# Function to monitor metrics
monitor_metrics() {
    local interval=${1:-10}
    local duration=${2:-0}
    local start_time=$(date +%s)
    
    log "Starting metrics monitoring (interval: ${interval}s)"
    
    while true; do
        # Check if duration limit reached
        if [ $duration -gt 0 ]; then
            local current_time=$(date +%s)
            local elapsed=$((current_time - start_time))
            if [ $elapsed -ge $duration ]; then
                log "Monitoring duration reached ($duration seconds)"
                break
            fi
        fi
        
        echo "=== $(date) ==="
        check_service_health
        get_active_connections
        get_top_metrics
        echo "=================="
        echo ""
        
        sleep "$interval"
    done
}

# Function to show current deployment status
show_deployment_status() {
    log "Current deployment status:"
    
    # Check which services are running
    local blue_status="stopped"
    local green_status="stopped"
    
    if docker-compose -f "$DOCKER_COMPOSE_FILE" ps app_blue | grep -q "Up"; then
        blue_status="running"
    fi
    
    if docker-compose -f "$DOCKER_COMPOSE_FILE" ps app_green | grep -q "Up"; then
        green_status="running"
    fi
    
    echo "app_blue: $blue_status"
    echo "app_green: $green_status"
    
    # Check nginx configuration
    local active_color
    if grep -q "server app_blue:8000" "$PROJECT_DIR/docker/nginx/nginx.conf"; then
        active_color="blue"
    else
        active_color="green"
    fi
    
    echo "Active color: $active_color"
    echo ""
}

# Main monitoring logic
main() {
    local monitor_only=false
    local log_only=false
    local interval=10
    local duration=0
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --metrics-only)
                monitor_only=true
                shift
                ;;
            --logs-only)
                log_only=true
                shift
                ;;
            --interval)
                interval="$2"
                shift 2
                ;;
            --duration)
                duration="$2"
                shift 2
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --metrics-only    Only monitor metrics, don't tail logs"
                echo "  --logs-only       Only tail logs, don't monitor metrics"
                echo "  --interval SEC    Metrics check interval in seconds (default: 10)"
                echo "  --duration SEC    Stop monitoring after SEC seconds (default: run forever)"
                echo "  --help, -h        Show this help message"
                echo ""
                echo "Examples:"
                echo "  $0                    # Monitor everything"
                echo "  $0 --metrics-only     # Only metrics"
                echo "  $0 --interval 5       # Check metrics every 5 seconds"
                echo "  $0 --duration 60      # Monitor for 60 seconds"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    log "Starting monitoring for Django WebSocket service..."
    
    # Show initial status
    show_deployment_status
    
    # Start log tailing if not metrics-only
    if [ "$monitor_only" = false ]; then
        tail_error_logs
    fi
    
    # Start metrics monitoring if not logs-only
    if [ "$log_only" = false ]; then
        monitor_metrics "$interval" "$duration"
    fi
    
    # If logs-only, keep the script running
    if [ "$log_only" = true ]; then
        log "Tailing logs only. Press Ctrl+C to stop."
        wait
    fi
}

# Handle script interruption
trap 'log "Monitoring stopped"; exit 0' INT TERM

# Run main function
main "$@" 