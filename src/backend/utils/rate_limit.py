import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List
import os
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from .logger import logger
from src.backend.llm.keycheck import CREDITS_AVAILABLE

@dataclass
class RateLimit:
    max_requests: int
    window_seconds: int
    requests: List[float] = None

    def __post_init__(self):
        self.requests = []

    def is_allowed(self) -> bool:
        """Check if request is allowed within rate limit"""
        now = time.time()
        # Remove old requests
        self.requests = [t for t in self.requests if now - t < self.window_seconds]
        return len(self.requests) < self.max_requests

    def add_request(self):
        """Add a request to the list"""
        now = time.time()
        # Clean expired requests first
        self.requests = [t for t in self.requests if now - t < self.window_seconds]
        self.requests.append(now)

    def get_remaining(self) -> int:
        """Get remaining requests"""
        now = time.time()
        # Only count requests that aren't expired
        valid_requests = [t for t in self.requests if now - t < self.window_seconds]
        return self.max_requests - len(valid_requests)

class RateLimiter:
    def __init__(self):
        # Get limits from environment or use defaults
        self.hourly_limit = int(os.getenv("RATE_LIMIT_PER_HOUR", "15"))
        self.daily_limit = int(os.getenv("RATE_LIMIT_PER_DAY", "50"))
        
        # Initialize counters
        self.hourly_requests = defaultdict(list)  # {ip: [timestamps]}
        self.daily_requests = defaultdict(list)   # {ip: [timestamps]}
        self.request_ids = set()  # Track unique request IDs
        
        # Current time window
        self.hour = 3600  # seconds
        self.day = 86400  # seconds
        
    def _cleanup_old_requests(self, ip: str):
        """Remove expired timestamps"""
        current_time = time.time()
        
        # Cleanup hourly
        self.hourly_requests[ip] = [
            ts for ts in self.hourly_requests[ip]
            if current_time - ts < self.hour
        ]
        
        # Cleanup daily
        self.daily_requests[ip] = [
            ts for ts in self.daily_requests[ip]
            if current_time - ts < self.day
        ]
        
        # Cleanup old request IDs (older than a day)
        self.request_ids = {
            rid for rid in self.request_ids
            if rid.split('-')[0].startswith('t')  # Only keep our timestamped IDs
            and current_time - float(rid.split('-')[0][1:]) < self.day  # Remove 't' prefix
        }

    def is_allowed(self, ip: str, request_id: str = None) -> bool:
        """Check if request is allowed based on rate limits"""
        # Skip rate limiting for Ollama requests (when credits not available)
        if not CREDITS_AVAILABLE:
            return True
            
        self._cleanup_old_requests(ip)
        
        # If request_id provided, check if it's a duplicate
        if request_id:
            if request_id in self.request_ids:
                return True  # Allow duplicate requests (retries)
            # Store with timestamp prefix for cleanup
            timestamped_id = f"t{time.time()}-{request_id}"
            self.request_ids.add(timestamped_id)
        
        # Check limits
        if len(self.hourly_requests[ip]) >= self.hourly_limit:
            return False
            
        if len(self.daily_requests[ip]) >= self.daily_limit:
            return False
        
        # Add timestamp for new request
        current_time = time.time()
        self.hourly_requests[ip].append(current_time)
        self.daily_requests[ip].append(current_time)
        
        return True
    
    def get_remaining(self, ip: str) -> dict:
        """Get remaining requests for the client"""
        self._cleanup_old_requests(ip)
        
        # If using Ollama, return unlimited
        if not CREDITS_AVAILABLE:
            return {
                "hourly_remaining": 999,
                "daily_remaining": 999
            }
        
        return {
            "hourly_remaining": max(0, self.hourly_limit - len(self.hourly_requests[ip])),
            "daily_remaining": max(0, self.daily_limit - len(self.daily_requests[ip]))
        }

# Create singleton instance
rate_limiter = RateLimiter()

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Get client IP
        client_ip = request.client.host
        
        # Only check and enforce rate limits for LLM API calls
        is_llm_api = request.url.path.startswith("/llm") and request.method == "POST"
        
        # Get request ID from header if present (for retries/backup attempts)
        request_id = request.headers.get("X-Request-ID")
        
        if is_llm_api and CREDITS_AVAILABLE:  # Only rate limit when using OpenRouter
            if not rate_limiter.is_allowed(client_ip, request_id):
                remaining = rate_limiter.get_remaining(client_ip)
                error_response = {
                    "error": {
                        "code": 429,
                        "message": "Rate limit exceeded",
                        "details": {
                            "hourly_remaining": remaining["hourly_remaining"],
                            "daily_remaining": remaining["daily_remaining"],
                            "hourly_limit": rate_limiter.hourly_limit,
                            "daily_limit": rate_limiter.daily_limit,
                            "retry_after": "Wait for the next hour or day depending on which limit was exceeded"
                        }
                    }
                }
                return Response(
                    content=json.dumps(error_response),
                    status_code=429,
                    headers={
                        "Content-Type": "application/json",
                        "X-RateLimit-Remaining-Hour": str(remaining["hourly_remaining"]),
                        "X-RateLimit-Remaining-Day": str(remaining["daily_remaining"])
                    }
                )
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers to response
        if is_llm_api:
            remaining = rate_limiter.get_remaining(client_ip)
            response.headers["X-RateLimit-Remaining-Hour"] = str(remaining["hourly_remaining"])
            response.headers["X-RateLimit-Remaining-Day"] = str(remaining["daily_remaining"])
        
        return response 