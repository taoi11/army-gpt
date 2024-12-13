from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from .logger import logger

# Setup templates
templates = Jinja2Templates(directory="src/frontend/templates")

# Create router for web pages
router = APIRouter(tags=["web"])

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