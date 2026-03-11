import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
	OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
	DATABASE_URL = os.getenv(
		"DATABASE_URL",
		"sqlite:///./safety.db"
	)
	REDIS_URL = os.getenv(
		"REDIS_URL",
		"redis://localhost:6379/0"
	)
	SECRET_KEY = os.getenv(
		"SECRET_KEY",
		"super-secret-key"
	)
	JWT_ALGORITHM = os.getenv(
		"JWT_ALGORITHM",
		"HS256"
	)

settings = Settings()