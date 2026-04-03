from functools import lru_cache
from typing import Annotated, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    APP_NAME: str = "Orbit API"
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql+psycopg://postgres:123456@localhost:5432/orbit_db"
    JWT_SECRET_KEY: str = "change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    BACKEND_CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return []

        if isinstance(value, str):
            cleaned_value = value.strip()
            if cleaned_value.startswith("[") and cleaned_value.endswith("]"):
                cleaned_value = cleaned_value[1:-1]

            return [
                item.strip().strip("\"'")
                for item in cleaned_value.split(",")
                if item.strip()
            ]

        if isinstance(value, list):
            return value

        raise ValueError("BACKEND_CORS_ORIGINS must be a comma-separated string or a list.")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
