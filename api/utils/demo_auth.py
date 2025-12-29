"""
Demo Authentication Loader - SECURE

Loads demo users from environment variable instead of hardcoded credentials.
This module MUST NOT contain any hardcoded passwords or hashes.

Security Features:
- No hardcoded credentials
- Environment variable only
- Blocked in production
- JSON validation
"""
import os
import json
from typing import Dict, Optional
from core.logging import get_logger

logger = get_logger("auth")


def load_demo_users() -> Dict[str, dict]:
    """
    Load demo users from environment variable.
    
    Format: 
    DEMO_USERS_JSON='{"demo":{"password_hash":"$2b$...","email":"demo@example.com"}}'
    
    Returns:
        Dict[str, dict]: Dictionary of demo users {username: {password_hash, email}}
        
    Raises:
        ValueError: If JSON format is invalid
        
    Example:
        >>> os.environ["DEMO_USERS_JSON"] = '{"demo":{"password_hash":"...","email":"..."}}'
        >>> users = load_demo_users()
        >>> "demo" in users
        True
        
    Security:
        - NO hardcoded credentials in code
        - Credentials loaded from environment only
        - Validation of required fields
    """
    demo_json = os.getenv("DEMO_USERS_JSON")
    
    if not demo_json:
        logger.warning("DEMO_USERS_JSON not set, no demo users available")
        return {}
    
    try:
        users = json.loads(demo_json)
        
        # Validation basique
        if not isinstance(users, dict):
            raise ValueError("DEMO_USERS_JSON must be a JSON object")
        
        for username, user_data in users.items():
            if not isinstance(user_data, dict):
                raise ValueError(f"Invalid user data for {username}")
            
            # Vérifier champs requis
            required_fields = ["password_hash", "email"]
            for field in required_fields:
                if field not in user_data:
                    raise ValueError(f"Missing field '{field}' for user {username}")
            
            # Vérifier format bcrypt hash
            password_hash = user_data["password_hash"]
            if not password_hash.startswith("$2b$"):
                raise ValueError(f"Invalid bcrypt hash format for user {username}")
        
        logger.info("Demo users loaded", count=len(users))
        return users
    
    except json.JSONDecodeError as e:
        logger.error("Invalid DEMO_USERS_JSON format", error=str(e))
        raise ValueError(f"Invalid DEMO_USERS_JSON format: {e}")
    except Exception as e:
        logger.error("Error loading demo users", error=str(e))
        raise


def get_demo_user(username: str) -> Optional[dict]:
    """
    Get demo user if demo auth is enabled.
    
    Args:
        username: Username to lookup
        
    Returns:
        Optional[dict]: User data if found and demo auth enabled, None otherwise
        
    Raises:
        RuntimeError: If demo auth is enabled in production (SECURITY)
        
    Example:
        >>> user = get_demo_user("demo")
        >>> user["email"]
        'demo@example.com'
        
    Security:
        - BLOCKS demo auth in production environment
        - Checks config.enable_demo_auth
        - Logs warning if demo auth used
    """
    from core.config import get_config
    
    config = get_config()
    
    # CRITICAL: Block demo auth in production
    if config.environment == "production":
        if config.enable_demo_auth:
            logger.error(
                "SECURITY VIOLATION: Demo auth enabled in production!",
                environment=config.environment
            )
            raise RuntimeError(
                "FATAL: Demo authentication MUST be disabled in production. "
                "Set ENABLE_DEMO_AUTH=false in production environment."
            )
    
    # Demo auth disabled
    if not config.enable_demo_auth:
        logger.debug("Demo auth disabled", username=username)
        return None
    
    # Load demo users
    demo_users = load_demo_users()
    user = demo_users.get(username)
    
    if user:
        logger.info("Demo user found", username=username)
    else:
        logger.debug("Demo user not found", username=username)
    
    return user


def validate_no_hardcoded_credentials(filepath: str) -> bool:
    """
    Validate that a Python file contains no hardcoded bcrypt hashes.
    
    Args:
        filepath: Path to Python file to check
        
    Returns:
        bool: True if no hardcoded credentials found
        
    Raises:
        SecurityError: If hardcoded credentials detected
        
    Example:
        >>> validate_no_hardcoded_credentials("api/routes/auth.py")
        True
        
    Security:
        - Scans for bcrypt hash pattern ($2b$)
        - Used in tests to prevent credential leaks
    """
    import re
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Pattern bcrypt: $2b$12$...
    bcrypt_pattern = r'\$2b\$\d{2}\$[A-Za-z0-9./]{53}'
    matches = re.findall(bcrypt_pattern, content)
    
    if matches:
        raise SecurityError(
            f"SECURITY VIOLATION: Hardcoded bcrypt hash found in {filepath}. "
            f"Found {len(matches)} credential(s). Remove immediately!"
        )
    
    return True


class SecurityError(Exception):
    """Security violation detected"""
    pass


# Validation au chargement du module
if __name__ == "__main__":
    # Test de chargement
    try:
        users = load_demo_users()
        print(f"✅ Loaded {len(users)} demo users")
        
        for username in users:
            user = get_demo_user(username)
            if user:
                print(f"  - {username}: {user['email']}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
