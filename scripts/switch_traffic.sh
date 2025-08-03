#!/bin/bash

# Script to switch nginx traffic between blue and green environments
# Usage: ./switch_traffic.sh [blue|green]

set -e

NGINX_CONF="docker/nginx/nginx.conf"
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

# Function to switch to blue
switch_to_blue() {
    echo "Switching traffic to blue..."
    
    # Create temporary file with blue configuration
    cat > "$NGINX_CONF" << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream app_blue {
        server app_blue:8000 max_fails=3 fail_timeout=30s;
    }

    # Default to blue
    upstream app_active {
        server app_blue:8000 max_fails=3 fail_timeout=30s;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=websocket:10m rate=100r/s;
    limit_req_zone $binary_remote_addr zone=api:10m rate=1000r/s;

    # Logging
    log_format json_combined escape=json '{'
        '"time_local":"$time_local",'
        '"remote_addr":"$remote_addr",'
        '"remote_user":"$remote_user",'
        '"request":"$request",'
        '"status": "$status",'
        '"body_bytes_sent":"$body_bytes_sent",'
        '"request_time":"$request_time",'
        '"http_referrer":"$http_referer",'
        '"http_user_agent":"$http_user_agent",'
        '"request_id":"$http_x_request_id"'
    '}';

    access_log /var/log/nginx/access.log json_combined;
    error_log /var/log/nginx/error.log;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    server {
        listen 80;
        server_name localhost;

        # Health check endpoint
        location /healthz {
            proxy_pass http://app_active;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Request-ID $http_x_request_id;
            access_log off;
        }

        # Readiness check endpoint
        location /readyz {
            proxy_pass http://app_active;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Request-ID $http_x_request_id;
            access_log off;
        }

        # Metrics endpoint
        location /metrics {
            proxy_pass http://app_active;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Request-ID $http_x_request_id;
            limit_req zone=api burst=10 nodelay;
        }

        # Status endpoint
        location /status {
            proxy_pass http://app_active;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Request-ID $http_x_request_id;
            limit_req zone=api burst=10 nodelay;
        }

        # WebSocket endpoint
        location /ws/ {
            proxy_pass http://app_active;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Request-ID $http_x_request_id;
            proxy_read_timeout 86400;
            proxy_send_timeout 86400;
            limit_req zone=websocket burst=20 nodelay;
        }

        # Admin interface
        location /admin/ {
            proxy_pass http://app_active;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Request-ID $http_x_request_id;
            limit_req zone=api burst=10 nodelay;
        }

        # Default location
        location / {
            proxy_pass http://app_active;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Request-ID $http_x_request_id;
            limit_req zone=api burst=10 nodelay;
        }
    }
}
EOF
}

# Function to switch to green
switch_to_green() {
    echo "Switching traffic to green..."
    
    # Create temporary file with green configuration
    cat > "$NGINX_CONF" << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream app_green {
        server app_green:8000 max_fails=3 fail_timeout=30s;
    }

    # Default to green
    upstream app_active {
        server app_green:8000 max_fails=3 fail_timeout=30s;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=websocket:10m rate=100r/s;
    limit_req_zone $binary_remote_addr zone=api:10m rate=1000r/s;

    # Logging
    log_format json_combined escape=json '{'
        '"time_local":"$time_local",'
        '"remote_addr":"$remote_addr",'
        '"remote_user":"$remote_user",'
        '"request":"$request",'
        '"status": "$status",'
        '"body_bytes_sent":"$body_bytes_sent",'
        '"request_time":"$request_time",'
        '"http_referrer":"$http_referer",'
        '"http_user_agent":"$http_user_agent",'
        '"request_id":"$http_x_request_id"'
    '}';

    access_log /var/log/nginx/access.log json_combined;
    error_log /var/log/nginx/error.log;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    server {
        listen 80;
        server_name localhost;

        # Health check endpoint
        location /healthz {
            proxy_pass http://app_active;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Request-ID $http_x_request_id;
            access_log off;
        }

        # Readiness check endpoint
        location /readyz {
            proxy_pass http://app_active;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Request-ID $http_x_request_id;
            access_log off;
        }

        # Metrics endpoint
        location /metrics {
            proxy_pass http://app_active;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Request-ID $http_x_request_id;
            limit_req zone=api burst=10 nodelay;
        }

        # Status endpoint
        location /status {
            proxy_pass http://app_active;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Request-ID $http_x_request_id;
            limit_req zone=api burst=10 nodelay;
        }

        # WebSocket endpoint
        location /ws/ {
            proxy_pass http://app_active;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Request-ID $http_x_request_id;
            proxy_read_timeout 86400;
            proxy_send_timeout 86400;
            limit_req zone=websocket burst=20 nodelay;
        }

        # Admin interface
        location /admin/ {
            proxy_pass http://app_active;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Request-ID $http_x_request_id;
            limit_req zone=api burst=10 nodelay;
        }

        # Default location
        location / {
            proxy_pass http://app_active;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Request-ID $http_x_request_id;
            limit_req zone=api burst=10 nodelay;
        }
    }
}
EOF
}

# Main logic
case "${1:-}" in
    "blue")
        switch_to_blue
        ;;
    "green")
        switch_to_green
        ;;
    *)
        echo "Usage: $0 [blue|green]"
        exit 1
        ;;
esac

echo "Traffic switched successfully!" 