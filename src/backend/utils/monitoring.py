from fastapi import APIRouter, Request
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
import time
from .logger import logger

# Request metrics
requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Response time metrics
request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# API call metrics
api_calls_total = Counter(
    'api_calls_total',
    'Total external API calls',
    ['api_name', 'status']
)

# Create router for monitoring endpoints
router = APIRouter(tags=["monitoring"])

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting request metrics"""
    async def dispatch(self, request: Request, call_next):
        # Start timer
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        method = request.method
        endpoint = request.url.path
        status = response.status_code
        
        # Update metrics
        requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        return response

def track_api_call(api_name: str, status: str = "success"):
    """Helper function to track external API calls"""
    api_calls_total.labels(
        api_name=api_name,
        status=status
    ).inc()
    logger.info(f"API call tracked: {api_name} - {status}") 