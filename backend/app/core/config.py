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
    gemini_api_key: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()