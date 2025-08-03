# Observability Documentation

## Overview

The Django WebSocket service implements comprehensive observability with structured logging, metrics collection, health checks, and alerting.

## Structured Logging

### Log Format

All application logs are in JSON format for easy parsing and analysis:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "logger": "chat.consumers",
  "message": "WebSocket connected",
  "connection_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_uuid": "abc123",
  "color": "blue",
  "request_id": "req-123",
  "remote_addr": "192.168.1.1",
  "user_agent": "Mozilla/5.0..."
}
```

### Log Levels

- **DEBUG**: Detailed debugging information
- **INFO**: General application flow
- **WARNING**: Unexpected but handled situations
- **ERROR**: Errors that don't stop the application
- **CRITICAL**: Critical errors that may stop the application

### Log Sources

1. **Django Application**: Request/response logging
2. **WebSocket Consumer**: Connection and message events
3. **Monitoring**: Health checks and metrics
4. **Middleware**: Request ID tracking and structured logging

## Metrics Collection

### Prometheus Metrics

The service exposes Prometheus-style metrics at `/metrics`:

#### WebSocket Metrics

```
# Total WebSocket connections
websocket_connections_total{color="blue"} 1250

# Active WebSocket connections
websocket_connections_active{color="blue"} 1000

# Total messages by type
websocket_messages_total{color="blue",type="received"} 5000
websocket_messages_total{color="blue",type="heartbeat"} 3000

# Message processing duration
websocket_message_duration_seconds_bucket{color="blue",le="0.1"} 4500
websocket_message_duration_seconds_bucket{color="blue",le="0.5"} 4800
websocket_message_duration_seconds_bucket{color="blue",le="1.0"} 5000

# Error counts by type
websocket_errors_total{color="blue",error_type="connection_failed"} 5
websocket_errors_total{color="blue",error_type="json_decode_error"} 2
```

#### HTTP Metrics

```
# HTTP request counts
http_requests_total{method="GET",endpoint="/healthz",status="200"} 1000
http_requests_total{method="GET",endpoint="/metrics",status="200"} 500

# HTTP request duration
http_request_duration_seconds_bucket{method="GET",endpoint="/healthz",le="0.1"} 950
http_request_duration_seconds_bucket{method="GET",endpoint="/healthz",le="0.5"} 1000
```

#### Application Metrics

```
# Application startup time
app_startup_time_seconds{color="blue"} 2.5

# Application shutdown time
app_shutdown_time_seconds{color="blue"} 8.2
```

### Metrics Collection

Metrics are collected using the `prometheus-client` library:

```python
from prometheus_client import Counter, Gauge, Histogram

# Counters for cumulative metrics
websocket_connections_total = Counter(
    'websocket_connections_total',
    'Total number of WebSocket connections',
    ['color']
)

# Gauges for current values
websocket_connections_active = Gauge(
    'websocket_connections_active',
    'Number of active WebSocket connections',
    ['color']
)

# Histograms for distribution metrics
websocket_message_duration = Histogram(
    'websocket_message_duration_seconds',
    'Time spent processing WebSocket messages',
    ['color']
)
```

## Health Checks

### Liveness Probe (`/healthz`)

Always returns 200 if the application is running:

```json
{
  "status": "healthy",
  "color": "blue",
  "timestamp": 1704067200.123
}
```

### Readiness Probe (`/readyz`)

Returns 200 only if the service is ready to handle traffic:

```json
{
  "status": "ready",
  "color": "blue",
  "active_connections": 1000,
  "timestamp": 1704067200.123
}
```

**Readiness checks:**
- Redis connectivity
- Channel layer availability
- Active connection count

### Status Endpoint (`/status`)

Provides detailed application information:

```json
{
  "status": "running",
  "color": "blue",
  "active_connections": 1000,
  "heartbeat_interval": 30,
  "graceful_shutdown_timeout": 10,
  "timestamp": 1704067200.123
}
```

## Monitoring Script

The `scripts/monitor.sh` script provides real-time monitoring:

### Features

- **Log Tailing**: Monitors container logs for ERROR messages
- **Metrics Display**: Shows top-5 metrics every 10 seconds
- **Health Status**: Displays service health and readiness
- **Connection Count**: Shows active WebSocket connections
- **Deployment Status**: Shows blue/green deployment status

### Usage

```bash
# Monitor everything
./scripts/monitor.sh

# Monitor metrics only
./scripts/monitor.sh --metrics-only

# Monitor logs only
./scripts/monitor.sh --logs-only

# Custom interval
./scripts/monitor.sh --interval 5

# Limited duration
./scripts/monitor.sh --duration 60
```

### Sample Output

```
[2024-01-01 12:00:00] Starting monitoring for Django WebSocket service...
[2024-01-01 12:00:00] Current deployment status:
app_blue: running
app_green: stopped
Active color: blue

[2024-01-01 12:00:00] Tailing logs for ERROR messages...
=== Mon Jan 1 12:00:10 UTC 2024 ===
Health: healthy
Ready: ready
Active connections: 1000
=== Top 5 Metrics ===
websocket_connections_active{color="blue"} 1000
websocket_connections_total{color="blue"} 1250
websocket_messages_total{color="blue",type="received"} 5000
websocket_messages_total{color="blue",type="heartbeat"} 3000
http_requests_total{method="GET",endpoint="/healthz",status="200"} 1000
==================
```

## Alerting Rules

### Prometheus Alerting Rules

Located in `monitoring/alerting/rules.yml`:

#### No Active Connections

```yaml
- alert: NoActiveConnections
  expr: websocket_connections_active == 0
  for: 60s
  labels:
    severity: warning
  annotations:
    summary: "No active WebSocket connections"
    description: "No active WebSocket connections for more than 60 seconds"
```

#### High Error Rate

```yaml
- alert: HighErrorRate
  expr: rate(websocket_errors_total[5m]) > 0.1
  for: 30s
  labels:
    severity: critical
  annotations:
    summary: "High WebSocket error rate"
    description: "WebSocket error rate is {{ $value }} errors per second"
```

#### High Latency

```yaml
- alert: HighLatency
  expr: histogram_quantile(0.95, websocket_message_duration_seconds) > 1
  for: 30s
  labels:
    severity: warning
  annotations:
    summary: "High WebSocket message latency"
    description: "95th percentile latency is {{ $value }} seconds"
```

## Grafana Dashboards

### WebSocket Dashboard

**Panels:**
1. **Connection Count**: Active vs total connections
2. **Message Throughput**: Messages per second
3. **Error Rate**: Errors per second by type
4. **Latency**: 95th percentile message processing time
5. **Health Status**: Service health over time

### System Dashboard

**Panels:**
1. **CPU Usage**: Per container CPU utilization
2. **Memory Usage**: Per container memory usage
3. **Network I/O**: Bytes sent/received
4. **Disk I/O**: Read/write operations

## Log Aggregation

### Docker Logs

Container logs are captured by Docker:

```bash
# View all logs
docker-compose logs

# Follow logs
docker-compose logs -f

# Filter by service
docker-compose logs app_blue
```

### Log Parsing

JSON logs can be parsed by log aggregation systems:

```python
import json

# Parse log line
log_data = json.loads(log_line)
print(f"Level: {log_data['level']}")
print(f"Message: {log_data['message']}")
print(f"Connection ID: {log_data.get('connection_id')}")
```

## Performance Monitoring

### Key Performance Indicators (KPIs)

1. **Connection Success Rate**: Successful connections / total attempts
2. **Message Success Rate**: Successful messages / total messages
3. **Average Latency**: Mean message processing time
4. **95th Percentile Latency**: 95th percentile message processing time
5. **Error Rate**: Errors per second
6. **Throughput**: Messages per second

### Capacity Planning

- **Connections per Worker**: ~1250 concurrent connections
- **Messages per Second**: ~10,000 messages per worker
- **Memory per Connection**: ~1KB per connection
- **CPU per Message**: ~0.1ms per message

## Troubleshooting

### Common Issues

1. **High Error Rate**: Check Redis connectivity and message format
2. **High Latency**: Monitor CPU and memory usage
3. **Connection Drops**: Check network stability and timeouts
4. **Memory Leaks**: Monitor connection cleanup and graceful shutdown

### Debug Commands

```bash
# Check service health
curl http://localhost/healthz

# Check readiness
curl http://localhost/readyz

# View metrics
curl http://localhost/metrics

# Check logs
docker-compose logs app_blue

# Monitor in real-time
./scripts/monitor.sh
```

## Integration with External Systems

### Prometheus Integration

Prometheus scrapes metrics from both blue and green instances:

```yaml
scrape_configs:
  - job_name: 'django-websocket'
    static_configs:
      - targets: ['app_blue:8000', 'app_green:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
```

### Grafana Integration

Grafana connects to Prometheus for dashboard visualization:

```yaml
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
```

### Alert Manager Integration

Prometheus AlertManager can send alerts to:
- Email
- Slack
- PagerDuty
- Webhooks 