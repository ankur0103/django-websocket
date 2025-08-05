# Django WebSocket Production Service

A production-ready Django WebSocket service with blue-green deployments, observability, and high concurrency support. This service implements a message counter over WebSockets with comprehensive monitoring and zero-downtime deployment capabilities.

## 🚀 Quick Start

```bash
# Clone and start the full stack
git clone <repository-url>
cd django-websocket
make up

# Run load tests (5000+ concurrent connections)
make load-test

# Blue-green deployment
make promote

# Monitor the service
make monitor
```

## 🛠️ Local Development Setup

### **Prerequisites**
- Python 3.11+
- Redis
- Virtual environment (recommended)

### **1. Install Dependencies**
```bash
cd app
pip install -r ../requirements.txt
```

### **2. Start Redis**
```bash
# Install Redis if not installed
# macOS: brew install redis
# Ubuntu: sudo apt-get install redis-server

# Start Redis
redis-server
```

### **3. Start the ASGI Server**
```bash
cd app
uvicorn app.asgi:application --host 0.0.0.0 --port 8000 --reload
```

**Production with graceful shutdown:**
```bash
uvicorn app.asgi:application --host 0.0.0.0 --port 8000 --workers 4
```

### **4. Test the Application**
- **WebSocket Test Page**: http://localhost:8000/test/
- **Health Check**: http://localhost:8000/healthz
- **Admin Interface**: http://localhost:8000/admin/

### **5. Test WebSocket Connection**
```bash
# Command line test
websocat ws://localhost:8000/ws/chat/

# Or use the browser test page
# Visit: http://localhost:8000/test/
```

## 📋 Features

### ✅ Functional Requirements
- **WebSocket Endpoint**: `/ws/chat/` accepts text messages and replies with `{"count": n}`
- **Server-side Push**: Broadcasts heartbeat `{"ts": <iso-timestamp>}` every 30 seconds
- **Graceful Shutdown**: Handles SIGTERM, closes sockets with code 1001, exits within 10 seconds
- **Reconnection Support**: Clients can include `session_uuid` query parameter to resume sessions

### ✅ Production Requirements
- **Blue-Green Deployment**: Two independent stacks with zero-downtime traffic switching
- **ASGI Concurrency**: 4 uvicorn workers with uvloop for high performance
- **Observability**: Structured JSON logs, Prometheus metrics, health checks, and alerting
- **Load Testing**: Supports 5000+ concurrent WebSocket connections

## 🏗️ Architecture

```
Client → Nginx (Load Balancer) → app_blue:8000 (Active)
                              → app_green:8000 (Standby)
                              → Redis (Channel Layer)
                              → Prometheus (Metrics)
                              → Grafana (Dashboards)
```

### Components
- **Django + Channels**: WebSocket handling with ASGI
- **Redis**: Channel layer backend for WebSocket scaling
- **Nginx**: Load balancer and reverse proxy
- **Prometheus + Grafana**: Metrics and monitoring
- **Docker Compose**: Blue-green deployment orchestration

## 📁 Project Structure

```
.
├── docker/
│   ├── Dockerfile              # Production Docker image
│   ├── compose.yml             # Blue-green deployment orchestration
│   └── nginx/
│       └── nginx.conf          # Load balancer configuration
├── app/
│   ├── manage.py
│   ├── app/
│   │   ├── settings.py         # Django settings with Channels
│   │   ├── asgi.py            # ASGI application with graceful shutdown
│   │   └── urls.py            # URL routing
│   ├── chat/
│   │   ├── consumers.py       # WebSocket consumer implementation
│   │   └── routing.py         # WebSocket URL routing
│   └── monitoring/
│       ├── middleware.py      # Request ID and structured logging
│       ├── metrics.py         # Prometheus metrics collection
│       ├── views.py           # Health check endpoints
│       └── urls.py            # Monitoring URL routing
├── scripts/
│   ├── promote.sh             # Blue-green deployment script
│   ├── monitor.sh             # Real-time monitoring script
│   └── load_test.py           # Load testing with asyncio
├── monitoring/
│   ├── prometheus.yml         # Prometheus configuration
│   └── alerting/
│       └── rules.yml          # Alerting rules
├── docs/
│   ├── DESIGN.md              # Architecture and design decisions
│   └── OBSERVABILITY.md       # Monitoring and observability guide
├── Makefile                   # Common commands
└── requirements.txt           # Python dependencies
```

## 🛠️ Installation & Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)
- Make (optional, for convenience commands)

### 1. Start the Full Stack
```bash
# Start all services
make up

# Or manually
docker-compose -f docker/compose.yml up -d
```

### 2. Verify Deployment
```bash
# Check service status
make status

# Test connectivity
make test

# View logs
make logs
```

### 3. Access Services
- **Application**: http://localhost
- **Metrics**: http://localhost/metrics
- **Health Check**: http://localhost/healthz
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## 🔧 Configuration

### **Environment Variables**
```bash
# WebSocket Base URL (default: ws://localhost:8000)
WS_BASE_URL=ws://localhost:8000

# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key
REDIS_URL=redis://localhost:6379/0
```

### **Custom Port Setup**
```bash
# For different port (e.g., 8001)
WS_BASE_URL=ws://localhost:8001 uvicorn app.asgi:application --host 0.0.0.0 --port 8001 --reload
```

## 🔄 Blue-Green Deployment

### Current Status
```bash
# Check current deployment status
make status
# or
./scripts/promote.sh status
```

### Perform Deployment
```bash
# Promote next color (blue ↔ green)
make promote
# or
./scripts/promote.sh
```

### Deployment Process
1. **Build & Start**: Deploy new version to standby color
2. **Health Check**: Verify service is healthy
3. **Smoke Tests**: Run basic functionality tests
4. **Traffic Switch**: Update Nginx configuration
5. **Verification**: Confirm new service handles traffic
6. **Cleanup**: Stop old service

## 📊 Monitoring & Observability

### Real-time Monitoring
```bash
# Monitor everything (logs + metrics)
make monitor

# Monitor metrics only
./scripts/monitor.sh --metrics-only

# Monitor logs only
./scripts/monitor.sh --logs-only

# Custom interval (5 seconds)
./scripts/monitor.sh --interval 5
```

### Health Checks
- **Liveness**: `GET /healthz` - Always returns 200 if running
- **Readiness**: `GET /readyz` - Returns 200 only if ready for traffic
- **Status**: `GET /status` - Detailed application information
- **Metrics**: `GET /metrics` - Prometheus metrics

### Structured Logging
All logs are in JSON format for easy parsing:
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

### Key Metrics
- `websocket_connections_active`: Active WebSocket connections
- `websocket_messages_total`: Total messages by type
- `websocket_errors_total`: Error count by type
- `websocket_message_duration_seconds`: Message processing time
- `app_startup_time_seconds`: Application startup time

## 🧪 Load Testing

### Run Load Tests
```bash
# Test with 5000 concurrent connections
make load-test

# Custom configuration
python3 scripts/load_test.py --connections 1000 --messages 50 --duration 60
```

### Load Test Features
- **Concurrent Connections**: Up to 5000+ WebSocket connections
- **Message Throughput**: Configurable messages per connection
- **Latency Measurement**: Response time tracking
- **Error Rate Monitoring**: Connection and message error tracking
- **Reconnection Testing**: Session UUID support

### Sample Results
```
============================================================
LOAD TEST RESULTS
============================================================
Test Duration: 120.00 seconds
Connections Created: 5000
Connections Successful: 4987
Total Messages Sent: 49870
Total Messages Received: 49865
Total Errors: 5
Success Rate: 99.99%
Average Latency: 12.34 ms
Median Latency: 10.21 ms
95th Percentile: 25.67 ms
Messages per Second: 415.58
Connections per Second: 41.56
============================================================
```

## 🔧 Development

### Local Development
```bash
# Install dependencies
make install

# Start development server
make dev

# Create superuser
make superuser
```

### **Quick Development Commands**
```bash
# Start Redis
redis-server

# Start ASGI server (required for WebSocket support)
cd app && uvicorn app.asgi:application --host 0.0.0.0 --port 8000 --reload

# Test WebSocket connection
websocat ws://localhost:8000/ws/chat/

# Test in browser
# Visit: http://localhost:8000/test/

# Run tests
cd app && python manage.py test
```

### Testing WebSocket
```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/chat/');

// Send message
ws.send(JSON.stringify({message: 'Hello World'}));

// Listen for responses
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
    // {count: 1} or {ts: "2024-01-01T12:00:00Z"} or {bye: true, total: 5}
};
```

### Reconnection Example
```javascript
const sessionUuid = 'abc123';
const ws = new WebSocket(`ws://localhost:8000/ws/chat/?session_uuid=${sessionUuid}`);
```

## 📈 Performance

### Concurrency Tuning
- **4 Uvicorn Workers**: CPU parallelism across processes
- **uvloop**: 2-4x performance improvement over asyncio
- **Redis Channel Layer**: Cross-worker communication
- **Nginx Rate Limiting**: 100 req/s for WebSocket, 1000 req/s for API

### Capacity Planning
- **Connections per Worker**: ~1250 concurrent connections
- **Total Capacity**: ~5000 connections
- **Memory per Connection**: ~1KB
- **Messages per Second**: ~10,000 per worker

### Performance Targets
- **Startup Time**: < 3 seconds
- **Shutdown Time**: < 10 seconds
- **Message Latency**: < 100ms (95th percentile)
- **Connection Success Rate**: > 99.9%

## 🚨 Alerting

### Prometheus Alert Rules
- **No Active Connections**: Alert if no connections for >60s
- **High Error Rate**: Alert if error rate >0.1 errors/second
- **High Latency**: Alert if 95th percentile >1s
- **Service Down**: Alert if service is down

### Alert Severity
- **Warning**: Performance degradation, high latency
- **Critical**: Service down, high error rate

## 🛡️ Security

### Security Features
- **Input Validation**: JSON message validation
- **Rate Limiting**: Nginx rate limiting on connections
- **Request Tracking**: Request ID for audit trails
- **Graceful Shutdown**: Prevents data loss during deployment

### Network Security
- **Reverse Proxy**: Nginx handles external traffic
- **Health Checks**: Prevents traffic to unhealthy instances
- **Container Isolation**: Each service runs in isolated container

## 🔍 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
make logs

# Check health
curl http://localhost/healthz

# Check readiness
curl http://localhost/readyz
```

#### High Error Rate
```bash
# Monitor errors in real-time
./scripts/monitor.sh --logs-only

# Check Redis connectivity
docker-compose exec redis redis-cli ping
```

#### Performance Issues
```bash
# Monitor metrics
./scripts/monitor.sh --metrics-only

# Check resource usage
docker stats
```

### Debug Commands
```bash
# View all logs
make logs

# Check deployment status
make status

# Monitor in real-time
make monitor

# Run quick tests
make test
```

## 📚 Documentation

- **[Design Documentation](docs/DESIGN.md)**: Architecture and implementation details
- **[Observability Guide](docs/OBSERVABILITY.md)**: Monitoring and alerting setup
- **[API Reference](docs/API.md)**: WebSocket API documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the documentation
3. Open an issue on GitHub

---

**Built with ❤️ for production WebSocket services**