"""
backend/tests/unit/test_config.py
---------------------------------
Unit tests for configuration validation and strict production safeguards.
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_default_local_settings():
    """Verify default settings for local development are safe and valid."""
    settings = Settings()
    assert settings.APP_ENV == "local"
    assert settings.DATA_MODE == "fixture"
    assert settings.AZURE_AUTH_MODE == "default_credential"
    assert settings.LOG_AI_PROMPTS is False
    assert "*" not in settings.cors_origins_list


def test_production_rejects_wildcard_cors():
    """Production mode must reject '*' in CORS origins."""
    with pytest.raises(
        ValidationError, match="Wildcard '\\*' in CORS_ALLOW_ORIGINS is forbidden in production"
    ):
        Settings(
            APP_ENV="production",
            INTERNAL_API_KEY="super-secret-key-that-is-long-enough",
            DATA_MODE="local_snapshot",
            CORS_ALLOW_ORIGINS="https://example.com, *",
        )


def test_production_requires_internal_api_key():
    """Production mode must require an INTERNAL_API_KEY with at least 16 characters."""
    with pytest.raises(ValidationError, match="INTERNAL_API_KEY must be set to a secure string"):
        Settings(
            APP_ENV="production",
            INTERNAL_API_KEY="",
            DATA_MODE="local_snapshot",
            CORS_ALLOW_ORIGINS="https://frontend.vercel.app",
        )

    with pytest.raises(ValidationError, match="INTERNAL_API_KEY must be set to a secure string"):
        Settings(
            APP_ENV="production",
            INTERNAL_API_KEY="short-key",
            DATA_MODE="local_snapshot",
            CORS_ALLOW_ORIGINS="https://frontend.vercel.app",
        )


def test_production_forbids_connection_string():
    """Production mode must forbid connection_string auth mode."""
    with pytest.raises(
        ValidationError, match="AZURE_AUTH_MODE='connection_string' is forbidden in production"
    ):
        Settings(
            APP_ENV="production",
            INTERNAL_API_KEY="super-secret-key-that-is-long-enough",
            DATA_MODE="azure",
            AZURE_AUTH_MODE="connection_string",
            CORS_ALLOW_ORIGINS="https://frontend.vercel.app",
        )


def test_production_forbids_prompt_logging():
    """Production mode must forbid LOG_AI_PROMPTS=True."""
    with pytest.raises(ValidationError, match="LOG_AI_PROMPTS must not be True in production"):
        Settings(
            APP_ENV="production",
            INTERNAL_API_KEY="super-secret-key-that-is-long-enough",
            DATA_MODE="local_snapshot",
            LOG_AI_PROMPTS=True,
            CORS_ALLOW_ORIGINS="https://frontend.vercel.app",
        )


def test_production_forbids_fixture_mode():
    """Production mode must forbid DATA_MODE='fixture'."""
    with pytest.raises(ValidationError, match="DATA_MODE='fixture' is forbidden in production"):
        Settings(
            APP_ENV="production",
            INTERNAL_API_KEY="super-secret-key-that-is-long-enough",
            DATA_MODE="fixture",
            CORS_ALLOW_ORIGINS="https://frontend.vercel.app",
        )


def test_valid_production_settings_pass():
    """A valid production configuration with all safeguards in place should validate cleanly."""
    settings = Settings(
        APP_ENV="production",
        INTERNAL_API_KEY="super-secure-internal-api-key-123456",
        DATA_MODE="azure",
        AZURE_AUTH_MODE="default_credential",
        LOG_AI_PROMPTS=False,
        CORS_ALLOW_ORIGINS="https://frontend.vercel.app, https://custom-domain.com",
    )
    assert settings.APP_ENV == "production"
    assert settings.INTERNAL_API_KEY == "super-secure-internal-api-key-123456"
    assert len(settings.cors_origins_list) == 2
