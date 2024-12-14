from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .logger import logger
from .cost import cost_tracker

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

# Create router for web pages
router = APIRouter(tags=["web"])

# Create router for API endpoints
api_router = APIRouter(prefix="/api", tags=["api"])

@api_router.get("/costs")
async def get_costs():
    """Get current costs for API usage and server rent"""
    costs = cost_tracker.get_current_costs()
    logger.debug(f"Returning costs: {costs}")  # Debug log
    return JSONResponse(content=costs)

@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main landing page"""
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/pace-notes", response_class=HTMLResponse)
async def pace_notes_page(request: Request):
    """Serve the pace notes page"""
    return templates.TemplateResponse("pace-notes.html", {"request": request})

@router.get("/policy-foo", response_class=HTMLResponse)
async def policy_foo_page(request: Request):
    """Serve the policy foo page"""
    return templates.TemplateResponse("policy-foo.html", {"request": request})

# Include both routers
app.include_router(router)
app.include_router(api_router) 