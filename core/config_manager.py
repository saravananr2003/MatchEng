"""
Configuration manager with caching for improved performance.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional
from threading import Lock


class ConfigManager:
    """Manages configuration files with caching and thread safety."""
    
    _instance: Optional['ConfigManager'] = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._cache: Dict[str, Any] = {}
                    cls._instance._file_timestamps: Dict[str, float] = {}
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._cache: Dict[str, Any] = {}
            self._file_timestamps: Dict[str, float] = {}
            self._initialized = True
    
    def load_config(self, file_path: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Load JSON configuration file with caching.
        
        Args:
            file_path: Path to the JSON config file
            use_cache: Whether to use cached version if file hasn't changed
            
        Returns:
            Dictionary containing config data, or empty dict if file doesn't exist
        """
        file_path = str(Path(file_path).resolve())
        
        # Check if file exists
        path = Path(file_path)
        if not path.exists():
            return {}
        
        # Get file modification time
        current_mtime = path.stat().st_mtime
        
        # Check cache
        if use_cache and file_path in self._cache:
            cached_mtime = self._file_timestamps.get(file_path, 0)
            if current_mtime <= cached_mtime:
                return self._cache[file_path]
        
        # Load from file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Update cache
            with self._lock:
                self._cache[file_path] = data
                self._file_timestamps[file_path] = current_mtime
            
            return data
        except (json.JSONDecodeError, IOError) as e:
            # Return empty dict on error, but log it
            return {}
    
    def save_config(self, file_path: str, data: Dict[str, Any]) -> bool:
        """
        Save configuration to JSON file and update cache.
        
        Args:
            file_path: Path to save the config file
            data: Configuration data to save
            
        Returns:
            True if successful, False otherwise
        """
        file_path = str(Path(file_path).resolve())
        path = Path(file_path)
        
        try:
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            
            # Update cache
            with self._lock:
                self._cache[file_path] = data
                self._file_timestamps[file_path] = path.stat().st_mtime
            
            return True
        except (IOError, OSError):
            return False
    
    def invalidate_cache(self, file_path: Optional[str] = None):
        """
        Invalidate cache for a specific file or all files.
        
        Args:
            file_path: Path to invalidate, or None to clear all cache
        """
        with self._lock:
            if file_path:
                file_path = str(Path(file_path).resolve())
                self._cache.pop(file_path, None)
                self._file_timestamps.pop(file_path, None)
            else:
                self._cache.clear()
                self._file_timestamps.clear()
    
    def get_cached(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get cached config without loading from disk."""
        file_path = str(Path(file_path).resolve())
        return self._cache.get(file_path)


# Global instance
_config_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    """Get the global ConfigManager instance."""
    return _config_manager

