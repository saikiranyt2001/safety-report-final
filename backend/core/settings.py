# Application settings and configuration

# Add settings management (e.g., environment variables, config loading)
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    APP_NAME: str = "AI Safety Platform"

    SECRET_KEY: str = "supersecretkey"

    DATABASE_URL: str = "sqlite:///./safety.db"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60


settings = Settings()