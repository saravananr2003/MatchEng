"""
Custom exceptions for the Matching Engine framework.
"""


class MatchEngException(Exception):
    """Base exception for Matching Engine framework."""
    pass


class ValidationError(MatchEngException):
    """Raised when validation fails."""
    pass


class ProcessingError(MatchEngException):
    """Raised when processing fails."""
    pass

