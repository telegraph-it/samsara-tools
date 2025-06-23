"""Samsara API Tools - A toolkit for interacting with the Samsara API."""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .core.client import SamsaraClient
from .core.geofence_query import SamsaraGeofenceQuery

__all__ = [
    "SamsaraClient",
    "SamsaraGeofenceQuery",
] 