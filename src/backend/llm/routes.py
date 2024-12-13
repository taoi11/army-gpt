from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
from src.backend.utils.logger import logger
from src.backend.pacenote import PaceNoteAgent
from .keycheck import CREDITS_AVAILABLE
from src.backend.utils.rate_limit import rate_limiter
import uuid
import json

router = APIRouter(prefix="/llm")

class PaceNoteRequest(BaseModel):
    content: str
    temperature: Optional[float] = 0.1
    stream: Optional[bool] = True  # Default to streaming for Ollama

class PaceNoteResponse(BaseModel):
    note: str
    remaining_requests: dict

class PolicyFooRequest(BaseModel):
    content: str
    temperature: Optional[float] = 0.1
    stream: Optional[bool] = False  # Default to non-streaming for policy-foo

@router.get("/credits")
async def get_credits_status():
    """Return current credit status"""
    return {"credits_available": CREDITS_AVAILABLE}

@router.post("/pace-notes/generate")
async def generate_pace_note(
    request: PaceNoteRequest,
    client_request: Request
):
    """Generate a pace note"""
    try:
        # Generate request ID
        request_id = str(uuid.uuid4())
        client_request.state.request_id = request_id

        # Get rate limit info
        rate_limits = rate_limiter.get_remaining(client_request.client.host)

        if request.stream:
            # Generate streaming response
            stream = PaceNoteAgent.generate(
                content=request.content,
                temperature=request.temperature,
                request_id=request_id,
                stream=True
            )

            async def stream_generator():
                try:
                    async for chunk in stream:
                        # Format each chunk as a Server-Sent Event
                        yield f"data: {json.dumps({'note': chunk, 'remaining_requests': rate_limits})}\n\n"
                except Exception as e:
                    logger.error(f"Error in stream generator: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream"
            )

        # Non-streaming response
        note = PaceNoteAgent.generate(
            content=request.content,
            temperature=request.temperature,
            request_id=request_id,
            stream=False
        )

        if note is None:
            raise HTTPException(
                status_code=503,
                detail="Failed to generate note. Please try again later."
            )

        return PaceNoteResponse(
            note=note,
            remaining_requests=rate_limits
        )

    except Exception as e:
        logger.error(f"Error in pace note generation endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        ) 

@router.post("/pace-notes/cancel")
async def cancel_generation(request: Request):
    """Cancel any ongoing generation for this client"""
    try:
        # Return 200 immediately to allow quick page refreshes
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Error in cancel endpoint: {str(e)}")
        return Response(status_code=200)  # Still return 200 to allow quick refresh 

@router.post("/policyfoo/generate")
async def generate_policy_response(
    request: PolicyFooRequest,
    client_request: Request
):
    """Generate policy response using the policy finder and chat agents"""
    try:
        # Get client IP and generate request ID
        client_ip = client_request.client.host
        request_id = str(uuid.uuid4())
        
        # Initialize response
        response = None
        remaining = {"hourly_remaining": 0, "daily_remaining": 0}
        
        try:
            # Import policy agents here to avoid circular imports
            from src.backend.policyfoo.finder import policy_finder
            from src.backend.policyfoo.reader import policy_reader
            from src.backend.policyfoo.chat import chat_agent
            
            # Step 1: Find relevant policies
            policy_refs = await policy_finder.find_relevant_policies(
                query=request.content,
                request_id=request_id
            )
            
            if not policy_refs:
                logger.warning("No relevant policies found")
                return JSONResponse(
                    content={
                        "content": "<response><answer>I couldn't find any relevant policies for your query. Could you please rephrase or provide more details?</answer><citations></citations><follow_up>Try asking about a specific policy area?</follow_up></response>",
                        "remaining_requests": remaining
                    },
                    headers={
                        "X-RateLimit-Remaining-Hour": str(remaining["hourly_remaining"]),
                        "X-RateLimit-Remaining-Day": str(remaining["daily_remaining"])
                    }
                )
            
            # Step 2: Get policy content with parallel processing
            policy_contents = await policy_reader.get_policy_content(
                policy_numbers=policy_refs,
                query=request.content,
                request_id=request_id,
                temperature=request.temperature,
                parallel=True  # Use parallel processing as specified in YAML
            )
            
            if not policy_contents:
                logger.warning("Failed to extract policy content")
                return JSONResponse(
                    content={
                        "content": "<response><answer>I found some relevant policies but couldn't extract their content. Please try again.</answer><citations></citations><follow_up>Maybe try rephrasing your question?</follow_up></response>",
                        "remaining_requests": remaining
                    },
                    headers={
                        "X-RateLimit-Remaining-Hour": str(remaining["hourly_remaining"]),
                        "X-RateLimit-Remaining-Day": str(remaining["daily_remaining"])
                    }
                )
            
            # Step 3: Generate chat response using first policy content
            # TODO: In future, combine multiple policy contents
            first_policy = next(iter(policy_contents.values()))
            response = await chat_agent.generate_response(
                query=request.content,
                policy_content=first_policy,
                request_id=request_id,
                temperature=request.temperature
            )
            
        except Exception as e:
            logger.error(f"Error generating policy response: {str(e)}")
            response = f"Error: {str(e)}"
        
        # Only check rate limits if we got a successful response and using OpenRouter
        if CREDITS_AVAILABLE and response and not response.startswith("Error:"):
            # is_allowed() will add the request if allowed
            if not rate_limiter.is_allowed(client_ip, request_id):
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded"
                )
            remaining = rate_limiter.get_remaining(client_ip)
        
        return JSONResponse(
            content={
                "content": response,
                "remaining_requests": remaining
            },
            headers={
                "X-RateLimit-Remaining-Hour": str(remaining["hourly_remaining"]),
                "X-RateLimit-Remaining-Day": str(remaining["daily_remaining"])
            }
        )

    except Exception as e:
        logger.error(f"Error in policy-foo generation endpoint: {str(e)}")
        # Get rate limits even in error case
        try:
            remaining = rate_limiter.get_remaining(client_request.client.host)
            headers = {
                "X-RateLimit-Remaining-Hour": str(remaining["hourly_remaining"]),
                "X-RateLimit-Remaining-Day": str(remaining["daily_remaining"])
            }
        except:
            headers = {}
            
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
            headers=headers
        )