"""
Structured Logging - Proper logging with context

Replaces print() statements with structured logging for:
- Better debugging
- Log aggregation (Datadog, CloudWatch, etc.)
- Performance monitoring
- Error tracking
"""
import logging
import sys
from typing import Any, Dict, Optional
from datetime import datetime
import json


class StructuredLogger:
    """
    Structured logger with context support
    
    Features:
    - JSON output for log aggregation
    - Contextual information
    - Log levels (DEBUG, INFO, WARNING, ERROR)
    - Performance tracking
    
    Example:
        >>> logger = get_logger("detection")
        >>> logger.info("Detection started", method="ensemble", image_size="800x600")
        >>> # Output: {"timestamp": "...", "level": "INFO", "message": "Detection started", "method": "ensemble", ...}
    """
    
    def __init__(self, name: str, level: int = logging.INFO):
        """
        Initialize structured logger
        
        Args:
            name: Logger name (e.g., "detection", "auth")
            level: Log level (DEBUG, INFO, WARNING, ERROR)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Avoid duplicate handlers
        if not self.logger.handlers:
            # Console handler
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(level)
            
            # JSON formatter
            formatter = JSONFormatter()
            handler.setFormatter(formatter)
            
            self.logger.addHandler(handler)
    
    def _log(self, level: str, message: str, **context):
        """Internal log method with context"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            **context
        }
        
        if level == "DEBUG":
            self.logger.debug(json.dumps(log_data))
        elif level == "INFO":
            self.logger.info(json.dumps(log_data))
        elif level == "WARNING":
            self.logger.warning(json.dumps(log_data))
        elif level == "ERROR":
            self.logger.error(json.dumps(log_data))
    
    def debug(self, message: str, **context):
        """
        Log debug message
        
        Args:
            message: Log message
            **context: Additional context (key=value pairs)
        
        Example:
            >>> logger.debug("Cache lookup", key="detection:abc123", hit=True)
        """
        self._log("DEBUG", message, **context)
    
    def info(self, message: str, **context):
        """
        Log info message
        
        Args:
            message: Log message
            **context: Additional context
        
        Example:
            >>> logger.info("Detection completed", duration_ms=342.5, method="ensemble")
        """
        self._log("INFO", message, **context)
    
    def warning(self, message: str, **context):
        """
        Log warning message
        
        Args:
            message: Log message
            **context: Additional context
        
        Example:
            >>> logger.warning("Redis connection failed", error=str(e), fallback="LRU")
        """
        self._log("WARNING", message, **context)
    
    def error(self, message: str, error: Optional[Exception] = None, **context):
        """
        Log error message
        
        Args:
            message: Log message
            error: Exception object
            **context: Additional context
        
        Example:
            >>> logger.error("Detection failed", error=e, image_size="800x600")
        """
        if error:
            context["error_type"] = type(error).__name__
            context["error_message"] = str(error)
        
        self._log("ERROR", message, **context)


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging
    
    Outputs logs as JSON for easy parsing and aggregation.
    """
    
    def format(self, record):
        """Format log record as JSON"""
        # Already formatted as JSON in StructuredLogger
        return record.getMessage()


# Logger instances cache
_loggers: Dict[str, StructuredLogger] = {}


def get_logger(name: str, level: int = logging.INFO) -> StructuredLogger:
    """
    Get or create structured logger
    
    Args:
        name: Logger name (e.g., "detection", "auth", "cache")
        level: Log level
    
    Returns:
        StructuredLogger: Logger instance
    
    Example:
        >>> logger = get_logger("detection")
        >>> logger.info("Detection started")
    """
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name, level)
    
    return _loggers[name]


# Convenience loggers
detection_logger = get_logger("detection")
auth_logger = get_logger("auth")
cache_logger = get_logger("cache")
database_logger = get_logger("database")
api_logger = get_logger("api")
