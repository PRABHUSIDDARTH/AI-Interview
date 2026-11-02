from typing import Union, List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Interview Simulator"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "local_development_only_secret_key_1234567890"
    JWT_SECRET: str | None = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DATABASE_URL: str = "sqlite:///./sql_app.db"
    ENVIRONMENT: str = "development"
    AI_PROVIDER: str = "mock"
    AI_API_KEY: str | None = None
    AI_MODEL: str | None = None

    # Email / SMTP settings (optional — if not set, reset URL is logged to console)
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str = "noreply@aiinterview.app"
    SMTP_USE_TLS: bool = True

    # Password reset
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    FRONTEND_URL: str = "http://localhost:3000"

    # Configurable CORS allowed origins (defaults to common local dev origins)
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    def model_post_init(self, __context):
        if self.JWT_SECRET and self.SECRET_KEY == "local_development_only_secret_key_1234567890":
            self.SECRET_KEY = self.JWT_SECRET

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()


