from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    app_name: str
    app_version: str
    debug: bool

    # Database
    database_url: str

    # Security
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    # AI
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"
    ollama_timeout_seconds: float = 300.0
    gemini_api_key1: str = ""
    gemini_api_key: str = ""
    gemini_api_keys: str = ""
    nvidia_api_key: str = ""
    nvidia_model: str = "z-ai/glm-5.3"
    openrouter_api_key: str = ""
    openrouter_model: str = "openrouter/auto"

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_mode(cls, value):
        if isinstance(value, str):
            normalized = value.strip().casefold()
            if normalized in {"release", "production", "prod"}:
                return False
            if normalized in {"debug", "development", "dev"}:
                return True
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
