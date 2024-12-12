import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List
import os
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
        
        if len(self.requests) >= self.max_requests:
            return False
            
        self.requests.append(now)
        return True

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

    def is_allowed(self, ip: str) -> bool:
        """Check if request is allowed for given IP"""
        # Always allow in debug mode
        if self.debug_mode:
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

        return True

    def get_remaining(self, ip: str) -> Dict[str, int]:
        """Get remaining requests for given IP"""
        # In debug mode, always show max limits
        if self.debug_mode:
            return {
                "hourly_remaining": self.hourly_limit,
                "daily_remaining": self.daily_limit
            }

        now = time.time()
        
        # Clean up old requests
        hourly_requests = [t for t in self.hourly_limits[ip].requests if now - t < 3600]
        daily_requests = [t for t in self.daily_limits[ip].requests if now - t < 86400]
        
        return {
            "hourly_remaining": self.hourly_limit - len(hourly_requests),
            "daily_remaining": self.daily_limit - len(daily_requests)
        }

# Create singleton instance
rate_limiter = RateLimiter()

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for static files and non-API routes
        if not request.url.path.startswith("/llm"):
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host
        
        # Check rate limit (will automatically pass if in debug mode)
        if not rate_limiter.is_allowed(client_ip):
            remaining = rate_limiter.get_remaining(client_ip)
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={
                    "X-RateLimit-Remaining-Hour": str(remaining["hourly_remaining"]),
                    "X-RateLimit-Remaining-Day": str(remaining["daily_remaining"])
                }
            )
            
        # Add rate limit headers to response
        response = await call_next(request)
        remaining = rate_limiter.get_remaining(client_ip)
        response.headers["X-RateLimit-Remaining-Hour"] = str(remaining["hourly_remaining"])
        response.headers["X-RateLimit-Remaining-Day"] = str(remaining["daily_remaining"])
        
        return response 