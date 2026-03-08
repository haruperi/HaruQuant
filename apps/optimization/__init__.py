"""Optimization module package."""

__version__ = "1.0.0"

# Keep package import-light so API routes can import request/response models
# without eagerly loading heavier optimization execution modules at startup.
__all__ = ["__version__"]
