"""
Secure password hashing with bcrypt

Provides password hashing and verification using bcrypt with secure defaults:
- 12 rounds (cost factor) - OWASP recommended
- Automatic salt generation
- Timing attack protection
- Password strength validation
"""
import re
import bcrypt
from typing import Optional


class PasswordManager:
    """
    Manages password hashing and verification
    
    Features:
    - Bcrypt hashing with 12 rounds
    - Automatic salt generation
    - Timing attack protection
    - Password strength validation
    - Secure comparison
    """
    
    # Bcrypt cost factor (OWASP recommends 12+ for 2023)
    BCRYPT_ROUNDS = 12
    
    # Password requirements
    MIN_LENGTH = 8
    MAX_LENGTH = 100
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        """
        Hash a password using bcrypt
        
        Args:
            password: Plain text password
        
        Returns:
            str: Bcrypt hash (includes salt)
        
        Example:
            >>> hashed = PasswordManager.hash_password("SecurePass123!")
            >>> hashed.startswith('$2b$')
            True
        """
        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=cls.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        return hashed.decode('utf-8')
    
    @classmethod
    def verify_password(cls, password: str, hashed: str) -> bool:
        """
        Verify a password against a hash
        
        Args:
            password: Plain text password to verify
            hashed: Bcrypt hash to check against
        
        Returns:
            bool: True if password matches, False otherwise
        
        Example:
            >>> hashed = PasswordManager.hash_password("MyPassword123!")
            >>> PasswordManager.verify_password("MyPassword123!", hashed)
            True
            >>> PasswordManager.verify_password("WrongPassword", hashed)
            False
        
        Note:
            Uses constant-time comparison to prevent timing attacks
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed.encode('utf-8')
            )
        except Exception:
            # Invalid hash format or other error
            return False
    
    @classmethod
    def validate_password_strength(cls, password: str) -> tuple[bool, Optional[str]]:
        """
        Validate password strength
        
        Requirements:
        - Length: 8-100 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        
        Args:
            password: Password to validate
        
        Returns:
            tuple: (is_valid, error_message)
        
        Example:
            >>> PasswordManager.validate_password_strength("weak")
            (False, "Password must be at least 8 characters")
            >>> PasswordManager.validate_password_strength("StrongPass123!")
            (True, None)
        """
        # Check length
        if len(password) < cls.MIN_LENGTH:
            return False, f"Password must be at least {cls.MIN_LENGTH} characters"
        
        if len(password) > cls.MAX_LENGTH:
            return False, f"Password must not exceed {cls.MAX_LENGTH} characters"
        
        # Check for uppercase
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        # Check for lowercase
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        # Check for digit
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        # Check for special character
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:,.<>?]', password):
            return False, "Password must contain at least one special character"
        
        return True, None
    
    @classmethod
    def generate_temp_password(cls, length: int = 16) -> str:
        """
        Generate a secure temporary password
        
        Args:
            length: Password length (default: 16)
        
        Returns:
            str: Random password meeting strength requirements
        
        Example:
            >>> temp = PasswordManager.generate_temp_password()
            >>> len(temp)
            16
            >>> PasswordManager.validate_password_strength(temp)[0]
            True
        """
        import secrets
        import string
        
        # Character sets
        uppercase = string.ascii_uppercase
        lowercase = string.ascii_lowercase
        digits = string.digits
        special = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        # Ensure at least one of each required type
        password = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]
        
        # Fill remaining length
        all_chars = uppercase + lowercase + digits + special
        password.extend(
            secrets.choice(all_chars)
            for _ in range(length - 4)
        )
        
        # Shuffle
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)
    
    @classmethod
    def needs_rehash(cls, hashed: str) -> bool:
        """
        Check if a password hash needs to be rehashed
        
        This is useful when upgrading the cost factor.
        
        Args:
            hashed: Bcrypt hash to check
        
        Returns:
            bool: True if rehash recommended
        
        Example:
            >>> old_hash = bcrypt.hashpw(b"password", bcrypt.gensalt(rounds=10)).decode()
            >>> PasswordManager.needs_rehash(old_hash)
            True
        """
        try:
            # Extract cost factor from hash
            # Format: $2b$12$...
            parts = hashed.split('$')
            if len(parts) >= 3:
                cost = int(parts[2])
                return cost < cls.BCRYPT_ROUNDS
        except:
            pass
        
        return False


# Utility functions

def hash_password(password: str) -> str:
    """
    Convenience function to hash a password
    
    Args:
        password: Plain text password
    
    Returns:
        str: Bcrypt hash
    """
    return PasswordManager.hash_password(password)


def verify_password(password: str, hashed: str) -> bool:
    """
    Convenience function to verify a password
    
    Args:
        password: Plain text password
        hashed: Bcrypt hash
    
    Returns:
        bool: True if password matches
    """
    return PasswordManager.verify_password(password, hashed)


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Convenience function to validate password strength
    
    Args:
        password: Password to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    return PasswordManager.validate_password_strength(password)
