# Custom exception classes for FastAPI

# Add custom exception handling logic

from fastapi import HTTPException


def not_found(entity: str):

    raise HTTPException(
        status_code=404,
        detail=f"{entity} not found"
    )


def unauthorized():

    raise HTTPException(
        status_code=401,
        detail="Unauthorized access"
    )
