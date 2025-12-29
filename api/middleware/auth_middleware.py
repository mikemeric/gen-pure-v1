"""
Authentication middleware for API

Provides:
- JWT token validation
- API key validation
- Request authentication
- User context injection
"""
from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.auth.jwt_manager import JWTManager
from services.auth.key_manager import KeyManager
from core.exceptions import AuthenticationError


# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)


class AuthMiddleware:
    """
    Authentication middleware
    
    Validates JWT tokens or API keys from requests.
    """
    
    def __init__(self):
        self.jwt_manager = JWTManager()
        self.key_manager = KeyManager()
    
    async def authenticate_request(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
    ) -> dict:
        """
        Authenticate request
        
        Tries authentication in order:
        1. Bearer token (JWT)
        2. API key header
        3. API key query parameter
        
        Args:
            request: FastAPI request
            credentials: HTTP bearer credentials
        
        Returns:
            dict: User context
        
        Raises:
            AuthenticationError: If authentication fails
        """
        # Try Bearer token first
        if credentials:
            return await self._authenticate_jwt(credentials.credentials)
        
        # Try API key in header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return await self._authenticate_api_key(api_key)
        
        # Try API key in query params
        api_key = request.query_params.get("api_key")
        if api_key:
            return await self._authenticate_api_key(api_key)
        
        # No authentication provided
        raise AuthenticationError("No authentication provided")
    
    async def _authenticate_jwt(self, token: str) -> dict:
        """
        Authenticate with JWT token
        
        Args:
            token: JWT token
        
        Returns:
            dict: User context from token
        
        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            payload = self.jwt_manager.verify_access_token(token)
            
            return {
                "user_id": payload.get("user_id"),
                "username": payload.get("username"),
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", []),
                "auth_method": "jwt"
            }
        
        except Exception as e:
            raise AuthenticationError(f"Invalid JWT token: {e}")
    
    async def _authenticate_api_key(self, api_key: str) -> dict:
        """
        Authenticate with API key
        
        Args:
            api_key: API key
        
        Returns:
            dict: User context from API key
        
        Raises:
            AuthenticationError: If API key is invalid
        """
        try:
            # Verify API key
            key_data = self.key_manager.verify_key(api_key)
            
            if not key_data:
                raise AuthenticationError("Invalid API key")
            
            return {
                "user_id": key_data.get("user_id"),
                "username": key_data.get("username"),
                "roles": key_data.get("roles", []),
                "permissions": key_data.get("permissions", []),
                "auth_method": "api_key",
                "api_key_id": key_data.get("key_id")
            }
        
        except Exception as e:
            raise AuthenticationError(f"Invalid API key: {e}")


# Dependency for protected routes
async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> dict:
    """
    Get current authenticated user
    
    Use as dependency in route handlers:
    
    @app.get("/protected")
    async def protected_route(user: dict = Depends(get_current_user)):
        return {"user_id": user["user_id"]}
    
    Args:
        request: FastAPI request
        credentials: HTTP bearer credentials
    
    Returns:
        dict: User context
    
    Raises:
        HTTPException: If authentication fails
    """
    auth = AuthMiddleware()
    
    try:
        return await auth.authenticate_request(request, credentials)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


# Dependency for optional authentication
async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Optional[dict]:
    """
    Get current user (optional)
    
    Returns None if no authentication provided.
    
    Args:
        request: FastAPI request
        credentials: HTTP bearer credentials
    
    Returns:
        Optional[dict]: User context or None
    """
    auth = AuthMiddleware()
    
    try:
        return await auth.authenticate_request(request, credentials)
    except AuthenticationError:
        return None


# Permission checker
def require_permission(permission: str):
    """
    Require specific permission
    
    Usage:
    @app.get("/admin")
    async def admin_route(user: dict = Depends(require_permission("admin:write"))):
        return {"message": "Admin access granted"}
    
    Args:
        permission: Required permission
    
    Returns:
        Callable: Dependency function
    """
    async def permission_checker(user: dict = Depends(get_current_user)) -> dict:
        """Check if user has permission"""
        permissions = user.get("permissions", [])
        
        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires '{permission}'"
            )
        
        return user
    
    return permission_checker


# Role checker
def require_role(role: str):
    """
    Require specific role
    
    Usage:
    @app.get("/admin")
    async def admin_route(user: dict = Depends(require_role("admin"))):
        return {"message": "Admin access granted"}
    
    Args:
        role: Required role
    
    Returns:
        Callable: Dependency function
    """
    async def role_checker(user: dict = Depends(get_current_user)) -> dict:
        """Check if user has role"""
        roles = user.get("roles", [])
        
        if role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: requires '{role}' role"
            )
        
        return user
    
    return role_checker
