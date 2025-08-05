import time
import threading
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from django.http import HttpResponse
from django.conf import settings

# Metrics
websocket_connections_total = Counter(
    'websocket_connections_total',
    'Total number of WebSocket connections'
)

websocket_messages_total = Counter(
    'websocket_messages_total',
    'Total number of WebSocket messages',
    ['type']
)

websocket_connections_active = Gauge(
    'websocket_connections_active',
    'Number of active WebSocket connections'
)

websocket_errors_total = Counter(
    'websocket_errors_total',
    'Total number of WebSocket errors',
    ['error_type']
)

websocket_message_duration = Histogram(
    'websocket_message_duration_seconds',
    'Time spent processing WebSocket messages'
)

http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration = Histogram(
    'http_request_duration_seconds',
    'Time spent processing HTTP requests',
    ['method', 'endpoint']
)

app_startup_time = Gauge(
    'app_startup_time_seconds',
    'Application startup time in seconds'
)

app_shutdown_time = Gauge(
    'app_shutdown_time_seconds',
    'Application shutdown time in seconds'
)

# Thread-safe connection tracking
class ConnectionTracker:
    def __init__(self):
        self._connections = set()
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._initialized = False
    
    def _ensure_initialized(self):
        """Ensure the tracker is properly initialized with Django settings."""
        if not self._initialized:
            try:
                # Record startup time only after Django is configured
                app_startup_time.set(time.time() - self._start_time)
                self._initialized = True
            except Exception:
                # Django settings not configured yet, skip for now
                pass
    
    def add_connection(self, connection_id):
        self._ensure_initialized()
        with self._lock:
            self._connections.add(connection_id)
            try:
                websocket_connections_active.set(len(self._connections))
                websocket_connections_total.inc()
            except Exception:
                # Django settings not configured yet, skip metrics
                pass
    
    def remove_connection(self, connection_id):
        self._ensure_initialized()
        with self._lock:
            self._connections.discard(connection_id)
            try:
                websocket_connections_active.set(len(self._connections))
            except Exception:
                # Django settings not configured yet, skip metrics
                pass
    
    def get_active_connections(self):
        with self._lock:
            return len(self._connections)
    
    def record_shutdown(self):
        try:
            shutdown_duration = time.time() - self._start_time
            app_shutdown_time.set(shutdown_duration)
        except Exception:
            # Django settings not configured yet, skip metrics
            pass

# Global connection tracker
connection_tracker = ConnectionTracker()

def metrics_view(request):
    """Prometheus metrics endpoint."""
    return HttpResponse(
        generate_latest(),
        content_type=CONTENT_TYPE_LATEST
    ) 