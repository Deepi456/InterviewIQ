"""Conversational InterviewIQ AI Coach service."""

import json
import logging
import sqlite3
import threading
import time
import uuid
from typing import Dict, List, Optional

from app.config import settings
from app.database import DB_PATH
from app.services.gemini_provider import (
    GeminiProvider,
    ProviderFailure,
    ProviderTimeoutError,
    ProviderUnavailableError,
    get_gemini_provider,
)
from app.services.question_repository import get_question_repository

try:
    from langchain_core.messages import AIMessage, HumanMessage
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.runnables import RunnableLambda
    LANGCHAIN_AVAILABLE = True
except ImportError:
    AIMessage = HumanMessage = MessagesPlaceholder = ChatPromptTemplate = RunnableLambda = None
    LANGCHAIN_AVAILABLE = False

logger = logging.getLogger(__name__)

COACH_MAX_OUTPUT_TOKENS = 2048
COACH_TIMEOUT_SECONDS = 25

SYSTEM_PROMPT = """You are InterviewIQ AI Coach, an expert interview preparation assistant.

Help candidates prepare for technical and behavioral interviews, explain concepts clearly,
generate realistic practice questions, give constructive feedback, and adapt difficulty.
Use practical interview-focused guidance and structured answers when useful.
Never invent interview results or claim access to information that was not provided.
Clearly distinguish general advice from personalized performance insights.
If interview context is supplied, use it precisely and explain what the data supports.

For mock interview mode, act as an interviewer: ask one question at a time, wait for the
candidate answer, give brief actionable feedback, then ask the next question. Track the
question count in the conversation and provide a concise completion summary at the end.

Answer the user's actual question first and stay relevant. Be concise but complete: never
stop mid-sentence or return an unfinished answer. Organize detailed answers with short
headings, bullets, or numbered steps. For technical questions, prioritize correctness. For
coding questions, provide working code and a useful example or output. Use conversation
context for follow-ups and do not repeat generic introductions. If ambiguous, ask one short
clarification instead of guessing. When a follow-up uses words such as "it", "this", or
"the first question", resolve them from the most recent relevant exchange instead of asking
the user to repeat the topic. Keep normal answers under 450 words unless code requires more.
Before sending, check that the answer ends cleanly and includes every requested part. Do not
mention APIs, prompts, models, or system details."""


class ChatService:
    """Maintains short-lived conversation memory and calls Gemini securely."""

    def __init__(self, database_path: str = str(DB_PATH)):
        self.database_path = database_path
        self._conversations: Dict[str, List[Dict[str, str]]] = {}
        self._conversation_owners: Dict[str, Optional[str]] = {}
        self._lock = threading.Lock()
        self.provider = get_gemini_provider()

    def respond(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        mode: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict:
        message = message.strip()
        if not message:
            raise ValueError("Message cannot be empty")

        conversation_id = conversation_id or str(uuid.uuid4())
        owner = self._conversation_owners.get(conversation_id)
        if owner is not None and owner != user_id:
            raise ValueError("Conversation not found")
        self._conversation_owners.setdefault(conversation_id, user_id)
        mode = self._resolve_mode(message, mode)
        context = self._get_interview_context(session_id, user_id) if mode == "performance_analysis" else None

        with self._lock:
            history = self._conversations.setdefault(conversation_id, [])
            history.append({"role": "user", "text": message})
            history = history[-18:]
            self._conversations[conversation_id] = history

        request_started = time.perf_counter()
        result = None
        try:
            for attempt in range(2):
                logger.info(
                    "AI Coach request started attempt=%s mode=%s history_items=%s",
                    attempt + 1,
                    mode,
                    len(history),
                )
                result = self._invoke_langchain(
                    history, context, mode, retry=attempt == 1
                )
                if isinstance(result, str):
                    result = {"text": result, "finish_reason": None}
                if self._is_complete_response(result):
                    break
                logger.warning(
                    "AI Coach incomplete provider response attempt=%s finish_reason=%s chars=%s",
                    attempt + 1,
                    result.get("finish_reason"),
                    len(result.get("text", "")),
                )
            else:
                raise RuntimeError("AI Coach returned an incomplete response")
        except (ProviderUnavailableError, ProviderTimeoutError) as exc:
            logger.error(
                "AI Coach provider failure elapsed_ms=%s: %s",
                round((time.perf_counter() - request_started) * 1000),
                exc,
            )
            # Safe local fallback for practice questions when Gemini is unreachable
            if mode == "practice_questions" or "practice question" in message.lower():
                fallback_text = self._get_local_practice_questions_fallback(message)
                if fallback_text:
                    with self._lock:
                        history.append({"role": "assistant", "text": fallback_text})
                        self._conversations[conversation_id] = history[-18:]
                    return {
                        "success": True,
                        "response": fallback_text,
                        "conversation_id": conversation_id,
                        "suggestions": self._suggestions_for(mode),
                        "mode": mode,
                    }

            with self._lock:
                if history and history[-1]["role"] == "user":
                    history.pop()
            raise
        except Exception as exc:
            logger.error(
                "AI Coach request failed elapsed_ms=%s error_type=%s",
                round((time.perf_counter() - request_started) * 1000),
                type(exc).__name__,
            )
            with self._lock:
                if history and history[-1]["role"] == "user":
                    history.pop()
            raise RuntimeError("AI Coach is temporarily unavailable") from exc

        response = result["text"].strip()
        logger.info(
            "AI Coach request completed elapsed_ms=%s response_chars=%s fallback_used=%s",
            round((time.perf_counter() - request_started) * 1000),
            len(response),
            result.get("fallback_used", not LANGCHAIN_AVAILABLE),
        )
        if not response:
            with self._lock:
                if history and history[-1]["role"] == "user":
                    history.pop()
            raise RuntimeError("AI Coach returned an empty response")

        with self._lock:
            history.append({"role": "assistant", "text": response})
            self._conversations[conversation_id] = history[-18:]

        return {
            "success": True,
            "response": response,
            "conversation_id": conversation_id,
            "suggestions": self._suggestions_for(mode),
            "mode": mode,
        }

    def _invoke_langchain(
        self,
        history: List[Dict[str, str]],
        context: Optional[Dict],
        mode: str,
        retry: bool = False,
    ) -> Dict:
        """Invoke Gemini through LangChain or direct provider."""
        provider = get_gemini_provider()
        prompt_str = self._build_prompt(history, context, mode)

        if not LANGCHAIN_AVAILABLE:
            rest_result = provider.generate_content(
                prompt_str,
                timeout=COACH_TIMEOUT_SECONDS,
                max_output_tokens=COACH_MAX_OUTPUT_TOKENS,
            )
            rest_result["fallback_used"] = True
            return rest_result

        context_text = json.dumps(context, ensure_ascii=True) if context else "No InterviewIQ report context is available."
        retry_text = " Previous output was incomplete. Answer more concisely and finish every requested item." if retry else ""
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"{SYSTEM_PROMPT}{retry_text}\n\nCURRENT MODE: {{mode}}\nINTERVIEWIQ CONTEXT:\n{{context}}"),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{message}"),
        ])
        messages = []
        for item in history[:-1]:
            messages.append(
                HumanMessage(content=item["text"])
                if item["role"] == "user"
                else AIMessage(content=item["text"])
            )
        latest_message = history[-1]["text"]
        chain = prompt | RunnableLambda(
            lambda prompt_value: provider.generate_content(
                prompt_value.to_string(),
                timeout=COACH_TIMEOUT_SECONDS,
                max_output_tokens=COACH_MAX_OUTPUT_TOKENS,
            )
        )
        result = chain.invoke({
            "mode": mode,
            "context": context_text,
            "history": messages[-16:],
            "message": latest_message,
        })
        result["fallback_used"] = False
        return result

    @staticmethod
    def _is_complete_response(result: Dict) -> bool:
        text = result.get("text", "").strip()
        finish_reason = (result.get("finish_reason") or "").upper()
        incomplete_reasons = {"MAX_TOKENS", "LENGTH", "MAX_OUTPUT_TOKENS"}
        return bool(text) and not any(reason in finish_reason for reason in incomplete_reasons) and not text.endswith("...") and text.count("```") % 2 == 0

    def _build_prompt(self, history: List[Dict[str, str]], context: Optional[Dict], mode: str) -> str:
        transcript = "\n".join(
            f"{item['role'].upper()}: {item['text']}"
            for item in history
        )
        context_text = json.dumps(context, ensure_ascii=True) if context else "No InterviewIQ report context is available."
        return f"""{SYSTEM_PROMPT}

CURRENT MODE: {mode}
INTERVIEWIQ CONTEXT:
{context_text}

CONVERSATION:
{transcript}

Respond to the latest user message. Do not invent missing context."""

    def _get_interview_context(self, session_id: Optional[str], user_id: Optional[str]) -> Optional[Dict]:
        if not session_id:
            return None

        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        try:
            session = conn.execute(
                "SELECT job_role, skills_json, total_questions, status FROM interview_sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            if not session:
                return None

            context = {
                "job_role": session["job_role"],
                "skills": json.loads(session["skills_json"] or "[]"),
                "total_questions": session["total_questions"],
                "status": session["status"],
            }
            report = conn.execute(
                "SELECT report_json FROM interview_reports WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if report and report["report_json"]:
                cached_report = json.loads(report["report_json"])
                context["report"] = {
                    "overall_score": cached_report.get("overall_score"),
                    "performance_level": cached_report.get("performance_level"),
                    "skill_scores": cached_report.get("skill_scores", []),
                    "strengths": cached_report.get("strengths", []),
                    "weak_areas": cached_report.get("weak_areas", []),
                    "recommendations": cached_report.get("recommendations", []),
                }
            return context
        finally:
            conn.close()

    def _get_local_practice_questions_fallback(self, message: str) -> Optional[str]:
        """Provide safe local curated practice questions when Gemini is unavailable."""
        try:
            repo = get_question_repository()
            # Detect skill from message
            matched_skill = None
            for skill in ["Python", "SQL", "Machine Learning", "Data Structures", "System Design", "Statistics"]:
                if skill.lower() in message.lower():
                    matched_skill = skill
                    break

            questions = []
            if matched_skill:
                for diff in ["Easy", "Medium", "Hard"]:
                    q = repo.get_random_question(skill=matched_skill, difficulty=diff)
                    if q and q not in questions:
                        questions.append(q)
            else:
                for _ in range(3):
                    q = repo.get_random_question()
                    if q and q not in questions:
                        questions.append(q)

            if not questions:
                return None

            lines = ["Here are curated practice questions from the InterviewIQ question bank:\n"]
            for idx, q in enumerate(questions[:3], start=1):
                lines.append(f"### {idx}. {q.question}")
                lines.append(f"**Skill**: {q.skill} | **Difficulty**: {q.difficulty}")
                if q.keywords:
                    lines.append(f"**Key concepts to cover**: {', '.join(q.keywords[:4])}\n")
            lines.append("Try answering one of these questions, or ask for hints and explanations!")
            return "\n".join(lines)
        except Exception as e:
            logger.warning("Local question bank fallback failed: %s", e)
            return None

    @staticmethod
    def _resolve_mode(message: str, mode: Optional[str]) -> str:
        if mode:
            return mode.lower()
        lowered = message.lower()
        if "mock interview" in lowered:
            return "mock_interview"
        if any(word in lowered for word in ("score", "performance", "report", "weak")):
            return "performance_analysis"
        if any(word in lowered for word in ("practice question", "give me questions", "practice python", "practice sql")):
            return "practice_questions"
        if any(word in lowered for word in ("test me", "quiz me", "ask me a question")):
            return "test_me"
        if any(word in lowered for word in ("explain", "what is", "concept", "example")):
            return "concept_explanation"
        if any(word in lowered for word in ("behavioral", "tell me about yourself")):
            return "behavioral_preparation"
        return "general_coach"

    @staticmethod
    def _suggestions_for(mode: str) -> List[str]:
        if mode == "mock_interview":
            return ["Make it harder", "Give me feedback", "End mock interview"]
        if mode == "performance_analysis":
            return ["Create a practice plan", "Give me practice questions", "Explain with an example"]
        if mode == "practice_questions":
            return ["Give me practice questions", "Explain with an example", "Test me"]
        return ["Give me practice questions", "Explain with an example", "Test me"]


_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
