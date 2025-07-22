"""Data models for Samsara API responses."""

# Future: Add Pydantic models for API responses
# from .gateway import Gateway
# from .geofence import Geofence  
# from .tag import Tag

from .route import Route, RoutePoint, RouteStop

__all__ = ["Route", "RoutePoint", "RouteStop"] 