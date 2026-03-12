# Logging Middleware

# Add FastAPI middleware for logging requests, responses, errors, etc.
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
import time
import logging

logger = logging.getLogger("api_logger")


class LoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        start_time = time.time()

        response = await call_next(request)

        process_time = round(time.time() - start_time, 4)

        logger.info(
            f"{request.method} {request.url.path} "
            f"Status:{response.status_code} "
            f"Time:{process_time}s"
        )

        return response