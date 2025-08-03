# Django WebSocket Service - Design Documentation

## Architecture Overview

This Django WebSocket service is designed for production use with high concurrency, zero-downtime deployments, and comprehensive observability.

### Core Components

1. **Django + Channels**: WebSocket handling with ASGI
2. **Redis**: Channel layer backend for WebSocket scaling
3. **Nginx**: Load balancer and reverse proxy
4. **Prometheus + Grafana**: Metrics and monitoring
5. **Docker Compose**: Blue-green deployment orchestration

## ASGI Concurrency Model

### Event Loop vs Thread Pool

The service uses a hybrid approach to handle both I/O-bound and CPU-bound operations:

- **Event Loop (uvloop)**: Handles WebSocket connections, message processing, and Redis operations
- **Thread Pool**: Offloads CPU-intensive operations and database queries
- **4 Uvicorn Workers**: Provides CPU parallelism across multiple processes

### Concurrency Tuning

```python
# Docker configuration
CMD ["uvicorn", "app.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop"]
```

**Why 4 workers?**
- Each worker can handle ~1250 concurrent connections
- Total capacity: ~5000 connections
- Balances memory usage and CPU utilization
- uvloop provides 2-4x performance improvement over asyncio

## WebSocket Implementation

### Message Counter Feature

The WebSocket consumer implements a simple message counter:

1. **Connection**: Accepts WebSocket connection, generates unique ID
2. **Message Processing**: Increments counter, sends response with count
3. **Heartbeat**: Broadcasts timestamp every 30 seconds
4. **Disconnection**: Sends goodbye message with total count

### Reconnection Support

Clients can include a `session_uuid` query parameter to resume sessions:

```javascript
const ws = new WebSocket('ws://localhost/ws/chat/?session_uuid=abc123');
```

### Graceful Shutdown

The service handles SIGTERM gracefully:

1. Stops accepting new connections
2. Completes in-flight messages
3. Sends goodbye messages to active connections
4. Closes connections with code 1001
5. Exits within 10 seconds

## Blue-Green Deployment

### Architecture

Two independent stacks (blue/green) behind Nginx:

```
Client → Nginx → app_blue:8000 (active)
              → app_green:8000 (standby)
```

### Deployment Process

1. **Build & Start**: Deploy new version to standby color
2. **Health Check**: Verify service is healthy
3. **Smoke Tests**: Run basic functionality tests
4. **Traffic Switch**: Update Nginx configuration
5. **Verification**: Confirm new service handles traffic
6. **Cleanup**: Stop old service

### Traffic Switching

Nginx configuration is updated dynamically:

```nginx
upstream app_active {
    server app_blue:8000 max_fails=3 fail_timeout=30s;
    # or
    server app_green:8000 max_fails=3 fail_timeout=30s;
}
```

## Observability

### Structured Logging

All logs are in JSON format with consistent fields:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "logger": "chat.consumers",
  "message": "WebSocket connected",
  "connection_id": "uuid",
  "color": "blue",
  "request_id": "uuid"
}
```

### Metrics

Prometheus-style metrics for monitoring:

- `websocket_connections_total`: Total connections
- `websocket_connections_active`: Active connections
- `websocket_messages_total`: Message count by type
- `websocket_errors_total`: Error count by type
- `websocket_message_duration_seconds`: Message processing time
- `app_startup_time_seconds`: Application startup time
- `app_shutdown_time_seconds`: Application shutdown time

### Health Checks

- **Liveness Probe** (`/healthz`): Always returns 200 if app is running
- **Readiness Probe** (`/readyz`): Returns 200 only if ready to serve traffic
- **Status Endpoint** (`/status`): Detailed application information

## Performance Considerations

### Memory Management

- Connection tracking uses thread-safe sets
- Metrics are collected efficiently with minimal overhead
- Graceful shutdown prevents memory leaks

### Network Optimization

- Nginx handles rate limiting and compression
- WebSocket connections use efficient binary protocol
- Redis connection pooling for channel layer

### Scalability

- Horizontal scaling with multiple workers
- Redis for cross-worker communication
- Stateless design for easy scaling

## Security Considerations

### Input Validation

- JSON message validation
- Rate limiting on WebSocket connections
- Request ID tracking for audit trails

### Network Security

- Nginx as reverse proxy
- Health checks prevent traffic to unhealthy instances
- Graceful shutdown prevents data loss

## Monitoring and Alerting

### Prometheus Rules

- No active connections for >60s
- High error rate (>0.1 errors/second)
- High latency (>1s 95th percentile)
- Service down detection

### Grafana Dashboards

- Real-time connection count
- Message throughput
- Error rates and latencies
- System resource usage

## Testing Strategy

### Load Testing

- 5000+ concurrent WebSocket connections
- Message throughput testing
- Latency measurement
- Error rate monitoring

### Integration Testing

- Health check validation
- Blue-green deployment testing
- Graceful shutdown verification
- Reconnection testing

## Deployment Considerations

### Resource Requirements

- **Memory**: 1GB per container
- **CPU**: 1 core per container
- **Storage**: Minimal (stateless)
- **Network**: High bandwidth for WebSocket connections

### Environment Variables

- `COLOR`: blue/green for deployment identification
- `REDIS_URL`: Redis connection string
- `DEBUG`: Enable/disable debug mode
- `SECRET_KEY`: Django secret key

## Future Enhancements

1. **Session Persistence**: Store session data in Redis
2. **Message Broadcasting**: Send messages to all connected clients
3. **Authentication**: Add WebSocket authentication
4. **Rate Limiting**: Per-client rate limiting
5. **Message Queuing**: Async message processing
6. **Multi-region**: Cross-region deployment support 