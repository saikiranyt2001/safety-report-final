from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared rate limiter instance used by API routes and app setup.
limiter = Limiter(key_func=get_remote_address)
