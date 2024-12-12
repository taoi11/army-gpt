from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.backend.utils.monitoring import MetricsMiddleware
from src.backend.utils.logger import logger
from src.backend.utils.errors import error_handler
from src.backend.utils.rate_limit import RateLimitMiddleware

# Initialize FastAPI app
app = FastAPI(
    title="Army-GPT",
    description="Collection of AI tools and agents for army dudes",
    version="1.0.0"
)

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

# Mount static files
app.mount("/static", StaticFiles(directory="src/frontend/static"), name="static")

# Import and include main router
from .routes import router
app.include_router(router)

logger.info("FastAPI application initialized with rate limiting") 