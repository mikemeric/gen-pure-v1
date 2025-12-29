"""
User repository for user-specific database operations

Extends BaseRepository with user-specific queries:
- get_by_username()
- get_by_email()
- authenticate()
- update_last_login()
"""
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from infrastructure.database.models import User
from infrastructure.database.repositories.base import BaseRepository
from services.auth.password import verify_password


class UserRepository(BaseRepository[User]):
    """
    User repository with user-specific operations
    
    Provides:
    - All BaseRepository methods (create, get, update, delete, etc.)
    - get_by_username() - Find user by username
    - get_by_email() - Find user by email
    - authenticate() - Verify credentials
    - update_last_login() - Update login timestamp
    - get_active_users() - Get all active users
    """
    
    def __init__(self, session: Session):
        """
        Initialize user repository
        
        Args:
            session: Database session
        """
        super().__init__(User, session)
    
    def get_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username
        
        Args:
            username: Username to search for
        
        Returns:
            User: User instance or None if not found
        
        Example:
            >>> user = user_repo.get_by_username("john")
        """
        return self.session.query(User).filter(
            User.username == username
        ).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email
        
        Args:
            email: Email to search for
        
        Returns:
            User: User instance or None if not found
        
        Example:
            >>> user = user_repo.get_by_email("john@example.com")
        """
        return self.session.query(User).filter(
            User.email == email
        ).first()
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate user with username and password
        
        Args:
            username: Username
            password: Plain text password
        
        Returns:
            User: User instance if authentication successful, None otherwise
        
        Example:
            >>> user = user_repo.authenticate("john", "password123")
            >>> if user:
            ...     print("Login successful")
        """
        # Get user
        user = self.get_by_username(username)
        
        if not user:
            # Timing attack protection - still verify a dummy password
            verify_password("dummy_password", "$2b$12$" + "0" * 53)
            return None
        
        # Check if user is active
        if not user.is_active:
            return None
        
        # Verify password
        if not verify_password(password, user.password_hash):
            return None
        
        return user
    
    def update_last_login(self, user_id: int) -> bool:
        """
        Update user's last login timestamp
        
        Args:
            user_id: User ID
        
        Returns:
            bool: True if updated, False if user not found
        
        Example:
            >>> user_repo.update_last_login(123)
        """
        user = self.update(user_id, last_login=datetime.utcnow())
        return user is not None
    
    def get_active_users(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> list:
        """
        Get all active users
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
        
        Returns:
            list: List of active users
        
        Example:
            >>> active_users = user_repo.get_active_users(limit=50)
        """
        return self.session.query(User).filter(
            User.is_active == True
        ).offset(skip).limit(limit).all()
    
    def username_exists(self, username: str) -> bool:
        """
        Check if username already exists
        
        Args:
            username: Username to check
        
        Returns:
            bool: True if exists, False otherwise
        
        Example:
            >>> if user_repo.username_exists("john"):
            ...     print("Username taken")
        """
        return self.session.query(
            self.session.query(User).filter(
                User.username == username
            ).exists()
        ).scalar()
    
    def email_exists(self, email: str) -> bool:
        """
        Check if email already exists
        
        Args:
            email: Email to check
        
        Returns:
            bool: True if exists, False otherwise
        
        Example:
            >>> if user_repo.email_exists("john@example.com"):
            ...     print("Email already registered")
        """
        return self.session.query(
            self.session.query(User).filter(
                User.email == email
            ).exists()
        ).scalar()
    
    def create_user(
        self,
        username: str,
        email: str,
        password_hash: str,
        full_name: Optional[str] = None,
        company: Optional[str] = None,
        roles: Optional[list] = None,
        permissions: Optional[list] = None
    ) -> User:
        """
        Create a new user with validation
        
        Args:
            username: Unique username
            email: Unique email
            password_hash: Hashed password (use services.auth.password.hash_password)
            full_name: User's full name (optional)
            company: User's company (optional)
            roles: List of roles (default: ['user'])
            permissions: List of permissions (default: ['detect'])
        
        Returns:
            User: Created user instance
        
        Raises:
            ValueError: If username or email already exists
        
        Example:
            >>> from services.auth.password import hash_password
            >>> user = user_repo.create_user(
            ...     username="john",
            ...     email="john@example.com",
            ...     password_hash=hash_password("SecurePass123!"),
            ...     full_name="John Doe"
            ... )
        """
        # Check if username exists
        if self.username_exists(username):
            raise ValueError(f"Username '{username}' already exists")
        
        # Check if email exists
        if self.email_exists(email):
            raise ValueError(f"Email '{email}' already exists")
        
        # Set defaults
        if roles is None:
            roles = ['user']
        if permissions is None:
            permissions = ['detect']
        
        # Create user
        return self.create(
            username=username,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            company=company,
            roles=roles,
            permissions=permissions
        )
