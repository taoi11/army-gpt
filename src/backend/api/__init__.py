from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.backend.utils.metrics import MetricsMiddleware
from src.backend.utils.logger import logger

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

# Add metrics middleware
app.add_middleware(MetricsMiddleware)

# Mount static files using container path
app.mount("/static", StaticFiles(directory="/app/static"), name="static")

logger.info("FastAPI application initialized") 