from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
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

# Setup templates
templates = Jinja2Templates(directory="src/frontend/templates")

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

# Root route
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Pace notes route
@app.get("/pace-notes", response_class=HTMLResponse)
async def pace_notes(request: Request):
    return templates.TemplateResponse("pace-notes.html", {"request": request})

# Import and include routers
from .routes import router as pace_notes_router

app.include_router(pace_notes_router)

logger.info("FastAPI application initialized with rate limiting") 