from typing import Annotated
from fastapi import Header, HTTPException, status
from src.config import settings

def verify_admin(x_admin_token: Annotated[str | None, Header()] = None):
    """
    Dependency to verify that the request contains the correct admin token.
    Raises a 401 Unauthorized error if the token is missing or invalid.
    """
    if not x_admin_token or x_admin_token != settings.admin_secret_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin token"
        )