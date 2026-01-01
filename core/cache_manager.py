"""
Cache manager for performance optimization.
"""

import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple
from threading import Lock


class CacheManager:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self, default_ttl: int = 300):
        """
        Initialize cache manager.
        
        Args:
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
        """
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = Lock()
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if it exists and hasn't expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    return value
                else:
                    # Expired, remove it
                    del self._cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        ttl = ttl or self.default_ttl
        expiry = time.time() + ttl
        
        with self._lock:
            self._cache[key] = (value, expiry)
    
    def delete(self, key: str):
        """Delete a key from cache."""
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self):
        """Remove expired entries from cache."""
        current_time = time.time()
        with self._lock:
            expired_keys = [
                key for key, (_, expiry) in self._cache.items()
                if current_time >= expiry
            ]
            for key in expired_keys:
                del self._cache[key]
    
    def size(self) -> int:
        """Get number of cached entries."""
        return len(self._cache)


# Global cache instance
_cache_manager = CacheManager(default_ttl=300)


def get_cache_manager() -> CacheManager:
    """Get the global CacheManager instance."""
    return _cache_manager


def cached(ttl: Optional[int] = None, key_func: Optional[Callable] = None):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time-to-live in seconds (uses cache default if None)
        key_func: Optional function to generate cache key from args/kwargs
    """
    def decorator(func: Callable) -> Callable:
        cache = get_cache_manager()
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: use function name + args + kwargs
                cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # Check cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator

