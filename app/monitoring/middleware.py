import uuid
import time
import structlog
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from .metrics import http_requests_total, http_request_duration

logger = structlog.get_logger(__name__)

class RequestIDMiddleware(MiddlewareMixin):
    """Add request ID to all requests for tracing."""
    
    def process_request(self, request):
        request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
        request.request_id = request_id
        request.META['HTTP_X_REQUEST_ID'] = request_id

class StructuredLoggingMiddleware(MiddlewareMixin):
    """Add structured logging for all requests."""
    
    def process_request(self, request):
        request._start_time = time.time()
        logger.info(
            "Request started",
            request_id=getattr(request, 'request_id', 'unknown'),
            method=request.method,
            path=request.path,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            remote_addr=request.META.get('REMOTE_ADDR', ''),
        )
    
    def process_response(self, request, response):
        # Record HTTP metrics
        try:
            duration = time.time() - getattr(request, '_start_time', time.time())
            endpoint = request.path
            method = request.method
            status = str(response.status_code)
            
            # Record metrics
            http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
            http_request_duration.labels(method=method, endpoint=endpoint).observe(duration)
        except Exception as e:
            logger.error("Failed to record HTTP metrics", error=str(e))
        
        logger.info(
            "Request completed",
            request_id=getattr(request, 'request_id', 'unknown'),
            status_code=response.status_code,
            content_length=len(response.content) if hasattr(response, 'content') else 0,
        )
        return response 