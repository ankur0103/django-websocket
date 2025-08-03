#!/bin/bash

set -euo pipefail

# Blue-green deployment script
# This script promotes the next color (blue/green) to active

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
NGINX_CONF="$PROJECT_DIR/docker/nginx/nginx.conf"
BACKUP_DIR="$PROJECT_DIR/backups"

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

# Function to get current active color
get_active_color() {
    if grep -q "server app_blue:8000" "$NGINX_CONF"; then
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

# Function to check if service is healthy
check_service_health() {
    local color=$1
    local max_attempts=30
    local attempt=1
    
    log "Checking health of app_$color..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker compose -f "$DOCKER_COMPOSE_FILE" exec -T "app_$color" curl -f http://localhost:8000/healthz >/dev/null 2>&1; then
            log "app_$color is healthy"
            return 0
        fi
        
        warn "app_$color health check failed (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    error "app_$color failed health checks after $max_attempts attempts"
}

# Function to run smoke tests
run_smoke_tests() {
    local color=$1
    log "Running smoke tests against app_$color..."
    
    # Test health endpoint
    if ! curl -f "http://localhost/healthz" >/dev/null 2>&1; then
        error "Health check failed for app_$color"
    fi
    
    # Test readiness endpoint
    if ! curl -f "http://localhost/readyz" >/dev/null 2>&1; then
        error "Readiness check failed for app_$color"
    fi
    
    # Test metrics endpoint
    if ! curl -f "http://localhost/metrics" >/dev/null 2>&1; then
        error "Metrics endpoint failed for app_$color"
    fi
    
    # Test WebSocket endpoint (smoke test)
    if command -v python >/dev/null 2>&1; then
        log "Testing WebSocket connection..."
        if ! python "$SCRIPT_DIR/test_websocket.py" --mode smoke >/dev/null 2>&1; then
            error "WebSocket connection failed for app_$color"
        fi
        log "WebSocket connection test passed"
    else
        warn "python not found, skipping WebSocket test"
    fi
    
    log "Smoke tests passed for app_$color"
}

# Function to switch traffic
switch_traffic() {
    local next_color=$1
    
    log "Switching traffic to app_$next_color..."
    
    # Create backup
    mkdir -p "$BACKUP_DIR"
    cp "$NGINX_CONF" "$BACKUP_DIR/nginx.conf.$(date +%Y%m%d_%H%M%S)"
    
    # Clean up old backups (keep only last 5)
    cleanup_old_backups() {
        local backup_dir="$1"
        local max_backups=5
        
        # Remove old backups, keeping only the most recent ones
        if [ -d "$backup_dir" ]; then
            cd "$backup_dir"
            ls -t nginx.conf.* 2>/dev/null | tail -n +$((max_backups + 1)) | xargs -r rm -f
            cd - > /dev/null
        fi
    }
    
    cleanup_old_backups "$BACKUP_DIR"
    
    # Update nginx configuration using the new switch_traffic script
    "$SCRIPT_DIR/switch_traffic.sh" "$next_color"
    
    # Reload nginx
    docker compose -f "$DOCKER_COMPOSE_FILE" exec nginx nginx -s reload
    
    log "Traffic switched to app_$next_color"
}

# Function to stop old service
stop_old_service() {
    local old_color=$1
    
    log "Stopping app_$old_color..."
    
    # Send SIGTERM for graceful shutdown
    docker compose -f "$DOCKER_COMPOSE_FILE" stop "app_$old_color"
    
    # Wait for graceful shutdown
    local timeout=15
    local elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        if ! docker compose -f "$DOCKER_COMPOSE_FILE" ps "app_$old_color" | grep -q "Up"; then
            log "app_$old_color stopped gracefully"
            return 0
        fi
        sleep 1
        ((elapsed++))
    done
    
    warn "app_$old_color did not stop gracefully, forcing shutdown"
    docker compose -f "$DOCKER_COMPOSE_FILE" kill "app_$old_color"
}

# Main deployment logic
main() {
    log "Starting blue-green deployment..."
    
    # Get current and next colors
    local current_color=$(get_active_color)
    local next_color=$(get_next_color)
    
    log "Current active color: $current_color"
    log "Promoting to color: $next_color"
    
    # Step 1: Build and start the next color
    log "Building and starting app_$next_color..."
    docker compose -f "$DOCKER_COMPOSE_FILE" up -d --build "app_$next_color"
    
    # Step 2: Wait for service to be healthy
    check_service_health "$next_color"
    
    # Step 3: Switch traffic first
    switch_traffic "$next_color"
    
    # Step 4: Run smoke tests against the new active environment
    log "Running smoke tests against active environment..."
    sleep 5
    run_smoke_tests "$next_color"
    
    log "Blue-green deployment completed successfully!"
    log "Active color: $next_color"
    log "Previous color: $current_color (still running for rollback safety)"
    log ""
    log "IMPORTANT: The old environment is still running for rollback safety."
    log "To stop the old environment after confirming stability, run:"
    log "  make stop-old"
}

# Handle script arguments
case "${1:-}" in
    "status")
        echo "Current active color: $(get_active_color)"
        echo "Next color to promote: $(get_next_color)"
        ;;
    "rollback")
        error "Rollback functionality not implemented yet"
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [status|rollback|help]"
        echo ""
        echo "Commands:"
        echo "  (no args)  - Perform blue-green deployment"
        echo "  status     - Show current deployment status"
        echo "  rollback   - Rollback to previous deployment"
        echo "  help       - Show this help message"
        ;;
    "")
        main
        ;;
    *)
        error "Unknown argument: $1"
        ;;
esac 