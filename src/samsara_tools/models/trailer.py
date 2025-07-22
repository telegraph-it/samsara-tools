"""
Trailer data models for Samsara API responses.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class TrailerLocation(BaseModel):
    """Represents the last known location of a trailer."""
    latitude: float
    longitude: float
    time: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class Trailer(BaseModel):
    """Represents a trailer asset."""
    id: str
    name: Optional[str] = None
    asset_number: Optional[str] = None  # Samsara "identifier"
    vin: Optional[str] = None
    tag_ids: List[str] = Field(default_factory=list)
    last_location: Optional[TrailerLocation] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None          # e.g. "moving", "idle"
    odometer_miles: Optional[float] = None
    fuel_level_percent: Optional[float] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    # --------------------------------------------------------------------- #
    # Helpers
    # --------------------------------------------------------------------- #
    def to_csv_dict(self) -> Dict[str, Any]:
        """Flatten trailer data for CSV export."""
        return {
            "trailer_id": self.id,
            "trailer_name": self.name,
            "asset_number": self.asset_number,
            "vin": self.vin,
            "tag_ids": ",".join(self.tag_ids),
            "latitude": self.last_location.latitude if self.last_location else None,
            "longitude": self.last_location.longitude if self.last_location else None,
            "location_time": (
                self.last_location.time.isoformat()
                if self.last_location and self.last_location.time
                else None
            ),
            "is_active": self.is_active,
            "status": self.status,
            "odometer_miles": self.odometer_miles,
            "fuel_level_percent": self.fuel_level_percent,
        }