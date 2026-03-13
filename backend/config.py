import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """
    Application configuration settings
    """

    # OpenAI API
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./safety.db"
    )

    # Redis
    REDIS_URL: str = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0"
    )

    # Security
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "change-this-secret-key"
    )

    JWT_ALGORITHM: str = os.getenv(
        "JWT_ALGORITHM",
        "HS256"
    )

    # Integrations
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    DEFAULT_SLACK_WEBHOOK_URL: str = os.getenv("DEFAULT_SLACK_WEBHOOK_URL", "")
    DEFAULT_TEAMS_WEBHOOK_URL: str = os.getenv("DEFAULT_TEAMS_WEBHOOK_URL", "")

    INTEGRATION_HTTP_TIMEOUT: int = int(os.getenv("INTEGRATION_HTTP_TIMEOUT", "10"))


# Create settings instance
settings = Settings()