#!/bin/bash

# Script to send application logs to Loki for local development
# This script monitors Docker container logs and sends them to Loki

LOKI_URL="http://localhost:3100"
CONTAINER_NAME="django-websocket-app_blue-1"

echo "🔍 Monitoring logs from container: $CONTAINER_NAME"
echo "📤 Sending logs to Loki at: $LOKI_URL"

# Function to send log to Loki
send_log_to_loki() {
    local timestamp=$(date +%s)000000000
    local log_entry="$1"
    local level="$2"
    local container="$3"
    
    # Create Loki log entry
    local loki_payload=$(cat <<EOF
{
  "streams": [
    {
      "stream": {
        "job": "django-websocket",
        "container": "$container",
        "level": "$level"
      },
      "values": [
        ["$timestamp", "$log_entry"]
      ]
    }
  ]
}
EOF
)

    # Send to Loki
    curl -s -X POST "$LOKI_URL/loki/api/v1/push" \
        -H "Content-Type: application/json" \
        -d "$loki_payload" > /dev/null
}

# Monitor Docker logs and send to Loki
docker logs -f --tail=0 "$CONTAINER_NAME" 2>/dev/null | while read -r line; do
    # Determine log level
    level="info"
    if [[ "$line" == *"ERROR"* ]] || [[ "$line" == *"error"* ]]; then
        level="error"
    elif [[ "$line" == *"WARNING"* ]] || [[ "$line" == *"warning"* ]]; then
        level="warning"
    elif [[ "$line" == *"DEBUG"* ]] || [[ "$line" == *"debug"* ]]; then
        level="debug"
    fi
    
    # Escape quotes in log message
    escaped_line=$(echo "$line" | sed 's/"/\\"/g')
    
    # Send to Loki
    send_log_to_loki "$escaped_line" "$level" "$CONTAINER_NAME"
    
    echo "📝 [$level] $line"
done 