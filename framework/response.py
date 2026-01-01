"""
Standardized API response classes for the MatchEng framework.
"""

from typing import Any, Dict, Optional
from flask import jsonify


class APIResponse:
    """Base class for standardized API responses."""
    
    def __init__(self, success: bool, data: Any = None, message: str = None, 
                 error: str = None, status_code: int = 200):
        self.success = success
        self.data = data
        self.message = message
        self.error = error
        self.status_code = status_code
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        result = {
            "ok": self.success,
            "success": self.success
        }
        
        if self.data is not None:
            result["data"] = self.data
        
        if self.message:
            result["message"] = self.message
        
        if self.error:
            result["error"] = self.error
        
        return result
    
    def to_json(self):
        """Convert response to Flask JSON response."""
        return jsonify(self.to_dict()), self.status_code


class SuccessResponse(APIResponse):
    """Standardized success response."""
    
    def __init__(self, data: Any = None, message: str = None, status_code: int = 200):
        super().__init__(
            success=True,
            data=data,
            message=message,
            status_code=status_code
        )


class ErrorResponse(APIResponse):
    """Standardized error response."""
    
    def __init__(self, error: str, status_code: int = 400, details: Any = None):
        data = {"details": details} if details else None
        super().__init__(
            success=False,
            data=data,
            error=error,
            status_code=status_code
        )

