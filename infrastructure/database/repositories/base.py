"""
Base repository pattern for database operations

Provides generic CRUD operations that can be inherited by specific repositories.
Uses the Unit of Work pattern with SQLAlchemy sessions.
"""
from typing import Type, TypeVar, Generic, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models import Base

# Type variable for model classes
ModelType = TypeVar('ModelType', bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with generic CRUD operations
    
    Provides:
    - create() - Insert new record
    - get() - Get by ID
    - get_all() - Get all records
    - update() - Update record
    - delete() - Delete record
    - count() - Count records
    
    Type Parameters:
        ModelType: SQLAlchemy model class
    
    Example:
        >>> class UserRepository(BaseRepository[User]):
        ...     def __init__(self, session: Session):
        ...         super().__init__(User, session)
    """
    
    def __init__(self, model: Type[ModelType], session: Session):
        """
        Initialize repository
        
        Args:
            model: SQLAlchemy model class
            session: Database session
        """
        self.model = model
        self.session = session
    
    def create(self, **kwargs) -> ModelType:
        """
        Create a new record
        
        Args:
            **kwargs: Model attributes
        
        Returns:
            ModelType: Created model instance
        
        Raises:
            SQLAlchemyError: If creation fails
        
        Example:
            >>> user = repo.create(
            ...     username="john",
            ...     email="john@example.com",
            ...     password_hash="..."
            ... )
        """
        try:
            instance = self.model(**kwargs)
            self.session.add(instance)
            self.session.flush()  # Get ID without committing
            return instance
        
        except SQLAlchemyError as e:
            self.session.rollback()
            raise
    
    def get(self, id: int) -> Optional[ModelType]:
        """
        Get a record by ID
        
        Args:
            id: Record ID
        
        Returns:
            ModelType: Model instance or None if not found
        
        Example:
            >>> user = repo.get(123)
        """
        return self.session.query(self.model).filter(
            self.model.id == id
        ).first()
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """
        Get all records with optional filtering and pagination
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of column:value filters
        
        Returns:
            list: List of model instances
        
        Example:
            >>> users = repo.get_all(skip=0, limit=10, filters={"is_active": True})
        """
        query = self.session.query(self.model)
        
        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)
        
        return query.offset(skip).limit(limit).all()
    
    def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """
        Update a record
        
        Args:
            id: Record ID
            **kwargs: Attributes to update
        
        Returns:
            ModelType: Updated model instance or None if not found
        
        Raises:
            SQLAlchemyError: If update fails
        
        Example:
            >>> user = repo.update(123, email="newemail@example.com")
        """
        try:
            instance = self.get(id)
            if not instance:
                return None
            
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            
            self.session.flush()
            return instance
        
        except SQLAlchemyError:
            self.session.rollback()
            raise
    
    def delete(self, id: int) -> bool:
        """
        Delete a record
        
        Args:
            id: Record ID
        
        Returns:
            bool: True if deleted, False if not found
        
        Raises:
            SQLAlchemyError: If deletion fails
        
        Example:
            >>> deleted = repo.delete(123)
        """
        try:
            instance = self.get(id)
            if not instance:
                return False
            
            self.session.delete(instance)
            self.session.flush()
            return True
        
        except SQLAlchemyError:
            self.session.rollback()
            raise
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records with optional filtering
        
        Args:
            filters: Dictionary of column:value filters
        
        Returns:
            int: Number of records
        
        Example:
            >>> count = repo.count(filters={"is_active": True})
        """
        query = self.session.query(self.model)
        
        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)
        
        return query.count()
    
    def exists(self, id: int) -> bool:
        """
        Check if a record exists
        
        Args:
            id: Record ID
        
        Returns:
            bool: True if exists, False otherwise
        
        Example:
            >>> if repo.exists(123):
            ...     print("User exists")
        """
        return self.session.query(
            self.session.query(self.model).filter(
                self.model.id == id
            ).exists()
        ).scalar()
    
    def commit(self):
        """Commit the current transaction"""
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise
    
    def rollback(self):
        """Rollback the current transaction"""
        self.session.rollback()
