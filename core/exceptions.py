"""Custom exceptions"""

class DetectionSystemError(Exception):
    """Base exception"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        self.http_status_code = 500
        super().__init__(message)

class AuthenticationError(DetectionSystemError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)
        self.http_status_code = 401

class ImageValidationError(DetectionSystemError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)
        self.http_status_code = 400

class DetectionError(DetectionSystemError):
    pass
