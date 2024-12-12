from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.backend.utils.logger import logger
from src.backend.pacenote import PaceNoteAgent
from .keycheck import CREDITS_AVAILABLE
from src.backend.utils.rate_limit import rate_limiter
import uuid

router = APIRouter(prefix="/llm")

class PaceNoteRequest(BaseModel):
    content: str
    temperature: Optional[float] = 0.1

class PaceNoteResponse(BaseModel):
    note: str
    remaining_requests: dict

@router.get("/credits")
async def get_credits_status():
    """Return current credit status"""
    return {"credits_available": CREDITS_AVAILABLE}

@router.post("/pace-notes/generate", response_model=PaceNoteResponse)
async def generate_pace_note(
    request: PaceNoteRequest,
    client_request: Request
):
    """Generate a pace note"""
    try:
        # Generate request ID
        request_id = str(uuid.uuid4())
        client_request.state.request_id = request_id

        note = PaceNoteAgent.generate(
            content=request.content,
            temperature=request.temperature,
            request_id=request_id
        )

        if note is None:
            raise HTTPException(
                status_code=503,
                detail="Failed to generate note. Please try again later."
            )

        # Let the middleware handle rate limit tracking
        return PaceNoteResponse(
            note=note,
            remaining_requests={
                "hourly_remaining": 0,  # Will be set by middleware
                "daily_remaining": 0
            }
        )

    except Exception as e:
        logger.error(f"Error in pace note generation endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        ) 