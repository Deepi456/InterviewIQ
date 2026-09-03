"""Job analysis service using centralized Gemini Provider.

Extracts skills and recommended interview topics from job descriptions.
Bypasses gRPC to avoid DLL policy blocks.
"""
import json
import logging
from typing import Optional

from app.config import settings
from app.models.job_models import JobAnalysisResponse, SkillModel
from app.services.gemini_provider import (
    ProviderFailure,
    ProviderTimeoutError,
    ProviderUnavailableError,
    extract_json_from_text,
    get_gemini_provider,
)

logger = logging.getLogger(__name__)


class JobAnalysisService:
    """Service for analyzing job descriptions and extracting required skills."""

    def __init__(self):
        """Initialize the service with Gemini Provider."""
        if not settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please set it before using job analysis features."
            )
        self.api_key = settings.gemini_api_key
        logger.info("✓ JobAnalysisService initialized with centralized Gemini Provider (no gRPC)")

    def analyze_job_description(
        self, job_role: str, job_description: str
    ) -> Optional[JobAnalysisResponse]:
        """Analyze a job description and extract required skills."""
        if not job_role or not job_role.strip():
            raise ValueError("Job role cannot be empty")
        if not job_description or len(job_description.strip()) < 10:
            raise ValueError("Job description must be at least 10 characters long")

        logger.info("Analyzing job description for role: %s", job_role)
        prompt = self._create_analysis_prompt(job_role, job_description)

        try:
            provider = get_gemini_provider(self.api_key)
            result = provider.generate_content(
                prompt=prompt,
                temperature=0.2,
                max_output_tokens=2048,
                response_mime_type="application/json",
                timeout=settings.gemini_timeout_seconds,
            )

            response_dict = extract_json_from_text(result["text"])
            if not isinstance(response_dict, dict):
                raise ValueError("Response is not a JSON object")

            analysis_response = JobAnalysisResponse(**response_dict)
            logger.info("Successfully analyzed job description. Found %s skills.", len(analysis_response.skills))
            return analysis_response
        except (ProviderUnavailableError, ProviderTimeoutError) as pe:
            logger.error("Job analysis provider unavailable: %s", pe)
            raise
        except ValueError as ve:
            logger.error("Job analysis validation error: %s", ve)
            raise
        except Exception as e:
            logger.error("Unexpected error during job analysis: %s", e)
            raise ValueError(f"Failed to analyze job description: {str(e)}") from e

    def _create_analysis_prompt(self, job_role: str, job_description: str) -> str:
        """Create the analysis prompt."""
        return f"""Analyze the following job description for a {job_role} position.

JOB DESCRIPTION:
{job_description}

Extract and categorize the required skills, rate their importance, and recommend interview topics.

Return ONLY a valid JSON response with this exact structure (no markdown, no code blocks):
{{
    "job_role": "{job_role}",
    "skills": [
        {{
            "name": "skill name",
            "importance": "high|medium|low",
            "category": "skill category"
        }}
    ],
    "recommended_topics": ["topic1", "topic2", "topic3"]
}}

Guidelines:
- Identify explicitly mentioned technical skills.
- Include strongly implied skills supported by the job description.
- Do NOT invent skills unrelated to the job description.
- Assign importance based on frequency and emphasis in the job description.
- Categorize skills (e.g., Programming, AI/ML, Database, Soft Skills, Tools).
- Recommended topics should be key interview subjects (usually 4-8 topics).
- Return valid JSON only, no explanation."""


_job_analysis_service: Optional[JobAnalysisService] = None


def get_job_analysis_service() -> JobAnalysisService:
    """Get or create the job analysis service singleton."""
    global _job_analysis_service
    if _job_analysis_service is None:
        _job_analysis_service = JobAnalysisService()
    return _job_analysis_service
