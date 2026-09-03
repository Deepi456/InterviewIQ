"""
Main FastAPI application for InterviewIQ.
Handles routing, CORS configuration, and health checks.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import health, job, interview, report, chat, auth, resume
from app.database import init_database
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-Powered Adaptive Career & Interview Coach"
)

# Configure CORS middleware to allow React frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    """Initialize database on application startup."""
    try:
        init_database()
        logger.info("✓ Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        if settings.app_env == "production":
            raise

# Include routes
app.include_router(health.router)
app.include_router(job.router)
app.include_router(interview.router)
app.include_router(report.router)
app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(resume.router)


@app.get("/")
def read_root():
    """
    Root endpoint.
    
    Returns:
        dict: Simple message indicating the API is running.
    """
    return {"message": "InterviewIQ API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
