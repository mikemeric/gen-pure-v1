"""
Rate limiting with Redis backend and in-memory fallback

Implements sliding window rate limiting to protect against:
- Brute force attacks
- DoS attacks
- API abuse

Supports both Redis (production) and in-memory (development) storage.
"""
import time
import threading
from typing import Dict, Optional
from collections import deque
from datetime import datetime, timedelta

from core.logging import get_logger

# Logger
logger = get_logger("auth")


class RateLimiter:
    """
    Sliding window rate limiter
    
    Features:
    - Configurable rate limits (requests per time window)
    - Redis backend with in-memory fallback
    - Automatic cleanup of expired entries
    - Thread-safe operations
    - Multiple storage backends
    """
    
    def __init__(
        self,
        max_attempts: int = 5,
        window_seconds: int = 300,
        storage: str = 'memory',
        redis_url: Optional[str] = None
    ):
        """
        Initialize rate limiter
        
        Args:
            max_attempts: Maximum attempts allowed in window
            window_seconds: Time window in seconds
            storage: 'redis' or 'memory' (default: 'memory')
            redis_url: Redis connection URL (required if storage='redis')
        
        Example:
            >>> limiter = RateLimiter(max_attempts=5, window_seconds=60)
            >>> limiter.is_allowed("user123")
            True
        """
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.storage = storage
        
        # In-memory storage
        self._memory_store: Dict[str, deque] = {}
        self._lock = threading.Lock()
        
        # Redis storage
        self._redis_client = None
        if storage == 'redis' and redis_url:
            try:
                import redis
                self._redis_client = redis.from_url(redis_url, decode_responses=False)
                logger.info("Rate limiter connected to Redis", backend="redis")
            except Exception as e:
                logger.warning("Redis unavailable, falling back to memory", error=str(e))
                self.storage = 'memory'
    
    def is_allowed(self, key: str) -> bool:
        """
        Check if request is allowed under rate limit
        
        Args:
            key: Identifier (IP address, user ID, etc.)
        
        Returns:
            bool: True if allowed, False if rate limited
        
        Raises:
            Exception: If rate limit exceeded
        
        Example:
            >>> limiter = RateLimiter(max_attempts=3, window_seconds=60)
            >>> for i in range(5):
            ...     try:
            ...         limiter.is_allowed("user1")
            ...         print(f"Request {i+1}: OK")
            ...     except Exception as e:
            ...         print(f"Request {i+1}: {e}")
        """
        if self.storage == 'redis' and self._redis_client:
            return self._is_allowed_redis(key)
        else:
            return self._is_allowed_memory(key)
    
    def _is_allowed_redis(self, key: str) -> bool:
        """Rate limit check using Redis"""
        try:
            now = time.time()
            window_start = now - self.window_seconds
            
            # Clean old entries
            self._redis_client.zremrangebyscore(
                f"ratelimit:{key}",
                0,
                window_start
            )
            
            # Count attempts in window
            count = self._redis_client.zcard(f"ratelimit:{key}")
            
            if count >= self.max_attempts:
                # Calculate retry after
                oldest = self._redis_client.zrange(
                    f"ratelimit:{key}",
                    0,
                    0,
                    withscores=True
                )
                if oldest:
                    retry_after = int(oldest[0][1] + self.window_seconds - now)
                    raise Exception(
                        f"Rate limit exceeded. Try again in {retry_after} seconds."
                    )
            
            # Record this attempt
            self._redis_client.zadd(
                f"ratelimit:{key}",
                {str(now): now}
            )
            
            # Set expiration
            self._redis_client.expire(
                f"ratelimit:{key}",
                self.window_seconds
            )
            
            return True
        
        except Exception as e:
            if "Rate limit exceeded" in str(e):
                raise
            # Redis error - fall back to allowing request
            logger.warning("Redis error in rate limiter", error=str(e))
            return True
    
    def _is_allowed_memory(self, key: str) -> bool:
        """Rate limit check using in-memory storage"""
        with self._lock:
            now = time.time()
            window_start = now - self.window_seconds
            
            # Get or create deque for this key
            if key not in self._memory_store:
                self._memory_store[key] = deque()
            
            attempts = self._memory_store[key]
            
            # Remove expired attempts
            while attempts and attempts[0] < window_start:
                attempts.popleft()
            
            # Check limit
            if len(attempts) >= self.max_attempts:
                # Calculate retry after
                retry_after = int(attempts[0] + self.window_seconds - now)
                raise Exception(
                    f"Rate limit exceeded. Try again in {retry_after} seconds."
                )
            
            # Record this attempt
            attempts.append(now)
            
            return True
    
    def get_remaining_attempts(self, key: str) -> int:
        """
        Get remaining attempts for a key
        
        Args:
            key: Identifier
        
        Returns:
            int: Number of remaining attempts
        """
        if self.storage == 'redis' and self._redis_client:
            try:
                now = time.time()
                window_start = now - self.window_seconds
                
                # Clean old entries
                self._redis_client.zremrangebyscore(
                    f"ratelimit:{key}",
                    0,
                    window_start
                )
                
                # Count attempts
                count = self._redis_client.zcard(f"ratelimit:{key}")
                return max(0, self.max_attempts - count)
            except:
                return self.max_attempts
        else:
            with self._lock:
                now = time.time()
                window_start = now - self.window_seconds
                
                if key not in self._memory_store:
                    return self.max_attempts
                
                attempts = self._memory_store[key]
                
                # Remove expired
                while attempts and attempts[0] < window_start:
                    attempts.popleft()
                
                return max(0, self.max_attempts - len(attempts))
    
    def reset(self, key: str):
        """
        Reset rate limit for a key
        
        Args:
            key: Identifier to reset
        """
        if self.storage == 'redis' and self._redis_client:
            try:
                self._redis_client.delete(f"ratelimit:{key}")
            except:
                pass
        else:
            with self._lock:
                if key in self._memory_store:
                    del self._memory_store[key]
    
    def cleanup_expired(self):
        """
        Clean up expired entries (memory storage only)
        
        Should be called periodically to prevent memory leaks.
        """
        if self.storage == 'memory':
            with self._lock:
                now = time.time()
                window_start = now - self.window_seconds
                
                # Clean each key
                keys_to_delete = []
                for key, attempts in self._memory_store.items():
                    # Remove expired attempts
                    while attempts and attempts[0] < window_start:
                        attempts.popleft()
                    
                    # Mark empty queues for deletion
                    if not attempts:
                        keys_to_delete.append(key)
                
                # Delete empty keys
                for key in keys_to_delete:
                    del self._memory_store[key]
    
    def get_stats(self) -> dict:
        """
        Get rate limiter statistics
        
        Returns:
            dict: Statistics
        """
        if self.storage == 'redis' and self._redis_client:
            try:
                keys = self._redis_client.keys("ratelimit:*")
                return {
                    "storage": "redis",
                    "tracked_keys": len(keys),
                    "max_attempts": self.max_attempts,
                    "window_seconds": self.window_seconds
                }
            except:
                pass
        
        with self._lock:
            return {
                "storage": "memory",
                "tracked_keys": len(self._memory_store),
                "max_attempts": self.max_attempts,
                "window_seconds": self.window_seconds
            }


# Singleton for global rate limiter
_global_rate_limiter: Optional[RateLimiter] = None
_rate_limiter_lock = threading.Lock()


def get_rate_limiter(
    max_attempts: int = 100,
    window_seconds: int = 60,
    storage: str = 'memory',
    redis_url: Optional[str] = None
) -> RateLimiter:
    """
    Get the global rate limiter singleton
    
    Args:
        max_attempts: Maximum attempts in window
        window_seconds: Time window
        storage: 'redis' or 'memory'
        redis_url: Redis URL
    
    Returns:
        RateLimiter: Singleton instance
    """
    global _global_rate_limiter
    
    if _global_rate_limiter is not None:
        return _global_rate_limiter
    
    with _rate_limiter_lock:
        if _global_rate_limiter is None:
            _global_rate_limiter = RateLimiter(
                max_attempts=max_attempts,
                window_seconds=window_seconds,
                storage=storage,
                redis_url=redis_url
            )
    
    return _global_rate_limiter
