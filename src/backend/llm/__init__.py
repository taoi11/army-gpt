from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from src.backend.utils.monitoring import MetricsMiddleware
from src.backend.utils.logger import logger
from src.backend.utils.errors import error_handler
from src.backend.utils.rate_limit import RateLimitMiddleware, rate_limiter
from src.backend.utils.web import router as web_router

# Initialize FastAPI app
app = FastAPI(
    title="Army-GPT",
    description="Collection of AI tools and agents for army dudes",
    version="1.0.0"
)

# Setup templates
templates = Jinja2Templates(directory="src/frontend/templates")

# Setup static files
app.mount("/static", StaticFiles(directory="src/frontend/static"), name="static")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Add metrics middleware
app.add_middleware(MetricsMiddleware)

# Add error handler
app.add_exception_handler(Exception, error_handler)

# Rate limits endpoint
@app.get("/api/limits")
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

# Include routers
app.include_router(web_router)  # Add web routes first
app.include_router(llm_router)

logger.info("FastAPI application initialized with rate limiting") 