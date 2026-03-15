from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):

    # ------------------------------------------------
    # APP
    # ------------------------------------------------
    APP_NAME: str = "AI Safety Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True


    # ------------------------------------------------
    # SECURITY
    # ------------------------------------------------
    SECRET_KEY: str = "supersecretkey"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60


    # ------------------------------------------------
    # DATABASE
    # ------------------------------------------------
    DATABASE_URL: str = "sqlite:///./safety.db"


    # ------------------------------------------------
    # REDIS (ADD THIS)
    # ------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"


    # ------------------------------------------------
    # CORS
    # ------------------------------------------------
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:8000",
    ]


    # ------------------------------------------------
    # AI / MODEL SETTINGS
    # ------------------------------------------------
    OPENAI_API_KEY: str | None = None
    DEFAULT_AI_MODEL: str = "gpt-4o-mini"


    # ------------------------------------------------
    # FILE STORAGE
    # ------------------------------------------------
    STORAGE_PATH: str = "storage"
    MAX_UPLOAD_SIZE_MB: int = 10


    # ------------------------------------------------
    # LOGGING
    # ------------------------------------------------
    LOG_LEVEL: str = "INFO"


    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()