"""
File service for handling file operations with performance optimizations.
"""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from core.cache_manager import get_cache_manager


class FileService:
    """Service for file operations with caching."""
    
    def __init__(self):
        self.cache = get_cache_manager()
    
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Get file information with caching.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file info (size, modified time, etc.)
        """
        if not file_path.exists():
            return {}
        
        stat = file_path.stat()
        cache_key = f"file_info:{file_path}:{stat.st_mtime}"
        
        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        info = {
            "filename": file_path.name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "path": str(file_path)
        }
        
        # Cache for 60 seconds
        self.cache.set(cache_key, info, ttl=60)
        return info
    
    def read_csv_preview(
        self, 
        file_path: Path, 
        max_rows: int = 100,
        encoding: str = 'utf-8'
    ) -> Dict[str, Any]:
        """
        Read CSV file preview with optimized I/O.
        
        Args:
            file_path: Path to CSV file
            max_rows: Maximum number of rows to read
            encoding: File encoding
            
        Returns:
            Dictionary with headers, preview rows, and total row count
        """
        cache_key = f"csv_preview:{file_path}:{file_path.stat().st_mtime}:{max_rows}"
        
        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            preview_rows = []
            headers = []
            total_rows = 0
            
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                
                for i, row in enumerate(reader):
                    total_rows = i + 1
                    if i < max_rows:
                        preview_rows.append(dict(row))
            
            result = {
                "headers": headers,
                "preview": preview_rows,
                "total_rows": total_rows
            }
            
            # Cache for 30 seconds
            self.cache.set(cache_key, result, ttl=30)
            return result
            
        except Exception as e:
            return {"error": str(e), "headers": [], "preview": [], "total_rows": 0}
    
    def count_csv_rows(self, file_path: Path) -> int:
        """
        Count rows in CSV file efficiently (without loading all data).
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Number of rows (excluding header)
        """
        cache_key = f"csv_count:{file_path}:{file_path.stat().st_mtime}"
        
        # Check cache
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                # Skip header
                next(f, None)
                # Count remaining lines
                count = sum(1 for _ in f)
            
            # Cache for 60 seconds
            self.cache.set(cache_key, count, ttl=60)
            return count
        except Exception:
            return 0
    
    def list_files(
        self, 
        directory: Path, 
        pattern: str = "*.csv",
        sort_by: str = "modified"
    ) -> List[Dict[str, Any]]:
        """
        List files in directory with metadata.
        
        Args:
            directory: Directory to list
            pattern: File pattern to match
            sort_by: Sort key ('modified', 'size', 'name')
            
        Returns:
            List of file info dictionaries
        """
        if not directory.exists():
            return []
        
        files = []
        for file_path in directory.glob(pattern):
            info = self.get_file_info(file_path)
            if info:
                files.append(info)
        
        # Sort
        reverse = sort_by == "modified"
        if sort_by == "modified":
            files.sort(key=lambda x: x.get("modified", ""), reverse=reverse)
        elif sort_by == "size":
            files.sort(key=lambda x: x.get("size", 0), reverse=reverse)
        else:
            files.sort(key=lambda x: x.get("filename", ""), reverse=reverse)
        
        return files


# Global instance
_file_service = FileService()


def get_file_service() -> FileService:
    """Get the global FileService instance."""
    return _file_service

