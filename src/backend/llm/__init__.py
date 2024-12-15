from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from src.backend.utils.logger import logger
from src.backend.utils.rate_limit import rate_limiter

# Create router for LLM endpoints
router = APIRouter()

# Import and include routers
from .routes import router as llm_router

# Include the LLM routes
router.include_router(llm_router, prefix="/llm", tags=["llm"])

# Initialize modules
from src.backend.policyfoo import init_app as init_policyfoo
init_policyfoo()

logger.info("LLM routes initialized") 