"""
Configuration module for InterviewIQ backend.
Loads environment variables for API keys and service URLs.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Gemini Configuration
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    gemini_fallback_models: list = [
        model.strip()
        for model in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.5-flash-lite,gemini-3.6-flash").split(",")
        if model.strip()
    ]
    gemini_timeout_seconds: float = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "25"))
    gemini_retry_attempts: int = int(os.getenv("GEMINI_RETRY_ATTEMPTS", "1"))
    gemini_retry_backoff_seconds: float = float(os.getenv("GEMINI_RETRY_BACKOFF_SECONDS", "0.5"))
    gemini_model_discovery_timeout_seconds: float = float(
        os.getenv("GEMINI_MODEL_DISCOVERY_TIMEOUT_SECONDS", "5")
    )
    interview_duration_seconds: int = int(os.getenv("INTERVIEW_DURATION_SECONDS", "1800"))
    interview_fullscreen_required: bool = os.getenv("INTERVIEW_FULLSCREEN_REQUIRED", "false").lower() == "true"
    interview_prevent_copy: bool = os.getenv("INTERVIEW_PREVENT_COPY", "false").lower() == "true"
    interview_prevent_paste: bool = os.getenv("INTERVIEW_PREVENT_PASTE", "false").lower() == "true"
    interview_prevent_cut: bool = os.getenv("INTERVIEW_PREVENT_CUT", "false").lower() == "true"
    interview_prevent_context_menu: bool = os.getenv("INTERVIEW_PREVENT_CONTEXT_MENU", "false").lower() == "true"

    # n8n Configuration
    n8n_webhook_url: str = os.getenv("N8N_WEBHOOK_URL", "")
    app_base_url: str = os.getenv("APP_BASE_URL", "http://localhost:8000")
    public_api_base_url: str = os.getenv(
        "PUBLIC_API_BASE_URL",
        app_base_url
    )
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

    # Application
    app_name: str = "InterviewIQ"
    app_version: str = "0.1.0"

    # CORS
    cors_origin_regex: str = os.getenv(
        "CORS_ORIGIN_REGEX",
        r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    )
    cors_origins: list = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:5174,http://localhost:3000"
            ",http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:4173"
        ).split(",")
        if origin.strip()
    ]

    # Database (for future use)
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./interviewiq.db")


settings = Settings()
