from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from src.backend.utils.logger import logger
from src.backend.utils.rate_limit import rate_limiter

# Create router for LLM endpoints
router = APIRouter(tags=["llm"])

# Rate limits endpoint
@router.get("/api/limits")
async def get_rate_limits(request: Request):
    """Get current rate limits without affecting the count"""
    remaining = rate_limiter.get_remaining(request.client.host)
    return JSONResponse(
        content={"message": "ok"},
        headers={
            "X-RateLimit-Remaining-Hour": str(remaining["hourly_remaining"]),
            "X-RateLimit-Remaining-Day": str(remaining["daily_remaining"])
        }
    )

# Import and include routers
from .routes import router as llm_router
from src.backend.policyfoo import init_app as init_policyfoo

# Initialize modules
init_policyfoo()

logger.info("LLM routes initialized") 