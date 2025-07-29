"""Samsara API Tools - A toolkit for interacting with the Samsara API."""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .core.client import SamsaraClient
from .core.geofence_query import SamsaraGeofenceQuery
from .core.geofence_resolver import GeofenceResolver
from .core.route_service import RouteService
from .models.route import Route, RoutePoint, RouteStop
from .models.trailer import Trailer, TrailerLocation
from .models.trip import Trip, TripPoint, TripStop

__all__ = [
    "SamsaraClient",
    "SamsaraGeofenceQuery",
    "GeofenceResolver", 
    "RouteService",
    "Route",
    "RoutePoint",
    "RouteStop",
    "Trailer",
    "TrailerLocation",
    "Trip",
    "TripPoint",
    "TripStop",
] 