"""
Upload Size Validator Middleware

Validates upload file sizes BEFORE processing to prevent:
- Denial of Service (DoS) attacks with huge files
- Memory exhaustion
- Disk space exhaustion

Security Features:
- Content-Length header validation
- Configurable size limit (default 10MB)
- Early rejection (before file processing)
- Proper HTTP 413 (Payload Too Large) response
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from core.logging import get_logger

logger = get_logger("upload")


class UploadSizeValidator(BaseHTTPMiddleware):
    """
    Middleware to validate upload file size before processing.
    
    Checks Content-Length header and rejects requests exceeding limit.
    This prevents DoS attacks and resource exhaustion.
    
    Usage:
        app.add_middleware(UploadSizeValidator)
    
    Configuration:
        Set MAX_UPLOAD_SIZE_MB in config (default: 10MB)
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Validate upload size before processing request.
        
        Args:
            request: FastAPI Request
            call_next: Next middleware/handler
            
        Returns:
            Response: From next handler if validation passes
            
        Raises:
            HTTPException: 413 if file too large
        """
        # Only check upload endpoints
        if request.method in ["POST", "PUT", "PATCH"]:
            # Check Content-Length header
            content_length = request.headers.get("content-length")
            
            if content_length:
                try:
                    content_length = int(content_length)
                except ValueError:
                    logger.warning("Invalid Content-Length header", value=content_length)
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid Content-Length header"
                    )
                
                # Get config
                config = request.app.state.config
                max_size_bytes = config.max_upload_size_bytes
                
                # Validate size
                if content_length > max_size_bytes:
                    size_mb = content_length / (1024 * 1024)
                    max_mb = config.max_upload_size_mb
                    
                    logger.warning(
                        "Upload too large",
                        size_mb=round(size_mb, 2),
                        max_mb=max_mb,
                        path=request.url.path
                    )
                    
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            f"File too large ({size_mb:.1f} MB). "
                            f"Maximum allowed: {max_mb} MB"
                        )
                    )
        
        # Process request
        response = await call_next(request)
        return response
