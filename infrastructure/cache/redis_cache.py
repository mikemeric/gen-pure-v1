"""
Redis cache with LRU and in-memory fallback, protected by Circuit Breaker

Provides caching with:
- Redis backend (production)
- In-memory LRU fallback (development)
- Automatic serialization/deserialization
- TTL support
- Cache statistics
- Circuit Breaker protection against Redis failures
- Structured logging
"""
import json
import time
import threading
from typing import Any, Optional, Dict
from collections import OrderedDict

from infrastructure.queue.circuit_breaker import CircuitBreaker, CircuitBreakerError
from core.logging import get_logger

# Logger
logger = get_logger("cache")


class LRUCache:
    """
    In-memory LRU (Least Recently Used) cache
    
    Features:
    - Thread-safe operations
    - Automatic eviction of least used items
    - TTL support
    - Statistics tracking
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize LRU cache
        
        Args:
            max_size: Maximum number of items to cache
        """
        self.max_size = max_size
        self._cache: OrderedDict = OrderedDict()
        self._ttl: Dict[str, float] = {}  # key -> expiration timestamp
        self._lock = threading.Lock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
        
        Returns:
            Any: Cached value or None if not found/expired
        """
        with self._lock:
            # Check if expired
            if key in self._ttl:
                if time.time() > self._ttl[key]:
                    # Expired - remove
                    del self._cache[key]
                    del self._ttl[key]
                    self._misses += 1
                    return None
            
            # Get value
            if key in self._cache:
                # Move to end (mark as recently used)
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            
            self._misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (optional)
        """
        with self._lock:
            # Add/update value
            self._cache[key] = value
            self._cache.move_to_end(key)
            
            # Set TTL if provided
            if ttl:
                self._ttl[key] = time.time() + ttl
            elif key in self._ttl:
                del self._ttl[key]
            
            # Evict oldest if over max size
            if len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                if oldest_key in self._ttl:
                    del self._ttl[oldest_key]
    
    def delete(self, key: str) -> bool:
        """
        Delete value from cache
        
        Args:
            key: Cache key
        
        Returns:
            bool: True if deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._ttl:
                    del self._ttl[key]
                return True
            return False
    
    def clear(self):
        """Clear all cached values"""
        with self._lock:
            self._cache.clear()
            self._ttl.clear()
            self._hits = 0
            self._misses = 0
    
    def get_stats(self) -> dict:
        """
        Get cache statistics
        
        Returns:
            dict: Statistics including hits, misses, hit rate
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            
            return {
                "type": "memory_lru",
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate * 100, 2)
            }


class RedisCache:
    """
    Redis-backed cache with automatic fallback to LRU
    
    Features:
    - Redis backend for production
    - LRU fallback if Redis unavailable
    - Automatic JSON serialization
    - TTL support
    - Cache statistics
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_size: int = 1000,
        default_ttl: int = 3600
    ):
        """
        Initialize Redis cache with Circuit Breaker protection
        
        Args:
            redis_url: Redis connection URL (optional)
            max_size: Max size for LRU fallback
            default_ttl: Default TTL in seconds
        """
        self.default_ttl = default_ttl
        self._redis_client = None
        self._lru_cache = LRUCache(max_size)
        self._using_redis = False
        
        # Circuit Breaker for Redis operations
        # Opens after 5 consecutive failures, recovers after 30 seconds
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30,
            expected_exception=Exception  # Catch all Redis exceptions
        )
        
        # Try to connect to Redis
        if redis_url:
            try:
                import redis
                self._redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self._redis_client.ping()
                self._using_redis = True
                logger.info("Redis cache connected", circuit_breaker=True, backend="redis")
            except Exception as e:
                logger.warning("Redis unavailable, using LRU fallback", error=str(e))
                self._redis_client = None
                self._using_redis = False
        else:
            logger.info("Redis cache using LRU fallback", reason="no URL provided")
    
    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON"""
        return json.dumps(value)
    
    def _deserialize(self, value: str) -> Any:
        """Deserialize value from JSON"""
        try:
            return json.loads(value)
        except:
            return value
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache with Circuit Breaker protection
        
        Args:
            key: Cache key
        
        Returns:
            Any: Cached value or None if not found
        """
        if self._using_redis and self._redis_client:
            try:
                # Use Circuit Breaker to protect Redis call
                def _redis_get():
                    value = self._redis_client.get(key)
                    if value is not None:
                        return self._deserialize(value)
                    return None
                
                return self.circuit_breaker.call(_redis_get)
            
            except CircuitBreakerError:
                # Circuit is open - fall back to LRU
                logger.warning("Redis circuit open, using LRU fallback", operation="get", key=key)
                return self._lru_cache.get(key)
            except Exception as e:
                # Redis error - fall back to LRU
                logger.warning("Redis get error, using LRU fallback", error=str(e), key=key)
                return self._lru_cache.get(key)
        else:
            return self._lru_cache.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache with Circuit Breaker protection
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: self.default_ttl)
        """
        if ttl is None:
            ttl = self.default_ttl
        
        if self._using_redis and self._redis_client:
            try:
                # Use Circuit Breaker to protect Redis call
                def _redis_set():
                    serialized = self._serialize(value)
                    self._redis_client.setex(key, ttl, serialized)
                
                self.circuit_breaker.call(_redis_set)
            
            except CircuitBreakerError:
                # Circuit is open - fall back to LRU
                logger.warning("Redis circuit open, using LRU fallback", operation="set", key=key)
                self._lru_cache.set(key, value, ttl)
            except Exception as e:
                # Redis error - fall back to LRU
                logger.warning("Redis set error, using LRU fallback", error=str(e), key=key)
                self._lru_cache.set(key, value, ttl)
        else:
            self._lru_cache.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """
        Delete value from cache
        
        Args:
            key: Cache key
        
        Returns:
            bool: True if deleted, False if not found
        """
        if self._using_redis and self._redis_client:
            try:
                result = self._redis_client.delete(key)
                return result > 0
            except Exception as e:
                logger.warning("Redis delete error", error=str(e), key=key)
                return self._lru_cache.delete(key)
        else:
            return self._lru_cache.delete(key)
    
    def clear(self):
        """Clear all cached values"""
        if self._using_redis and self._redis_client:
            try:
                self._redis_client.flushdb()
            except Exception as e:
                logger.warning("Redis clear error", error=str(e))
        
        self._lru_cache.clear()
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache
        
        Args:
            key: Cache key
        
        Returns:
            bool: True if exists, False otherwise
        """
        if self._using_redis and self._redis_client:
            try:
                # Use circuit breaker for consistency with other Redis operations
                def _redis_exists():
                    return self._redis_client.exists(key) > 0
                
                return self.circuit_breaker.call(_redis_exists)
            except:
                # Fallback to LRU on any error (including CircuitBreakerError)
                return self._lru_cache.get(key) is not None
        else:
            return self._lru_cache.get(key) is not None
    
    async def health_check(self) -> bool:
        """
        Check Redis health and attempt reconnection if down.
        
        Returns:
            bool: True if Redis is healthy (or successfully reconnected)
        
        Features:
            - Pings Redis to verify connection
            - Auto-reconnects if Redis is down
            - Switches from LRU fallback back to Redis
            - Logs status changes
        """
        # If using Redis, check connection
        if self._redis_client:
            try:
                self._redis_client.ping()
                
                # If we were using LRU fallback, log reconnection
                if not self._using_redis:
                    logger.info(
                        "Redis reconnected - switching from LRU fallback",
                        backend="redis"
                    )
                    self._using_redis = True
                
                return True
            
            except Exception as e:
                # Redis down
                if self._using_redis:
                    logger.warning(
                        "Redis connection lost - switching to LRU fallback",
                        error=str(e)
                    )
                    self._using_redis = False
                
                # Try to reconnect
                return await self.try_reconnect()
        
        # No Redis client configured
        else:
            # Try to reconnect if we have URL
            return await self.try_reconnect()
    
    async def try_reconnect(self) -> bool:
        """
        Attempt to reconnect to Redis.
        
        Returns:
            bool: True if reconnection succeeded
        """
        try:
            # Get Redis URL from config
            from core.config import get_config
            redis_url = get_config().redis_url
            
            if not redis_url:
                return False
            
            # Attempt connection
            import redis
            test_client = redis.from_url(redis_url, decode_responses=True)
            test_client.ping()
            
            # Success - update client
            self._redis_client = test_client
            self._using_redis = True
            
            logger.info(
                "Redis reconnection successful",
                backend="redis"
            )
            return True
        
        except Exception as e:
            logger.debug(
                "Redis reconnection failed",
                error=str(e)
            )
            return False
    
    def get_stats(self) -> dict:
        """
        Get cache statistics
        
        Returns:
            dict: Cache statistics
        """
        if self._using_redis and self._redis_client:
            try:
                info = self._redis_client.info('stats')
                return {
                    "type": "redis",
                    "connected": True,
                    "hits": info.get('keyspace_hits', 0),
                    "misses": info.get('keyspace_misses', 0),
                    "keys": self._redis_client.dbsize()
                }
            except:
                return {
                    "type": "redis",
                    "connected": False,
                    "fallback": self._lru_cache.get_stats()
                }
        else:
            return self._lru_cache.get_stats()


# Singleton instance
_cache: Optional[RedisCache] = None
_cache_lock = threading.Lock()


def get_cache(redis_url: Optional[str] = None) -> RedisCache:
    """
    Get the cache singleton (thread-safe)
    
    Args:
        redis_url: Redis connection URL (required on first call)
    
    Returns:
        RedisCache: Singleton instance
    
    Example:
        >>> from core.config import get_config
        >>> cache = get_cache(get_config().redis_url)
    """
    global _cache
    
    # Fast path
    if _cache is not None:
        return _cache
    
    # Slow path with lock
    with _cache_lock:
        if _cache is None:
            if redis_url is None:
                # Try to get from config
                try:
                    from core.config import get_config
                    redis_url = get_config().redis_url
                except:
                    pass
            
            _cache = RedisCache(redis_url)
    
    return _cache
