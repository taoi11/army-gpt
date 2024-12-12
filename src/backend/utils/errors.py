from fastapi import Request
from fastapi.responses import JSONResponse
from .logger import logger

async def error_handler(request: Request, exc: Exception):
    """Global error handler"""
    logger.error(f"Global error handler caught: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"},
    ) 