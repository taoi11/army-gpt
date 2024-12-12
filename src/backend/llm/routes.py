from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from src.backend.utils.rate_limit import rate_limiter
from src.backend.utils.logger import logger
from src.backend.pacenote import pace_note_agent

router = APIRouter()

class PaceNoteRequest(BaseModel):
    content: str
    temperature: Optional[float] = 0.1

class PaceNoteResponse(BaseModel):
    note: str
    remaining_requests: dict

def get_client_ip(request: Request) -> str:
    """Get client IP from request"""
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0]
    return request.client.host

def check_rate_limit(request: Request):
    """Dependency to check rate limit"""
    client_ip = get_client_ip(request)
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    return client_ip

@router.post("/pace-notes/generate", response_model=PaceNoteResponse)
async def generate_pace_note(
    request: PaceNoteRequest,
    client_ip: str = Depends(check_rate_limit)
):
    """Generate a pace note"""
    try:
        # Generate note using the pace note agent
        note = pace_note_agent.generate(
            content=request.content,
            temperature=request.temperature
        )

        if note is None:
            raise HTTPException(
                status_code=503,
                detail="Failed to generate note. Please try again later."
            )

        # Get remaining requests
        remaining = rate_limiter.get_remaining(client_ip)

        return PaceNoteResponse(
            note=note,
            remaining_requests=remaining
        )

    except Exception as e:
        logger.error(f"Error in pace note generation endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        ) 