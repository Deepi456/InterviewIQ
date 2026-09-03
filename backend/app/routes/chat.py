"""InterviewIQ AI Coach API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_current_user
from app.models.chat_models import ChatRequest, ChatResponse
from app.services.chat_service import get_chat_service
from app.services.gemini_provider import ProviderTimeoutError, ProviderUnavailableError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["ai-coach"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, current_user=Depends(require_current_user)):
    """Generate a secure conversational AI Coach response."""
    try:
        result = get_chat_service().respond(
            message=request.message,
            conversation_id=request.conversation_id,
            session_id=request.session_id,
            mode=request.mode,
            user_id=current_user["id"] if current_user else None,
        )
        return ChatResponse(**result)
    except HTTPException:
        raise
    except ProviderTimeoutError as exc:
        logger.warning("AI Coach request timed out: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "code": "AI_TIMEOUT",
                "message": "AI response timed out. Please try again.",
            },
        ) from exc
    except ProviderUnavailableError as exc:
        logger.warning("AI Coach provider unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "AI_PROVIDER_UNAVAILABLE",
                "message": "AI service is temporarily unavailable. Please try again.",
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.exception("AI Coach runtime failure: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "AI_PROVIDER_UNAVAILABLE",
                "message": "AI service is temporarily unavailable. Please try again.",
            },
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected AI Coach error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "AI_PROVIDER_UNAVAILABLE",
                "message": "AI service is temporarily unavailable. Please try again.",
            },
        ) from exc
