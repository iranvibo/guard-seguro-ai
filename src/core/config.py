"""Application configuration module for GuardSeguro AI.

Provides structured, typed settings loaded from environment variables and `.env` files.
"""

import os
from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    import streamlit as st

    if hasattr(st, "secrets"):
        for _k, _v in st.secrets.items():
            if isinstance(_v, str) and _k not in os.environ:
                os.environ[_k] = _v
except Exception:
    pass


class Settings(BaseSettings):
    """Configuration settings for GuardSeguro AI."""

    # LLM Settings
    openai_api_key: str = Field(
        default="",
        description="API Key for OpenAI API.",
        validation_alias="OPENAI_API_KEY",
    )
    openai_model_name: str = Field(
        default="gpt-4o-mini",
        description="LLM model identifier.",
        validation_alias="OPENAI_MODEL_NAME",
    )
    openai_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for LLM deterministic responses.",
        validation_alias="OPENAI_TEMPERATURE",
    )

    # App Settings
    app_name: str = Field(
        default="GuardSeguro AI",
        description="Human-readable application name.",
        validation_alias="APP_NAME",
    )
    app_env: Literal["development", "staging", "production", "test"] = Field(
        default="development",
        description="Application runtime environment.",
        validation_alias="APP_ENV",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level.",
        validation_alias="LOG_LEVEL",
    )

    # Server Settings
    streamlit_server_port: int = Field(
        default=8501,
        description="Port for Streamlit server.",
        validation_alias="STREAMLIT_SERVER_PORT",
    )
    streamlit_server_address: str = Field(
        default="0.0.0.0",
        description="Host address for Streamlit server.",
        validation_alias="STREAMLIT_SERVER_ADDRESS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_api_key_configured(self) -> bool:
        """Check if a valid, non-placeholder OpenAI API key is set."""
        return bool(
            self.openai_api_key
            and not self.openai_api_key.startswith("sk-proj-tu-clave")
        )


@lru_cache()
def get_settings() -> Settings:
    """Get a cached instance of application settings."""
    return Settings()
