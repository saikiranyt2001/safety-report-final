# Rate Limiting Middleware

# Add FastAPI middleware for rate limiting, e.g., limiting requests per user/IP.
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)