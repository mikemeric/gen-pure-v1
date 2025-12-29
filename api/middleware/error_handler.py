"""
Error handling middleware for API

Provides:
- Global exception handling
- Standard error responses
- Error logging
- Status code mapping
"""
import traceback
from typing import Callable
from fastapi import Request, status
from fastapi.responses import JSONResponse
from datetime import datetime

from core.exceptions import (
    AuthenticationError,
    ValidationError as CustomValidationError,
    NotFoundError,
    RateLimitError
)


class ErrorHandlerMiddleware:
    """
    Global error handler middleware
    
    Catches all exceptions and returns standardized JSON responses.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Could add custom headers here
                pass
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            # Handle exception
            response = handle_exception(exc)
            await response(scope, receive, send)


def handle_exception(exc: Exception) -> JSONResponse:
    """
    Handle exception and return JSON response
    
    Args:
        exc: Exception to handle
    
    Returns:
        JSONResponse: Standardized error response
    """
    # Authentication errors
    if isinstance(exc, AuthenticationError):
        return create_error_response(
            error="AuthenticationError",
            message=str(exc),
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # Validation errors
    elif isinstance(exc, CustomValidationError):
        return create_error_response(
            error="ValidationError",
            message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
            details=getattr(exc, 'details', None)
        )
    
    # Not found errors
    elif isinstance(exc, NotFoundError):
        return create_error_response(
            error="NotFoundError",
            message=str(exc),
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # Rate limit errors
    elif isinstance(exc, RateLimitError):
        return create_error_response(
            error="RateLimitError",
            message=str(exc),
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    # Pydantic validation errors
    elif hasattr(exc, '__class__') and exc.__class__.__name__ == 'ValidationError':
        return create_error_response(
            error="ValidationError",
            message="Request validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"errors": str(exc)}
        )
    
    # Value errors
    elif isinstance(exc, ValueError):
        return create_error_response(
            error="ValueError",
            message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Generic errors
    else:
        # Log full traceback for debugging
        print(f"❌ Unhandled exception: {exc}")
        traceback.print_exc()
        
        return create_error_response(
            error="InternalServerError",
            message="An internal error occurred",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"exception": str(exc)} if is_debug_mode() else None
        )


def create_error_response(
    error: str,
    message: str,
    status_code: int,
    details: dict = None
) -> JSONResponse:
    """
    Create standardized error response
    
    Args:
        error: Error type
        message: Error message
        status_code: HTTP status code
        details: Optional error details
    
    Returns:
        JSONResponse: Error response
    """
    content = {
        "success": False,
        "error": error,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    
    if details:
        content["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content=content
    )


def is_debug_mode() -> bool:
    """Check if debug mode is enabled"""
    import os
    return os.getenv("ENVIRONMENT", "production") in ["development", "testing"]


# Exception handler functions for FastAPI
async def authentication_exception_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors"""
    return create_error_response(
        error="AuthenticationError",
        message=str(exc),
        status_code=status.HTTP_401_UNAUTHORIZED
    )


async def validation_exception_handler(request: Request, exc: CustomValidationError):
    """Handle validation errors"""
    return create_error_response(
        error="ValidationError",
        message=str(exc),
        status_code=status.HTTP_400_BAD_REQUEST,
        details=getattr(exc, 'details', None)
    )


async def not_found_exception_handler(request: Request, exc: NotFoundError):
    """Handle not found errors"""
    return create_error_response(
        error="NotFoundError",
        message=str(exc),
        status_code=status.HTTP_404_NOT_FOUND
    )


async def rate_limit_exception_handler(request: Request, exc: RateLimitError):
    """Handle rate limit errors"""
    return create_error_response(
        error="RateLimitError",
        message=str(exc),
        status_code=status.HTTP_429_TOO_MANY_REQUESTS
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle generic exceptions"""
    print(f"❌ Unhandled exception: {exc}")
    traceback.print_exc()
    
    return create_error_response(
        error="InternalServerError",
        message="An internal error occurred",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details={"exception": str(exc)} if is_debug_mode() else None
    )
