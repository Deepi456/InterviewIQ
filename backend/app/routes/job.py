"""
Job analysis routes for InterviewIQ API.
Handles job description analysis and skill extraction.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.auth import require_current_user
from app.models.job_models import JobAnalysisRequest, JobAnalysisResponse
from app.services.job_analysis_service import get_job_analysis_service

router = APIRouter(prefix="/api/job", tags=["job"])


@router.post("/analyze", response_model=JobAnalysisResponse)
async def analyze_job_description(request: JobAnalysisRequest, current_user=Depends(require_current_user)):
    """
    Analyze a job description and extract required skills.
    
    Args:
        request: JobAnalysisRequest containing job_role and job_description
    
    Returns:
        JobAnalysisResponse with extracted skills and recommended topics
    
    Raises:
        HTTPException 400: If inputs are invalid
        HTTPException 500: If API call fails
    """
    try:
        # Get the job analysis service
        service = get_job_analysis_service()
        
        # Analyze the job description
        analysis_result = service.analyze_job_description(
            job_role=request.job_role,
            job_description=request.job_description
        )
        
        return analysis_result
    
    except ValueError as ve:
        # Handle validation or API errors
        raise HTTPException(
            status_code=400,
            detail=str(ve)
        )
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze job description: {str(e)}"
        )
