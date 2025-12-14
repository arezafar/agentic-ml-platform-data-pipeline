"""
FastAPI Routers Package

This package contains all API route definitions organized by domain.
"""

from . import health, predictions

__all__ = ['health', 'predictions']
