"""
Flask blueprints for modular route organization.
"""

from .pages import pages_bp
from .api import api_bp

__all__ = ['pages_bp', 'api_bp']

