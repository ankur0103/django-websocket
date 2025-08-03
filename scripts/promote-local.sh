#!/bin/bash

set -euo pipefail

# Local blue-green deployment script (without Docker)
# This script demonstrates the blue-green concept using development servers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BLUE_PORT=8000
GREEN_PORT=8001
ACTIVE_PORT_FILE="$PROJECT_DIR/.active_port"

# Logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Function to get current active port
get_active_port() {
    if [ -f "$ACTIVE_PORT_FILE" ]; then
        cat "$ACTIVE_PORT_FILE"
    else
        echo "$BLUE_PORT"  # Default to blue
    fi
}

# Function to get current active color
get_active_color() {
    local port=$(get_active_port)
    if [ "$port" = "$BLUE_PORT" ]; then
        echo "blue"
    else
        echo "green"
    fi
}

# Function to get next color
get_next_color() {
    local current_color=$(get_active_color)
    if [ "$current_color" = "blue" ]; then
        echo "green"
    else
        echo "blue"
    fi
}

# Function to get port for color
get_port_for_color() {
    local color=$1
    if [ "$color" = "blue" ]; then
        echo "$BLUE_PORT"
    else
        echo "$GREEN_PORT"
    fi
}

# Function to check if service is healthy
check_service_health() {
    local port=$1
    local max_attempts=30
    local attempt=1
    
    log "Checking health of service on port $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f "http://localhost:$port/healthz" >/dev/null 2>&1; then
            log "Service on port $port is healthy"
            return 0
        fi
        
        warn "Service on port $port health check failed (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    error "Service on port $port failed health checks after $max_attempts attempts"
}

# Function to run smoke tests
run_smoke_tests() {
    local port=$1
    log "Running smoke tests against service on port $port..."
    
    # Test health endpoint
    if ! curl -f "http://localhost:$port/healthz" >/dev/null 2>&1; then
        error "Health check failed for service on port $port"
    fi
    
    # Test readiness endpoint
    if ! curl -f "http://localhost:$port/readyz" >/dev/null 2>&1; then
        error "Readiness check failed for service on port $port"
    fi
    
    # Test metrics endpoint
    if ! curl -f "http://localhost:$port/metrics" >/dev/null 2>&1; then
        error "Metrics endpoint failed for service on port $port"
    fi
    
    # Test WebSocket endpoint (basic connectivity - should return 404 for GET, which is expected)
    response=$(curl -s -w "%{http_code}" "http://localhost:$port/ws/chat/")
    http_code="${response: -3}"
    if [ "$http_code" != "404" ]; then
        error "WebSocket endpoint not accessible on port $port (expected 404, got $http_code)"
    fi
    
    log "Smoke tests passed for service on port $port"
}

# Function to start service
start_service() {
    local color=$1
    local port=$2
    
    log "Starting $color service on port $port..."
    
    # Set environment variables
    export COLOR=$color
    export WS_BASE_URL="ws://localhost:$port/ws"
    
    # Start the service in background
    cd "$PROJECT_DIR/app"
    uvicorn app.asgi:application --host 0.0.0.0 --port $port &
    local pid=$!
    
    # Save PID to file
    echo $pid > "$PROJECT_DIR/.${color}_pid"
    
    log "$color service started with PID $pid on port $port"
}

# Function to stop service
stop_service() {
    local color=$1
    
    log "Stopping $color service..."
    
    local pid_file="$PROJECT_DIR/.${color}_pid"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            # Send SIGTERM for graceful shutdown
            kill -TERM $pid
            
            # Wait for graceful shutdown
            local timeout=15
            local elapsed=0
            
            while [ $elapsed -lt $timeout ]; do
                if ! kill -0 $pid 2>/dev/null; then
                    log "$color service stopped gracefully"
                    rm -f "$pid_file"
                    return 0
                fi
                sleep 1
                ((elapsed++))
            done
            
            warn "$color service did not stop gracefully, forcing shutdown"
            kill -KILL $pid
            rm -f "$pid_file"
        else
            log "$color service already stopped"
            rm -f "$pid_file"
        fi
    else
        log "$color service not running"
    fi
}

# Function to switch traffic
switch_traffic() {
    local next_color=$1
    local next_port=$(get_port_for_color $next_color)
    
    log "Switching traffic to $next_color service on port $next_port..."
    
    # Update active port file
    echo "$next_port" > "$ACTIVE_PORT_FILE"
    
    log "Traffic switched to $next_color service on port $next_port"
    log "Access the application at: http://localhost:$next_port"
}

# Main deployment logic
main() {
    log "Starting local blue-green deployment..."
    
    # Get current and next colors
    local current_color=$(get_active_color)
    local next_color=$(get_next_color)
    local current_port=$(get_active_port)
    local next_port=$(get_port_for_color $next_color)
    
    log "Current active color: $current_color (port $current_port)"
    log "Promoting to color: $next_color (port $next_port)"
    
    # Step 1: Start the next color
    start_service "$next_color" "$next_port"
    
    # Step 2: Wait for service to be healthy
    check_service_health "$next_port"
    
    # Step 3: Run smoke tests
    run_smoke_tests "$next_port"
    
    # Step 4: Switch traffic
    switch_traffic "$next_color"
    
    # Step 5: Verify new service is handling traffic
    log "Verifying $next_color service is handling traffic..."
    sleep 5
    run_smoke_tests "$next_port"
    
    # Step 6: Stop old service
    stop_service "$current_color"
    
    log "Local blue-green deployment completed successfully!"
    log "Active color: $next_color (port $next_port)"
    log "Previous color: $current_color (stopped)"
    log ""
    log "Access points:"
    log "  - Application: http://localhost:$next_port"
    log "  - Health: http://localhost:$next_port/healthz"
    log "  - Metrics: http://localhost:$next_port/metrics"
    log "  - WebSocket: ws://localhost:$next_port/ws/chat/"
}

# Handle script arguments
case "${1:-}" in
    "status")
        echo "Current active color: $(get_active_color) (port $(get_active_port))"
        echo "Next color to promote: $(get_next_color)"
        echo ""
        echo "Service status:"
        if [ -f "$PROJECT_DIR/.blue_pid" ]; then
            pid=$(cat "$PROJECT_DIR/.blue_pid")
            if kill -0 $pid 2>/dev/null; then
                echo "  Blue: Running (PID $pid)"
            else
                echo "  Blue: Stopped"
            fi
        else
            echo "  Blue: Not started"
        fi
        
        if [ -f "$PROJECT_DIR/.green_pid" ]; then
            pid=$(cat "$PROJECT_DIR/.green_pid")
            if kill -0 $pid 2>/dev/null; then
                echo "  Green: Running (PID $pid)"
            else
                echo "  Green: Stopped"
            fi
        else
            echo "  Green: Not started"
        fi
        ;;
    "stop")
        stop_service "blue"
        stop_service "green"
        rm -f "$ACTIVE_PORT_FILE"
        log "All services stopped"
        ;;
    "start-blue")
        start_service "blue" "$BLUE_PORT"
        echo "$BLUE_PORT" > "$ACTIVE_PORT_FILE"
        log "Blue service started and set as active"
        ;;
    "start-green")
        start_service "green" "$GREEN_PORT"
        echo "$GREEN_PORT" > "$ACTIVE_PORT_FILE"
        log "Green service started and set as active"
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [status|stop|start-blue|start-green|help]"
        echo ""
        echo "Commands:"
        echo "  (no args)  - Perform blue-green deployment"
        echo "  status     - Show current deployment status"
        echo "  stop       - Stop all services"
        echo "  start-blue - Start blue service only"
        echo "  start-green- Start green service only"
        echo "  help       - Show this help message"
        ;;
    "")
        main
        ;;
    *)
        error "Unknown argument: $1"
        ;;
esac 