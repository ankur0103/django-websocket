import uuid
import structlog
from django.utils.deprecation import MiddlewareMixin

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
        logger.info(
            "Request started",
            request_id=getattr(request, 'request_id', 'unknown'),
            method=request.method,
            path=request.path,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            remote_addr=request.META.get('REMOTE_ADDR', ''),
        )
    
    def process_response(self, request, response):
        logger.info(
            "Request completed",
            request_id=getattr(request, 'request_id', 'unknown'),
            status_code=response.status_code,
            content_length=len(response.content) if hasattr(response, 'content') else 0,
        )
        return response 