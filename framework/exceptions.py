"""
Custom exceptions for the MatchEng framework.
"""


class MatchEngException(Exception):
    """Base exception for MatchEng framework."""
    pass


class ValidationError(MatchEngException):
    """Raised when validation fails."""
    pass


class ProcessingError(MatchEngException):
    """Raised when processing fails."""
    pass

