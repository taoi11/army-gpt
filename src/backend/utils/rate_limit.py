import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List
import os
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from .logger import logger

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
        # Load limits from environment
        self.hourly_limit = int(os.getenv("RATE_LIMIT_PER_HOUR", "15"))
        self.daily_limit = int(os.getenv("RATE_LIMIT_PER_DAY", "50"))
        self.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
        
        # Initialize limits per IP
        self.hourly_limits: Dict[str, RateLimit] = defaultdict(
            lambda: RateLimit(self.hourly_limit, 3600)
        )
        self.daily_limits: Dict[str, RateLimit] = defaultdict(
            lambda: RateLimit(self.daily_limit, 86400)
        )
        
        # Track requests in progress to avoid double counting
        self.requests_in_progress: Dict[str, set] = defaultdict(set)

    def is_allowed(self, ip: str, request_id: str = None) -> bool:
        """Check if request is allowed for given IP"""
        # Always allow in debug mode
        if self.debug_mode:
            return True

        # If this is a retry (has request_id and is in progress), allow it
        if request_id and request_id in self.requests_in_progress[ip]:
            return True

        # Check both hourly and daily limits
        hourly_allowed = self.hourly_limits[ip].is_allowed()
        if not hourly_allowed:
            logger.warning(f"IP {ip} exceeded hourly rate limit")
            return False

        daily_allowed = self.daily_limits[ip].is_allowed()
        if not daily_allowed:
            logger.warning(f"IP {ip} exceeded daily rate limit")
            return False

        # Track new request if it has an ID
        if request_id:
            self.requests_in_progress[ip].add(request_id)

        return True

    def record_request(self, ip: str, request_id: str = None):
        """Record a successful request"""
        if not self.debug_mode:
            # Only record if it's a new request or no request_id provided
            if not request_id or request_id not in self.requests_in_progress[ip]:
                self.hourly_limits[ip].add_request()
                self.daily_limits[ip].add_request()
            
            # Clean up tracking
            if request_id:
                self.requests_in_progress[ip].discard(request_id)

    def get_remaining(self, ip: str) -> Dict[str, int]:
        """Get remaining requests for given IP"""
        # In debug mode, always show max limits
        if self.debug_mode:
            return {
                "hourly_remaining": self.hourly_limit,
                "daily_remaining": self.daily_limit
            }

        # Clean up expired requests before getting count
        self.hourly_limits[ip].is_allowed()  # This cleans up expired requests
        self.daily_limits[ip].is_allowed()   # This cleans up expired requests

        return {
            "hourly_remaining": self.hourly_limits[ip].get_remaining(),
            "daily_remaining": self.daily_limits[ip].get_remaining()
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
        
        if is_llm_api:
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
        
        # Record only LLM API calls
        if is_llm_api:
            rate_limiter.record_request(client_ip, request_id)
            remaining = rate_limiter.get_remaining(client_ip)
        else:
            # For non-API routes or GET requests, just get current limits
            remaining = rate_limiter.get_remaining(client_ip)
        
        # Always add rate limit headers
        response.headers["X-RateLimit-Remaining-Hour"] = str(remaining["hourly_remaining"])
        response.headers["X-RateLimit-Remaining-Day"] = str(remaining["daily_remaining"])
        
        return response 