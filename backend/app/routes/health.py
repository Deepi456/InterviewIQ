"""
Health check routes for InterviewIQ API.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Status and service name.
    """
    return {
        "status": "healthy",
        "service": "InterviewIQ"
    }
