"""
JWT token management with security hardening

Provides thread-safe JWT token creation and verification.
Uses HS256 algorithm with proper error handling.
"""
import jwt
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class JWTManager:
    """
    Manages JWT token creation and verification
    
    Features:
    - Thread-safe token operations
    - Automatic expiration handling
    - Comprehensive error handling
    - Configurable algorithm and expiration
    """
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 60
    ):
        """
        Initialize JWT manager
        
        Args:
            secret_key: Secret key for signing tokens (min 32 chars)
            algorithm: JWT signing algorithm (default: HS256)
            access_token_expire_minutes: Token lifetime in minutes
        
        Raises:
            ValueError: If secret_key is too short
        """
        if len(secret_key) < 32:
            raise ValueError("Secret key must be at least 32 characters")
        
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
    
    def create_access_token(
        self,
        user_data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a new JWT access token
        
        Args:
            user_data: User information to encode in token
            expires_delta: Custom expiration time (optional)
        
        Returns:
            str: Encoded JWT token
        
        Example:
            >>> manager = JWTManager("secret_key")
            >>> token = manager.create_access_token({
            ...     "user_id": "123",
            ...     "username": "john",
            ...     "roles": ["user"]
            ... })
        """
        # Calculate expiration time
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.access_token_expire_minutes
            )
        
        # Build payload
        payload = {
            **user_data,
            'exp': expire,
            'iat': datetime.utcnow(),
            'type': 'access'
        }
        
        # Encode token
        encoded_jwt = jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm
        )
        
        return encoded_jwt
    
    def create_refresh_token(
        self,
        user_data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a new JWT refresh token
        
        Refresh tokens have longer lifetime (7 days default) and can be used
        to obtain new access tokens without re-authentication.
        
        Args:
            user_data: User information to encode
            expires_delta: Custom expiration (default: 7 days)
        
        Returns:
            str: Encoded refresh token
        
        Example:
            >>> manager = JWTManager("secret_key")
            >>> refresh = manager.create_refresh_token({"user_id": "123"})
        """
        # Calculate expiration (7 days default)
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=7)
        
        # Build payload (minimal data for refresh tokens)
        payload = {
            'user_id': user_data.get('user_id'),
            'username': user_data.get('username'),
            'exp': expire,
            'iat': datetime.utcnow(),
            'type': 'refresh'
        }
        
        # Encode token
        encoded_jwt = jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm
        )
        
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token
        
        Args:
            token: JWT token to verify
        
        Returns:
            dict: Decoded token payload
        
        Raises:
            ValueError: If token is invalid, expired, or malformed
        
        Example:
            >>> manager = JWTManager("secret_key")
            >>> payload = manager.verify_token(token)
            >>> user_id = payload['user_id']
        """
        try:
            # Decode and verify token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Verify token type
            if payload.get('type') != 'access':
                raise ValueError("Invalid token type")
            
            return payload
        
        except jwt.ExpiredSignatureError:
            raise ValueError(
                "Token has expired. Please login again."
            )
        
        except jwt.InvalidTokenError as e:
            raise ValueError(
                f"Invalid token: {str(e)}"
            )
        
        except Exception as e:
            raise ValueError(
                f"Token verification failed: {str(e)}"
            )
    
    def decode_token_unsafe(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode token without verification (for debugging only)
        
        ⚠️  WARNING: Do not use for authentication!
        This method does not verify the signature.
        
        Args:
            token: JWT token to decode
        
        Returns:
            dict: Decoded payload or None if invalid
        """
        try:
            return jwt.decode(
                token,
                options={"verify_signature": False}
            )
        except Exception:
            return None


# Thread-safe singleton
_jwt_manager: Optional[JWTManager] = None
_jwt_lock = threading.Lock()


def get_jwt_manager() -> JWTManager:
    """
    Get the JWT manager singleton instance (thread-safe)
    
    Returns:
        JWTManager: Singleton instance
    
    The instance is created once and reused for all subsequent calls.
    Thread-safe using double-checked locking pattern.
    """
    global _jwt_manager
    
    # Fast path - no lock needed
    if _jwt_manager is not None:
        return _jwt_manager
    
    # Slow path - acquire lock and create instance
    with _jwt_lock:
        # Double-check inside lock
        if _jwt_manager is None:
            from core.config import get_config
            config = get_config()
            
            _jwt_manager = JWTManager(
                secret_key=config.jwt_secret_key,
                algorithm=config.jwt_algorithm,
                access_token_expire_minutes=config.access_token_expire_minutes
            )
    
    return _jwt_manager
