"""Unit tests for core configuration and environment loading."""

import os
from unittest.mock import patch
from src.core.config import Settings, get_settings


def test_default_settings():
    """Verify default settings values when no environment is set."""
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        assert settings.app_name == "GuardSeguro AI"
        assert settings.app_env == "development"
        assert settings.openai_model_name == "gpt-4o-mini"
        assert settings.openai_temperature == 0.0
        assert settings.streamlit_server_port == 8501
        assert not settings.is_api_key_configured


def test_custom_environment_settings():
    """Verify custom environment variable overriding."""
    custom_env = {
        "OPENAI_API_KEY": "sk-proj-valid-test-key-123456",
        "OPENAI_MODEL_NAME": "gpt-4o",
        "APP_ENV": "production",
        "STREAMLIT_SERVER_PORT": "9000",
    }
    with patch.dict(os.environ, custom_env, clear=True):
        settings = Settings()
        assert settings.openai_api_key == "sk-proj-valid-test-key-123456"
        assert settings.openai_model_name == "gpt-4o"
        assert settings.app_env == "production"
        assert settings.streamlit_server_port == 9000
        assert settings.is_api_key_configured


def test_placeholder_api_key_not_configured():
    """Verify placeholder key from .env.example is recognized as unconfigured."""
    placeholder_env = {
        "OPENAI_API_KEY": "sk-proj-tu-clave-aqui",
    }
    with patch.dict(os.environ, placeholder_env, clear=True):
        settings = Settings()
        assert not settings.is_api_key_configured


def test_get_settings_caching():
    """Verify get_settings returns a valid Settings instance."""
    settings = get_settings()
    assert isinstance(settings, Settings)
