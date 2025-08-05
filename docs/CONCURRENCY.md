# Concurrency Model & Tuning

## Overview

This Django WebSocket service uses a multi-layered concurrency model optimized for high-performance WebSocket handling with support for 5000+ concurrent connections.

## Architecture

### 1. Process-Level Concurrency (CPU Parallelism)

**Configuration:**
```dockerfile
CMD ["uvicorn", "app.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop", "--worker-class", "uvicorn.workers.UvicornWorker"]
```

**Why 4 Workers?**
- **1 worker per CPU core** for I/O-bound workloads
- Each worker runs in a separate process for CPU parallelism
- **Connection capacity per worker depends on:**
  - Available memory (typically 1-2GB per container)
  - Memory per connection (~2-5KB per idle connection)
  - CPU overhead for message processing
  - Network I/O limits
  - Redis connection pool limits
- **Typical capacity**: 500-2000 connections per worker (varies by hardware)
- **Total capacity**: 2000-8000 concurrent connections (4 workers)

**CPU vs I/O Bound Considerations:**
- **I/O-bound (non-blocking)**: WebSocket connections, Redis operations, network I/O
- **I/O-bound (blocking)**: Database queries, file operations, external API calls
- **CPU-bound**: Message processing, metrics calculations, complex computations
- Workers handle non-blocking I/O operations efficiently
- Thread pool handles blocking I/O and CPU-bound operations

### 2. Event Loop (I/O Concurrency)

**Configuration:**
```python
# requirements.txt
uvloop==0.19.0
```

**Benefits:**
- **2-4x performance improvement** over standard asyncio
- Optimized for high-concurrency WebSocket handling
- Non-blocking I/O operations
- Efficient event loop implementation

### 3. Thread Pool (CPU-Bound Operations)

**Default Configuration:**
- Uvicorn's built-in thread pool for sync operations
- Handles blocking I/O (database queries, file I/O) and CPU-intensive tasks
- Prevents blocking the event loop

**Usage in Code:**
```python
from asgiref.sync import sync_to_async

# Blocking operations run in thread pool
@sync_to_async
def blocking_database_query():
    # Database queries are I/O-bound but blocking
    # This runs in thread pool, not blocking event loop
    return User.objects.get(id=1)

@sync_to_async
def cpu_intensive_operation():
    # CPU-bound operations also run in thread pool
    # Complex calculations, data processing, etc.
    pass
```

### 4. Async WebSocket Consumers

**Configuration:**
```python
# settings.py
ASYNC_CAPABLE = True

# consumers.py
class ChatConsumer(AsyncWebsocketConsumer):
    # Fully async implementation
    async def connect(self):
        # Non-blocking connection handling
        pass
```

**Benefits:**
- Non-blocking WebSocket operations
- Efficient message processing
- Graceful connection handling

## Resource Allocation

### Docker Compose Configuration

```yaml
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '1.0'
    reservations:
      cpus: '0.5'
      memory: 512M
```

**Resource Strategy:**
- **CPU**: 1.0 core limit, 0.5 core reservation
- **Memory**: 1GB limit, 512MB reservation
- Ensures predictable performance
- Prevents resource starvation

### Redis Channel Layer

**Configuration:**
```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.environ.get("REDIS_URL", "redis://localhost:6379/0")],
        },
    },
}
```

**Purpose:**
- Inter-worker communication
- Message broadcasting across workers
- Session state sharing

## Performance Characteristics

### Connection Capacity
- **Per Worker**: 500-2000 concurrent WebSocket connections (varies by hardware)
- **Total**: 2000-8000 concurrent connections (4 workers)
- **Memory Usage**: ~2-5KB per idle connection
- **CPU Usage**: Minimal for idle connections
- **Determining Factors**:
  - Available memory (1-2GB per container)
  - Message processing overhead
  - Network I/O capacity
  - Redis connection limits

### Message Throughput
- **WebSocket Messages**: Async processing, no blocking
- **Heartbeats**: 30-second intervals, minimal overhead
- **Redis Operations**: Non-blocking, high throughput

### Scalability
- **Horizontal**: Add more containers with load balancer
- **Vertical**: Increase worker count based on CPU cores
- **Memory**: Scale based on connection count

## Monitoring & Observability

### Metrics
- **Active Connections**: Per worker and total
- **Message Count**: Per connection and total
- **Error Rates**: Connection failures, message errors
- **Resource Usage**: CPU, memory, network I/O

### Health Checks
- **Liveness**: `/healthz` endpoint
- **Readiness**: `/readyz` endpoint
- **Graceful Shutdown**: SIGTERM handling

## Capacity Planning & Testing

### Load Testing
Use the load testing script to validate performance under concurrent load:

```bash
# Test WebSocket performance
python scripts/load_test.py --url ws://localhost/ws/chat/ --connections 1000 --messages 10 --duration 60

# This will provide performance data on:
# - Message throughput and latency
# - Connection success rates
# - System behavior under sustained load
# - Error rates and timeouts
```

### Tuning Recommendations

### For High Load (10,000+ connections)
```dockerfile
# Increase worker count based on CPU cores and capacity testing
CMD ["uvicorn", "app.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "8", "--loop", "uvloop"]
```

### For CPU-Intensive Workloads
```python
# Increase thread pool size
import asyncio
asyncio.get_event_loop().set_default_executor(
    concurrent.futures.ThreadPoolExecutor(max_workers=20)
)
```

### For Memory-Constrained Environments
```yaml
# Reduce memory limits
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
```

## Best Practices

1. **Keep Workers Async**: Avoid blocking operations in WebSocket consumers
2. **Use Thread Pool**: For blocking I/O operations (database queries, file I/O) and CPU-bound tasks
3. **Monitor Resources**: Track CPU, memory, and connection counts
4. **Graceful Shutdown**: Handle SIGTERM properly
5. **Connection Limits**: Set appropriate limits based on resources

## Troubleshooting

### High CPU Usage
- Check for blocking operations in async code
- Verify thread pool usage for CPU-bound tasks
- Monitor worker distribution

### Memory Leaks
- Check for unclosed WebSocket connections
- Monitor session store size
- Verify Redis connection cleanup

### Connection Failures
- Check Redis connectivity
- Verify worker health
- Monitor nginx proxy settings 