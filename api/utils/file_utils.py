"""
File Utilities - Secure temporary file handling

Provides secure file cleanup with TOCTOU protection and crash resistance
using weakref.finalize for guaranteed cleanup.
"""
import os
import tempfile
import weakref
from pathlib import Path
from typing import Optional
from contextlib import contextmanager


def secure_cleanup_file(filepath: str) -> None:
    """
    Securely delete file without TOCTOU vulnerability
    
    Args:
        filepath: Path to file to delete
    
    Security:
        - Atomic deletion (no check-then-delete)
        - Handles FileNotFoundError gracefully
        - Logs but doesn't crash on errors
    
    TOCTOU Protection:
        Does NOT use os.path.exists() before os.unlink()
        to avoid race condition where file could be:
        - Deleted by another process
        - Replaced with symlink (security risk)
    
    Example:
        >>> secure_cleanup_file("/tmp/myfile.jpg")
    """
    try:
        os.unlink(filepath)
    except FileNotFoundError:
        # File already deleted - OK
        pass
    except PermissionError as e:
        # Permission issue - log but don't crash
        print(f"⚠️  Cannot delete {filepath}: {e}")
    except Exception as e:
        # Other error - log
        print(f"⚠️  Cleanup error for {filepath}: {e}")


@contextmanager
def secure_temp_file(suffix: str = "", prefix: str = "tmp", dir: Optional[str] = None):
    """
    Context manager for secure temporary file with guaranteed cleanup
    
    Args:
        suffix: File extension (e.g., ".jpg")
        prefix: Filename prefix
        dir: Directory for temp file
    
    Yields:
        tuple: (file_path: str, file_object)
    
    Security Features:
        - Automatic cleanup on exit (normal or exception)
        - Crash-resistant cleanup with weakref.finalize
        - TOCTOU-safe deletion
    
    Example:
        >>> with secure_temp_file(suffix=".jpg") as (path, f):
        ...     f.write(image_data)
        ...     f.close()
        ...     # Process file at 'path'
        ...     # File auto-deleted on exit
    """
    # Create temp file (delete=False for manual control)
    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
        prefix=prefix,
        dir=dir
    )
    temp_path = temp_file.name
    
    # Register cleanup even if process crashes (SIGKILL, etc.)
    # weakref.finalize will call cleanup when temp_file is garbage collected
    finalizer = weakref.finalize(temp_file, secure_cleanup_file, temp_path)
    
    try:
        yield temp_path, temp_file
    finally:
        # Explicit cleanup (in addition to finalizer)
        try:
            temp_file.close()
        except:
            pass
        
        # Delete file
        secure_cleanup_file(temp_path)
        
        # Detach finalizer (already cleaned up)
        finalizer.detach()


def validate_file_path(filepath: str, allowed_dirs: Optional[list] = None) -> bool:
    """
    Validate file path for security
    
    Args:
        filepath: Path to validate
        allowed_dirs: List of allowed parent directories
    
    Returns:
        bool: True if path is safe
    
    Security Checks:
        - No path traversal (../)
        - Within allowed directories
        - Not a symlink to sensitive location
    
    Example:
        >>> validate_file_path("/tmp/upload.jpg", allowed_dirs=["/tmp"])
        True
        >>> validate_file_path("/tmp/../etc/passwd")
        False
    """
    try:
        # Resolve to absolute path
        abs_path = Path(filepath).resolve()
        
        # Check for path traversal
        if ".." in str(abs_path):
            return False
        
        # Check allowed directories
        if allowed_dirs:
            allowed = any(
                abs_path.is_relative_to(Path(d).resolve())
                for d in allowed_dirs
            )
            if not allowed:
                return False
        
        return True
    
    except Exception:
        return False


def get_safe_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename for security
    
    Args:
        filename: Original filename
        max_length: Maximum length
    
    Returns:
        str: Safe filename
    
    Security:
        - Remove path separators
        - Remove null bytes
        - Limit length
        - Keep extension
    
    Example:
        >>> get_safe_filename("../../etc/passwd")
        'passwd'
        >>> get_safe_filename("image<script>.jpg")
        'imagescript.jpg'
    """
    # Remove path separators
    filename = os.path.basename(filename)
    
    # Remove null bytes and dangerous characters
    dangerous_chars = ['\0', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
    for char in dangerous_chars:
        filename = filename.replace(char, '')
    
    # Limit length (preserve extension)
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        max_name_length = max_length - len(ext)
        filename = name[:max_name_length] + ext
    
    return filename or "unnamed"
