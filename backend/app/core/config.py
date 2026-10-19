"""
backend/app/core/config.py
--------------------------
Central configuration using Pydantic Settings.
Enforces strict production safeguards per docs/FINANCE_COMPLAINTS_DEVELOPMENT_PLAN.md §12.4.
"""

from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Core Environment
    APP_ENV: Literal["local", "test", "production"] = "local"

    # Data Source & Storage
    DATA_MODE: Literal["fixture", "local_snapshot", "azure"] = "fixture"
    LOCAL_DATA_DIR: str = ".local_data"

    # Azure Storage Configuration
    AZURE_STORAGE_ACCOUNT_NAME: str = "financecomplaintssa"
    AZURE_AUTH_MODE: Literal["default_credential", "connection_string"] = "default_credential"
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_SILVER_CONTAINER: str = "silver"
    AZURE_GOLD_CONTAINER: str = "gold"

    SILVER_COMPLAINTS_BLOB: str = "ConsumerComplaints_Silver.csv"
    SILVER_PRODUCTS_BLOB: str = "ProductCategoryReference_Silver.csv"
    GOLD_CATEGORY_BLOB: str = "complaints_by_category_gold.csv"
    GOLD_TREND_BLOB: str = "complaints_trend_gold.csv"
    GOLD_ANOMALY_BLOB: str = "complaints_anomaly_gold.csv"
    GOLD_DQ_REPORT_BLOB: str = "data_quality_report_gold.csv"
    GOLD_DQ_RUN_BLOB: str = "data_quality_run_gold.csv"

    DATA_REFRESH_CHECK_SECONDS: int = 300
    DATA_MAX_SKEW_HOURS: int = 24
    MAX_BLOB_BYTES: int = 104_857_600  # 100 MB

    # Security & Rate Limits
    INTERNAL_API_KEY: str = ""
    CORS_ALLOW_ORIGINS: str = "http://localhost:3000"
    MAX_REQUEST_BYTES: int = 65_536  # 64 KB
    RATE_LIMIT_DEFAULT: str = "120/minute"
    RATE_LIMIT_EXPORT: str = "10/hour"
    RATE_LIMIT_AI: str = "10/minute"
    EXPORT_MAX_ROWS: int = 10_000

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["console", "json"] = "console"
    LOG_AI_PROMPTS: bool = False

    # AI Assistant & LLM
    LLM_PROVIDER: Literal["azure_openai", "fake", "disabled"] = "disabled"
    LLM_ENDPOINT: str = ""
    LLM_DEPLOYMENT: str = ""
    LLM_API_VERSION: str = "2024-02-15-preview"
    LLM_AUTH_MODE: Literal["api_key", "entra"] = "api_key"
    LLM_API_KEY: str = ""
    LLM_TIMEOUT_SECONDS: int = 20
    LLM_MAX_OUTPUT_TOKENS: int = 700

    AI_MAX_TOOL_CALLS: int = 3
    AI_HISTORY_MAX_MESSAGES: int = 6
    AI_MAX_QUESTION_CHARS: int = 500
    AI_DAILY_REQUEST_CAP: int = 300

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_production_safeguards(self) -> "Settings":
        """Strict production-mode validators per §12.4."""
        if self.APP_ENV == "production":
            # 1. Reject wildcard CORS
            if "*" in self.cors_origins_list:
                raise ValueError("Wildcard '*' in CORS_ALLOW_ORIGINS is forbidden in production")

            # 2. Require internal API key
            if not self.INTERNAL_API_KEY or len(self.INTERNAL_API_KEY.strip()) < 16:
                raise ValueError(
                    "INTERNAL_API_KEY must be set to a secure string (>= 16 chars) in production"
                )

            # 3. Forbid connection_string auth in production
            if self.AZURE_AUTH_MODE == "connection_string":
                raise ValueError(
                    "AZURE_AUTH_MODE='connection_string' is forbidden in production; use 'default_credential'"
                )

            # 4. Forbid prompt logging in production
            if self.LOG_AI_PROMPTS:
                raise ValueError("LOG_AI_PROMPTS must not be True in production")

            # 5. Forbid fixture mode in production
            if self.DATA_MODE == "fixture":
                raise ValueError(
                    "DATA_MODE='fixture' is forbidden in production; use 'azure' or 'local_snapshot'"
                )

        return self


def get_settings() -> Settings:
    """Dependency helper to retrieve cached or fresh settings."""
    return Settings()
