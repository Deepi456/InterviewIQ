"""AI-Powered Answer Evaluation Service using centralized Gemini Provider.

Bypasses gRPC to avoid DLL policy blocks on Windows.
"""

import json
import logging
import os
import time
from typing import Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from app.config import settings
from app.services.gemini_provider import (
    GeminiProvider,
    ProviderFailure,
    ProviderTimeoutError,
    ProviderUnavailableError,
    extract_json_from_text,
    get_gemini_provider,
)

logger = logging.getLogger(__name__)


class AnswerEvaluation(BaseModel):
    """Structured answer evaluation output from Gemini."""

    score: int = Field(..., ge=0, le=10)
    correctness: str = Field(..., description="Poor/Fair/Good/Excellent")
    relevance: str = Field(..., description="Low/Medium/High")
    completeness: str = Field(..., description="Incomplete/Partial/Moderate/Comprehensive")
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    feedback: str = Field(..., min_length=1)
    recommended_difficulty: str = Field(..., description="Easy/Medium/Hard")
    ideal_answer: Optional[str] = Field(default=None, description="Expected ideal answer")
    expected_answer: Optional[str] = Field(default=None, description="Expected ideal answer alias")
    improvement: Optional[str] = Field(default="", description="Specific actionable improvement advice")
    result: Optional[str] = Field(default=None, description="Correct/Wrong verdict")


class EvaluationService:
    """Evaluates interview answers using centralized Gemini REST Provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        http_session=None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        """Initialize evaluation service with Gemini REST Provider."""
        self.api_key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "Gemini API key not provided. Set GEMINI_API_KEY environment variable."
            )

        self.model = (settings.gemini_model or "gemini-3.5-flash").removeprefix("models/")
        self.fallback_models = [
            model.removeprefix("models/").strip()
            for model in settings.gemini_fallback_models
            if model.removeprefix("models/").strip() and model.removeprefix("models/").strip() != self.model
        ]
        self.api_base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.http = http_session
        self.sleep = sleep

        self.provider = GeminiProvider(
            api_key=self.api_key,
            http_session=http_session,
            sleep_func=sleep,
        )

        logger.info("✓ EvaluationService initialized with Gemini REST Provider (no gRPC)")

    def evaluate_answer(
        self,
        question: str,
        ideal_answer: str,
        keywords: List[str],
        candidate_answer: str,
        skill: str,
        difficulty: str,
    ) -> AnswerEvaluation:
        """Evaluate candidate answer using Gemini Provider."""
        if not candidate_answer or not candidate_answer.strip():
            return AnswerEvaluation(
                score=0,
                correctness="Poor",
                relevance="Low",
                completeness="Incomplete",
                strengths=[],
                weaknesses=["No answer provided"],
                feedback="Please provide an answer to the question.",
                improvement="Answer the question directly by defining the core concept and providing a concrete example.",
                ideal_answer=ideal_answer,
                expected_answer=ideal_answer,
                recommended_difficulty="Easy",
                result="Wrong",
            )

        prompt = self._create_evaluation_prompt(
            question, ideal_answer, keywords, candidate_answer, skill, difficulty
        )

        try:
            logger.info("Evaluating answer for skill: %s using Gemini Provider", skill)
            result = self.provider.generate_content(
                prompt,
                timeout=settings.gemini_timeout_seconds,
                max_output_tokens=1536,
                response_mime_type="application/json",
            )

            evaluation = self._parse_evaluation_response(result["text"], default_ideal_answer=ideal_answer)
            if not evaluation.ideal_answer:
                evaluation.ideal_answer = ideal_answer
            if not evaluation.expected_answer:
                evaluation.expected_answer = evaluation.ideal_answer
            if not evaluation.improvement:
                evaluation.improvement = evaluation.feedback
            logger.info("✓ Answer evaluated via Gemini. Score: %s/10 (model=%s, elapsed=%sms)",
                        evaluation.score, result.get("model"), result.get("elapsed_ms"))
            return evaluation
        except (ProviderUnavailableError, ProviderTimeoutError):
            raise
        except Exception as e:
            logger.error("Error during Gemini evaluation: %s", e)
            raise ValueError(f"Failed to evaluate answer: {str(e)}") from e

    def _call_gemini_api(
        self,
        prompt: str,
        timeout: int = 60,
        max_output_tokens: int = 1024,
        response_mime_type: Optional[str] = None,
    ) -> str:
        """Call Gemini API and return text response."""
        return self._call_gemini_api_with_metadata(
            prompt,
            timeout=timeout,
            max_output_tokens=max_output_tokens,
            response_mime_type=response_mime_type,
        )["text"]

    def _call_gemini_api_with_metadata(
        self,
        prompt: str,
        timeout: int = 60,
        max_output_tokens: int = 1024,
        response_mime_type: Optional[str] = None,
    ) -> dict:
        """Call Gemini API and return response dictionary with metadata."""
        # Update provider model configuration dynamically if settings changed (e.g. in tests)
        self.provider.primary_model = (settings.gemini_model or "gemini-3.5-flash").removeprefix("models/")
        self.provider.fallback_models = [
            m.removeprefix("models/").strip()
            for m in settings.gemini_fallback_models
            if m.removeprefix("models/").strip() and m.removeprefix("models/").strip() != self.provider.primary_model
        ]
        if self.http:
            self.provider.http = self.http
        if self.sleep:
            self.provider.sleep = self.sleep

        # If custom http_session has discovery mocked (for test compatibility), check discovery
        if self.http and hasattr(self.http, "get"):
            available = self._discover_models_safely()
            if available is not None:
                # Filter candidates by discovered catalog
                primary_avail = [self.provider.primary_model] if self.provider.primary_model in available else []
                fallbacks_avail = [m for m in self.provider.fallback_models if m in available]
                verified = primary_avail + fallbacks_avail
                if not verified:
                    raise ProviderUnavailableError([
                        ProviderFailure("unavailable_model", "No configured model supports generateContent")
                    ])

        return self.provider.generate_content(
            prompt=prompt,
            timeout=min(timeout, settings.gemini_timeout_seconds),
            max_output_tokens=max_output_tokens,
            response_mime_type=response_mime_type,
        )

    def _discover_models_safely(self) -> Optional[set]:
        """Discover models if custom http session provides GET /models."""
        try:
            resp = self.http.get(
                f"{self.api_base_url}/models",
                headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
                timeout=settings.gemini_model_discovery_timeout_seconds,
            )
            if resp is None:
                return None
            if resp.status_code in (401, 403):
                raise ProviderUnavailableError([ProviderFailure("invalid_api_key", "Gemini API key was rejected", resp.status_code)])
            if resp.status_code != 200:
                cat = "rate_limited" if resp.status_code == 429 else "provider_unavailable"
                raise ProviderUnavailableError([ProviderFailure(cat, "Gemini model discovery failed", resp.status_code)])

            models = set()
            for item in resp.json().get("models", []):
                name = str(item.get("name", "")).removeprefix("models/")
                methods = item.get("supportedGenerationMethods", [])
                if name and "generateContent" in methods:
                    models.add(name)
            return models
        except ProviderUnavailableError:
            raise
        except Exception:
            return None

    def _parse_evaluation_response(self, response_text: str, default_ideal_answer: str = "") -> AnswerEvaluation:
        """Parse Gemini's response into AnswerEvaluation."""
        try:
            eval_dict = extract_json_from_text(response_text)
            if not isinstance(eval_dict, dict):
                raise ValueError("Evaluation response is not a JSON object")

            # Fill in defaults if LLM missed optional fields
            eval_dict.setdefault("relevance", "Medium")
            eval_dict.setdefault("completeness", "Moderate")
            eval_dict.setdefault("strengths", [])
            eval_dict.setdefault("weaknesses", [])
            eval_dict.setdefault("recommended_difficulty", "Medium")
            eval_dict.setdefault("ideal_answer", default_ideal_answer)
            eval_dict.setdefault("expected_answer", eval_dict.get("ideal_answer") or default_ideal_answer)
            eval_dict.setdefault("improvement", eval_dict.get("feedback", ""))
            if "score" not in eval_dict:
                raise ValueError("Missing 'score' in evaluation response")

            eval_dict["score"] = max(0, min(10, int(eval_dict["score"])))
            return AnswerEvaluation.model_validate(eval_dict)
        except Exception as e:
            logger.error("Failed to parse evaluation response: %s (error: %s)", response_text[:200], e)
            raise ValueError(f"Invalid evaluation response format: {str(e)}") from e

    def _create_evaluation_prompt(
        self,
        question: str,
        ideal_answer: str,
        keywords: List[str],
        candidate_answer: str,
        skill: str,
        difficulty: str,
    ) -> str:
        """Create structured evaluation prompt for Gemini."""
        keywords_str = ", ".join(keywords) if keywords else "N/A"

        return f"""You are an expert technical interviewer evaluating a candidate's answer.

QUESTION: {question}

MODEL ANSWER: {ideal_answer}

KEY CONCEPTS: {keywords_str}

CANDIDATE ANSWER: {candidate_answer}

SKILL: {skill}
DIFFICULTY: {difficulty}

Evaluate this answer on a scale of 0-10 based on technical accuracy, correctness, clarity, and completeness.
Return ONLY a valid JSON object matching this exact schema:

{{
    "score": <integer from 0 to 10>,
    "correctness": "<Poor|Fair|Good|Excellent>",
    "relevance": "<Low|Medium|High>",
    "completeness": "<Incomplete|Partial|Moderate|Comprehensive>",
    "strengths": ["<specific strength observed in answer>"],
    "weaknesses": ["<specific gap or improvement area>"],
    "feedback": "<constructive, concise feedback evaluating what was good or missing in the answer>",
    "improvement": "<clear, actionable advice explaining exactly how to structure and write a better answer>",
    "ideal_answer": "<the comprehensive, accurate ideal/correct answer for this question>",
    "recommended_difficulty": "<Easy|Medium|Hard>"
}}

Be strict, objective, and fair. Do not include markdown code fences or extra text."""


_evaluation_service: Optional[EvaluationService] = None


def get_evaluation_service(api_key: Optional[str] = None) -> EvaluationService:
    """Get or create singleton EvaluationService instance."""
    global _evaluation_service
    if _evaluation_service is None or (api_key and _evaluation_service.api_key != api_key):
        _evaluation_service = EvaluationService(api_key)
    return _evaluation_service
