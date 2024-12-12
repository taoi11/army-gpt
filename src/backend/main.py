from src.backend.api import app
from src.backend.api.routes import router
from src.backend.api.middleware import error_handler
from src.backend.utils.logger import logger

# Add error handler
app.add_exception_handler(Exception, error_handler)

# Include routes
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Army-GPT server")
    uvicorn.run(app, host="0.0.0.0", port=8020) 