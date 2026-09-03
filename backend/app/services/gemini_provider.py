"""Centralized Google Gemini REST Provider for InterviewIQ.

Provides reliable, resilient LLM interactions with:
- Configurable model fallback chain (primary -> fallback_1 -> fallback_2)
- Strict per-request timeout budgets
- Limited exponential backoff for transient errors (429, 500, 503, timeouts)
- Thread-safe model catalog discovery with TTL caching (bypasses redundant network calls)
- Pure REST implementation (avoids Windows gRPC / DLL policy issues)
"""

import json
import logging
import os
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Union

import requests
from app.config import settings

logger = logging.getLogger(__name__)


class ProviderFailure(Exception):
    """Represents a failure from a specific Gemini model attempt."""

    def __init__(
        self,
        category: str,
        message: str,
        status: Optional[int] = None,
        model: Optional[str] = None,
    ):
        super().__init__(message)
        self.category = category  # e.g., 'quota_or_rate_limit', 'overloaded', 'timeout', 'invalid_api_key', 'unavailable_model'
        self.message = message
        self.status = status
        self.model = model

    def __repr__(self) -> str:
        return f"ProviderFailure(category={self.category!r}, status={self.status!r}, model={self.model!r})"


class ProviderUnavailableError(Exception):
    """Raised when all candidate Gemini models fail or are unreachable."""

    def __init__(self, failures: List[ProviderFailure]):
        self.failures = failures
        summary = "; ".join(f"[{f.model or 'unknown'}: {f.category} ({f.status or 'N/A'})]" for f in failures)
        super().__init__(f"All Gemini candidate models failed: {summary}")


class ProviderTimeoutError(ProviderUnavailableError):
    """Raised when an AI request exceeds its configured timeout budget."""

    def __init__(
        self,
        message: str = "AI response timed out. Please try again.",
        failures: Optional[List[ProviderFailure]] = None,
    ):
        self.failures = failures or [ProviderFailure("timeout", message)]
        super().__init__(self.failures)


def extract_json_from_text(text: str) -> Union[Dict, List]:
    """Robust JSON extraction from LLM response text."""
    trimmed = text.strip()
    if trimmed.startswith("```"):
        # Strip markdown code fencing (e.g. ```json ... ```)
        trimmed = re.sub(r"^```(?:json)?\s*", "", trimmed)
        trimmed = re.sub(r"\s*```$", "", trimmed)

    # First direct parse attempt
    try:
        return json.loads(trimmed)
    except json.JSONDecodeError:
        pass

    # Try to find the first '{' and matching '}'
    if "{" in trimmed and "}" in trimmed:
        start = trimmed.find("{")
        end = trimmed.rfind("}") + 1
        try:
            return json.loads(trimmed[start:end])
        except json.JSONDecodeError:
            pass

    # Try to find '[' and ']'
    if "[" in trimmed and "]" in trimmed:
        start = trimmed.find("[")
        end = trimmed.rfind("]") + 1
        try:
            return json.loads(trimmed[start:end])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON found in response: {text[:200]}...")


class GeminiProvider:
    """Centralized, resilient provider for Google Gemini models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        http_session=None,
        sleep_func: Callable[[float], None] = time.sleep,
    ):
        self.api_key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self.primary_model = (settings.gemini_model or "gemini-3.5-flash").removeprefix("models/")
        self.fallback_models = [
            m.removeprefix("models/").strip()
            for m in settings.gemini_fallback_models
            if m.removeprefix("models/").strip() and m.removeprefix("models/").strip() != self.primary_model
        ]
        self.api_base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.http = http_session or requests
        self.sleep = sleep_func

        # Cache for discovered models to prevent extra network roundtrips per call
        self._discovered_models: Optional[Set[str]] = None
        self._discovered_at: float = 0.0
        self._discovery_ttl_seconds: float = 600.0  # 10 minutes cache
        self._lock = threading.Lock()

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

    def _discover_models(self) -> Optional[Set[str]]:
        """Query supported model catalog once and cache results."""
        now = time.monotonic()
        if self._discovered_models is not None and (now - self._discovered_at) < self._discovery_ttl_seconds:
            return self._discovered_models

        with self._lock:
            if self._discovered_models is not None and (now - self._discovered_at) < self._discovery_ttl_seconds:
                return self._discovered_models
            try:
                disc_timeout = min(5.0, float(getattr(settings, "gemini_model_discovery_timeout_seconds", 5)))
                url = f"{self.api_base_url}/models"
                response = self.http.get(url, headers=self._headers(), timeout=disc_timeout)
                if response is None:
                    return None
                status = getattr(response, "status_code", None)
                if status in (401, 403):
                    raise ProviderFailure("invalid_api_key", "Gemini API key rejected during discovery", status=status)
                if getattr(response, "ok", False):
                    data = response.json()
                    models = {
                        item["name"].removeprefix("models/")
                        for item in data.get("models", [])
                        if "generateContent" in item.get("supportedGenerationMethods", [])
                    }
                    self._discovered_models = models
                    self._discovered_at = now
                    return models
            except ProviderFailure:
                raise
            except Exception as exc:
                logger.debug("Gemini model discovery skipped/failed: %s", exc)
        return None

    def _get_candidate_models(self) -> List[str]:
        """Get ordered list of candidate models to attempt (primary -> fallbacks)."""
        candidates = [self.primary_model] + self.fallback_models
        unique_candidates = list(dict.fromkeys(c for c in candidates if c))
        discovered = self._discover_models()
        if discovered:
            filtered = [m for m in unique_candidates if m in discovered]
            if filtered:
                return filtered
        return unique_candidates

    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 1536,
        response_mime_type: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Execute a generation request across configured candidate models with automatic fallback.

        Returns:
            Dict containing text, model, elapsed_ms, finish_reason, candidates count.
        """
        if not self.api_key:
            raise ProviderUnavailableError([
                ProviderFailure("invalid_api_key", "Gemini API key is not configured.")
            ])

        total_timeout = timeout or settings.gemini_timeout_seconds
        deadline = time.monotonic() + total_timeout
        failures: List[ProviderFailure] = []

        try:
            candidate_models = self._get_candidate_models()
        except ProviderFailure as pf:
            raise ProviderUnavailableError([pf])

        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        if response_mime_type:
            payload["generationConfig"]["responseMimeType"] = response_mime_type

        # Split remaining timeout budget across candidate models
        num_candidates = max(1, len(candidate_models))

        for idx, model in enumerate(candidate_models):
            remaining_total = deadline - time.monotonic()
            if remaining_total <= 0:
                failures.append(ProviderFailure("timeout", "Overall request deadline exceeded", model=model))
                break

            per_model_timeout = max(4.0, remaining_total / (num_candidates - idx))
            per_model_timeout = min(remaining_total, per_model_timeout)

            try:
                result = self._request_model_with_retry(
                    model=model,
                    payload=payload,
                    timeout=per_model_timeout,
                    deadline=deadline,
                    max_attempts=settings.gemini_retry_attempts + 1,
                )
                return result
            except ProviderFailure as failure:
                failures.append(failure)
                if failure.category == "invalid_api_key":
                    # Auth error is terminal for all models
                    break
                logger.warning(
                    "Gemini model '%s' failed (category=%s, status=%s). Attempting next model if available.",
                    model, failure.category, failure.status
                )

        # All candidate models failed
        timeout_only = failures and all(f.category == "timeout" for f in failures)
        if timeout_only:
            raise ProviderTimeoutError("AI response timed out. Please try again.", failures=failures)
        raise ProviderUnavailableError(failures)

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
        timeout: Optional[float] = None,
    ) -> Union[Dict, List]:
        """Execute request and parse returned structured JSON."""
        result = self.generate_content(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
            timeout=timeout,
        )
        return extract_json_from_text(result["text"])

    def _request_model_with_retry(
        self,
        model: str,
        payload: Dict[str, Any],
        timeout: float,
        deadline: float,
        max_attempts: int,
    ) -> Dict[str, Any]:
        """Execute request against a specific model with bounded exponential backoff."""
        url = f"{self.api_base_url}/models/{model}:generateContent"

        for attempt in range(max_attempts):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProviderFailure("timeout", "Deadline exceeded before attempt", model=model)

            attempt_timeout = min(timeout, remaining)
            started = time.perf_counter()

            try:
                response = self.http.post(
                    url,
                    json=payload,
                    headers=self._headers(),
                    timeout=attempt_timeout,
                )
            except requests.Timeout as exc:
                logger.warning("Gemini timeout for model=%s attempt=%s/%s", model, attempt + 1, max_attempts)
                if attempt + 1 < max_attempts and (deadline - time.monotonic()) > 0.05:
                    self._backoff(attempt)
                    continue
                raise ProviderFailure("timeout", f"Gemini request timed out on model {model}", model=model) from exc
            except requests.RequestException as exc:
                logger.warning("Gemini network error for model=%s attempt=%s/%s: %s", model, attempt + 1, max_attempts, exc)
                if attempt + 1 < max_attempts and (deadline - time.monotonic()) > 0.05:
                    self._backoff(attempt)
                    continue
                raise ProviderFailure("provider_unreachable", f"Gemini unreachable on model {model}: {exc}", model=model) from exc

            status = response.status_code
            elapsed_ms = round((time.perf_counter() - started) * 1000)

            if status in (401, 403):
                raise ProviderFailure("invalid_api_key", "Gemini API key rejected", status=status, model=model)

            if status == 404:
                # Model not found / deprecated
                raise ProviderFailure("unavailable_model", f"Model '{model}' not found (404)", status=status, model=model)

            if status in (429, 500, 502, 503):
                category = "quota_or_rate_limit" if status == 429 else "overloaded"
                logger.warning(
                    "Gemini transient status=%s model=%s attempt=%s/%s elapsed_ms=%s",
                    status, model, attempt + 1, max_attempts, elapsed_ms
                )
                if attempt + 1 < max_attempts and (deadline - time.monotonic()) > 0.05:
                    self._backoff(attempt)
                    continue
                raise ProviderFailure(category, f"Gemini model '{model}' returned status {status}", status=status, model=model)

            if not response.ok:
                raise ProviderFailure("provider_error", f"Gemini returned status {status}: {response.text[:200]}", status=status, model=model)

            try:
                data = response.json()
            except Exception as exc:
                raise ProviderFailure("invalid_json", f"Failed to parse Gemini response as JSON: {exc}", status=status, model=model)

            candidates = data.get("candidates", [])
            if not candidates:
                raise ProviderFailure("empty_response", "Gemini returned no candidates", status=status, model=model)

            first_candidate = candidates[0]
            finish_reason = first_candidate.get("finishReason", "UNKNOWN")
            content = first_candidate.get("content", {})
            parts = content.get("parts", [])

            # Aggregate all text parts in the candidate
            text = "".join(part.get("text", "") for part in parts if isinstance(part, dict) and "text" in part)

            if not text.strip():
                raise ProviderFailure("empty_text", "Gemini candidate contained no text", status=status, model=model)

            return {
                "text": text,
                "model": model,
                "elapsed_ms": elapsed_ms,
                "finish_reason": finish_reason,
                "candidates_count": len(candidates),
                "raw": data,
            }

        raise ProviderFailure("max_retries_exceeded", f"Exceeded {max_attempts} attempts on model {model}", model=model)

    def _backoff(self, attempt: int) -> None:
        """Apply exponential backoff capped at 2.0 seconds."""
        base = settings.gemini_retry_backoff_seconds or 0.5
        delay = min(2.0, base * (2 ** attempt))
        if delay > 0:
            self.sleep(delay)


_provider_instance: Optional[GeminiProvider] = None
_provider_lock = threading.Lock()


def get_gemini_provider(api_key: Optional[str] = None) -> GeminiProvider:
    """Singleton getter for GeminiProvider."""
    global _provider_instance
    if _provider_instance is None or (api_key and _provider_instance.api_key != api_key):
        with _provider_lock:
            if _provider_instance is None or (api_key and _provider_instance.api_key != api_key):
                _provider_instance = GeminiProvider(api_key=api_key)
    return _provider_instance
