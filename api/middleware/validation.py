"""
Request validation middleware

Provides:
- File upload validation
- Content-type validation
- File size limits
- File type checking
- Magic bytes validation (security)
"""
from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
import magic  # python-magic for MIME type detection


def validate_image_magic_bytes(content: bytes) -> bool:
    """
    Validate image file using magic bytes (file signature)
    
    Security: Prevents malicious files disguised as images
    (e.g., PHP script with .jpg extension)
    
    Args:
        content: File content bytes
    
    Returns:
        bool: True if valid image format
    
    Magic Bytes (File Signatures):
        - JPEG: FF D8 FF
        - PNG:  89 50 4E 47 0D 0A 1A 0A
        - GIF:  GIF87a or GIF89a
        - BMP:  42 4D
        - TIFF: 49 49 2A 00 or 4D 4D 00 2A
    
    Example:
        >>> with open("image.jpg", "rb") as f:
        ...     content = f.read()
        >>> validate_image_magic_bytes(content)
        True
    """
    if not content or len(content) < 8:
        return False
    
    # Check magic bytes for each supported format
    magic_bytes = {
        # JPEG
        b"\xFF\xD8\xFF": "jpeg",
        
        # PNG
        b"\x89PNG\r\n\x1a\n": "png",
        
        # GIF87a
        b"GIF87a": "gif",
        
        # GIF89a
        b"GIF89a": "gif",
        
        # BMP
        b"BM": "bmp",
        
        # TIFF (little-endian)
        b"II\x2a\x00": "tiff",
        
        # TIFF (big-endian)
        b"MM\x00\x2a": "tiff",
    }
    
    # Check if content starts with any known magic bytes
    for magic, format_name in magic_bytes.items():
        if content.startswith(magic):
            return True
    
    return False


def validate_mime_vs_magic_bytes(content: bytes, mime_type: str) -> bool:
    """
    Cross-validate MIME type against magic bytes.
    
    Security: Prevents file spoofing where declared MIME type
    doesn't match actual file content.
    
    Args:
        content: File content bytes
        mime_type: Declared MIME type (from python-magic)
    
    Returns:
        bool: True if MIME matches magic bytes
    
    Example:
        >>> # Valid: JPEG content with image/jpeg MIME
        >>> validate_mime_vs_magic_bytes(jpeg_content, "image/jpeg")
        True
        
        >>> # Invalid: PNG content claiming to be JPEG
        >>> validate_mime_vs_magic_bytes(png_content, "image/jpeg")
        False
    
    Security Note:
        This prevents attacks where malicious files are disguised
        with fake MIME types or wrong extensions.
    """
    if not content or len(content) < 8:
        return False
    
    # Mapping: MIME type -> Expected magic bytes
    mime_to_magic = {
        "image/jpeg": [b"\xFF\xD8\xFF"],
        "image/png": [b"\x89PNG\r\n\x1a\n"],
        "image/gif": [b"GIF87a", b"GIF89a"],
        "image/bmp": [b"BM"],
        "image/tiff": [b"II\x2a\x00", b"MM\x00\x2a"],
    }
    
    # Get expected magic bytes for this MIME type
    expected_magics = mime_to_magic.get(mime_type)
    
    if not expected_magics:
        # Unknown MIME type
        return False
    
    # Check if content starts with any expected magic bytes
    for magic in expected_magics:
        if content.startswith(magic):
            return True
    
    # MIME type doesn't match actual file content
    return False


class FileValidator:
    """
    File upload validator
    
    Validates uploaded files for:
    - Size limits
    - MIME types
    - File extensions
    """
    
    def __init__(
        self,
        max_size_mb: int = 10,
        allowed_extensions: Optional[List[str]] = None,
        allowed_mime_types: Optional[List[str]] = None
    ):
        """
        Initialize file validator
        
        Args:
            max_size_mb: Maximum file size in MB
            allowed_extensions: Allowed file extensions (e.g. ['.jpg', '.png'])
            allowed_mime_types: Allowed MIME types (e.g. ['image/jpeg'])
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.allowed_extensions = allowed_extensions or [
            '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff'
        ]
        self.allowed_mime_types = allowed_mime_types or [
            'image/jpeg', 'image/png', 'image/bmp', 'image/gif', 'image/tiff'
        ]
    
    async def validate_image(self, file: UploadFile) -> bool:
        """
        Validate uploaded image file
        
        Args:
            file: Uploaded file
        
        Returns:
            bool: True if valid
        
        Raises:
            HTTPException: If validation fails
        """
        # Check filename
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required"
            )
        
        # Check file extension
        extension = self._get_extension(file.filename)
        if extension.lower() not in self.allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file extension. Allowed: {', '.join(self.allowed_extensions)}"
            )
        
        # Read file content for validation
        content = await file.read()
        
        # Check file size
        size = len(content)
        if size > self.max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {self.max_size_bytes / 1024 / 1024:.1f}MB"
            )
        
        # Check if empty
        if size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        # SECURITY: STRICT MIME type validation (REQUIRED)
        # Both MIME and magic bytes MUST be validated
        try:
            mime_type = magic.from_buffer(content, mime=True)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"MIME type detection failed: {str(e)}. Install python-magic: pip install python-magic"
            )
        
        if mime_type not in self.allowed_mime_types:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=(
                    f"Unsupported file type: {mime_type}. "
                    f"Allowed: {', '.join(self.allowed_mime_types)}"
                )
            )
        
        # SECURITY: Validate magic bytes (file signature)
        # Prevents malicious files disguised as images
        if not validate_image_magic_bytes(content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image file signature. File may be corrupted or not a valid image."
            )
        
        # SECURITY: Cross-check MIME vs Magic bytes
        # Ensure they match (prevent spoofing)
        if not validate_mime_vs_magic_bytes(content, mime_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File signature does not match declared MIME type. Possible file spoofing attempt."
            )
        
        # Reset file pointer for later reading
        await file.seek(0)
        
        return True
    
    def _get_extension(self, filename: str) -> str:
        """Get file extension"""
        import os
        _, ext = os.path.splitext(filename)
        return ext


# Default image validator
image_validator = FileValidator(
    max_size_mb=10,
    allowed_extensions=['.jpg', '.jpeg', '.png', '.bmp'],
    allowed_mime_types=['image/jpeg', 'image/png', 'image/bmp']
)


# Dependency for file validation
async def validate_image_file(file: UploadFile) -> UploadFile:
    """
    Validate image file
    
    Use as dependency:
    @app.post("/upload")
    async def upload(file: UploadFile = Depends(validate_image_file)):
        ...
    
    Args:
        file: Uploaded file
    
    Returns:
        UploadFile: Validated file
    
    Raises:
        HTTPException: If validation fails
    """
    await image_validator.validate_image(file)
    return file
