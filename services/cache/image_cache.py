"""
Image Cache - Intelligent caching by content hash

Prevents reprocessing identical images by caching results based on image content hash.
"""
import hashlib
from typing import Optional, Any
import json

from core.logging import get_logger

# Logger
logger = get_logger("cache")


def get_image_hash(content: bytes) -> str:
    """
    Generate cache key from image content hash
    
    Uses SHA-256 to create deterministic hash of image bytes.
    Same image = same hash = cache hit.
    
    Args:
        content: Image file bytes
    
    Returns:
        str: SHA-256 hash as hex string (64 chars)
    
    Example:
        >>> with open("image.jpg", "rb") as f:
        ...     content = f.read()
        >>> cache_key = get_image_hash(content)
        >>> # cache_key = "a1b2c3d4..."
    
    Performance:
        - SHA-256 is fast (~100MB/s)
        - Same image uploaded 10 times = processed once
        - Cache TTL: 1 hour (configurable)
    """
    return hashlib.sha256(content).hexdigest()


def get_detection_cache_key(
    content: bytes,
    method: str,
    use_preprocessing: bool = True
) -> str:
    """
    Generate cache key including detection parameters
    
    Cache key format: "detection:{hash}:{method}:{preprocessing}"
    
    Args:
        content: Image bytes
        method: Detection method (hough, clustering, edge, ensemble)
        use_preprocessing: Whether preprocessing is enabled
    
    Returns:
        str: Complete cache key
    
    Example:
        >>> key = get_detection_cache_key(content, "ensemble", True)
        >>> # "detection:a1b2c3d4...:ensemble:1"
    
    Why method and preprocessing matter:
        - Same image with different methods → different results
        - Same image with/without preprocessing → different results
        - Cache must be specific to all parameters
    """
    image_hash = get_image_hash(content)
    preprocessing_flag = "1" if use_preprocessing else "0"
    
    return f"detection:{image_hash}:{method}:{preprocessing_flag}"


class ImageCache:
    """
    Intelligent image-based cache wrapper
    
    Features:
    - Content-based hashing (not filename)
    - Parameter-aware caching (method, preprocessing)
    - Automatic serialization/deserialization
    - Statistics tracking
    
    Example:
        >>> from infrastructure.cache.redis_cache import RedisCache
        >>> redis = RedisCache(redis_url="redis://localhost:6379")
        >>> cache = ImageCache(redis)
        >>> 
        >>> # Try to get cached result
        >>> cached = await cache.get_detection_result(content, "ensemble", True)
        >>> if cached:
        ...     return cached  # Cache hit!
        >>> 
        >>> # Cache miss - compute result
        >>> result = detector.detect(image, method="ensemble")
        >>> 
        >>> # Cache result
        >>> await cache.set_detection_result(content, "ensemble", True, result, ttl=3600)
    """
    
    def __init__(self, backend):
        """
        Initialize image cache
        
        Args:
            backend: Cache backend (RedisCache or LRUCache)
        """
        self.backend = backend
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0
        }
    
    async def get_detection_result(
        self,
        content: bytes,
        method: str,
        use_preprocessing: bool = True
    ) -> Optional[dict]:
        """
        Get cached detection result
        
        Args:
            content: Image bytes
            method: Detection method
            use_preprocessing: Preprocessing flag
        
        Returns:
            dict: Cached result or None if cache miss
        """
        cache_key = get_detection_cache_key(content, method, use_preprocessing)
        
        try:
            cached_value = self.backend.get(cache_key)
            
            if cached_value:
                self.stats["hits"] += 1
                
                # Deserialize if string
                if isinstance(cached_value, str):
                    return json.loads(cached_value)
                
                return cached_value
            else:
                self.stats["misses"] += 1
                return None
        
        except Exception as e:
            logger.warning("Cache get error", error=str(e), operation="get_detection_result")
            self.stats["misses"] += 1
            return None
    
    async def set_detection_result(
        self,
        content: bytes,
        method: str,
        use_preprocessing: bool,
        result: dict,
        ttl: int = 3600
    ) -> bool:
        """
        Cache detection result
        
        Args:
            content: Image bytes
            method: Detection method
            use_preprocessing: Preprocessing flag
            result: Detection result to cache
            ttl: Time-to-live in seconds (default: 1 hour)
        
        Returns:
            bool: True if cached successfully
        """
        cache_key = get_detection_cache_key(content, method, use_preprocessing)
        
        try:
            # Serialize result
            if not isinstance(result, (str, bytes)):
                result_str = json.dumps(result)
            else:
                result_str = result
            
            # Cache result
            self.backend.set(cache_key, result_str, ttl=ttl)
            self.stats["sets"] += 1
            
            return True
        
        except Exception as e:
            logger.warning("Cache set error", error=str(e), operation="set_detection_result")
            return False
    
    def get_stats(self) -> dict:
        """
        Get cache statistics
        
        Returns:
            dict: Cache statistics with hit rate
        """
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2)
        }
    
    def clear_stats(self):
        """Reset statistics"""
        self.stats = {"hits": 0, "misses": 0, "sets": 0}


# Singleton instance (shared across requests)
_image_cache_instance = None


def get_image_cache():
    """
    Get shared ImageCache instance
    
    Returns:
        ImageCache: Shared cache instance
    
    Usage:
        >>> cache = get_image_cache()
        >>> cached = await cache.get_detection_result(content, "ensemble", True)
    """
    global _image_cache_instance
    
    if _image_cache_instance is None:
        # Import here to avoid circular dependency
        from infrastructure.cache.redis_cache import RedisCache
        from core.config import get_config
        
        config = get_config()
        backend = RedisCache(redis_url=config.redis_url)
        _image_cache_instance = ImageCache(backend)
    
    return _image_cache_instance
