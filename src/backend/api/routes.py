from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main landing page"""
    with open("src/frontend/static/index.html", "r") as f:
        return f.read()

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"} 