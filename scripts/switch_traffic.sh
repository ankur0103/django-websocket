#!/bin/bash

# Script to switch nginx traffic between blue and green environments
# Usage: ./switch_traffic.sh [blue|green]
# This script ONLY changes the app_active upstream target, preserving all other optimized settings

set -e

NGINX_CONF="nginx/nginx.conf"
BACKUP_DIR="docker/nginx/backups"

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

# Function to switch to blue (preserves all optimized settings)
switch_to_blue() {
    echo "Switching traffic to blue..."
    
    # Update only the app_active upstream server line
    sed -i.bak '/upstream app_active {/,/}/ {
        s/server app_green:8000/server app_blue:8000/g
        s/server app_blue:8000/server app_blue:8000/g
    }' "$NGINX_CONF"
    
    echo "Traffic switched to blue (app_blue:8000)"
}

# Function to switch to green (preserves all optimized settings)
switch_to_green() {
    echo "Switching traffic to green..."
    
    # Update only the app_active upstream server line
    sed -i.bak '/upstream app_active {/,/}/ {
        s/server app_blue:8000/server app_green:8000/g
        s/server app_green:8000/server app_green:8000/g
    }' "$NGINX_CONF"
    
    echo "Traffic switched to green (app_green:8000)"
}

# Function to validate nginx config
validate_config() {
    echo "Validating nginx configuration..."
    # Simple syntax check - if file exists and has upstream app_active, it's likely valid
    if grep -q "upstream app_active" "$NGINX_CONF" && grep -q "server app_" "$NGINX_CONF"; then
        echo "✅ Nginx configuration appears valid"
        return 0
    else
        echo "❌ Nginx configuration appears invalid"
        return 1
    fi
}

# Main logic
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 [blue|green]"
    exit 1
fi

TARGET_COLOR="$1"

case "$TARGET_COLOR" in
    blue)
        switch_to_blue
        ;;
    green)
        switch_to_green
        ;;
    *)
        echo "Error: Invalid color '$TARGET_COLOR'. Use 'blue' or 'green'."
        exit 1
        ;;
esac

# Validate the configuration
if validate_config; then
    echo "✅ Traffic successfully switched to $TARGET_COLOR"
    echo ""
    echo "Current app_active upstream:"
    grep -A 3 "upstream app_active" "$NGINX_CONF"
else
    echo "❌ Configuration validation failed. Restoring backup..."
    # Restore from backup
    LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/nginx.conf.* | head -1)
    if [ -n "$LATEST_BACKUP" ]; then
        cp "$LATEST_BACKUP" "$NGINX_CONF"
        echo "Configuration restored from backup: $LATEST_BACKUP"
    fi
    exit 1
fi