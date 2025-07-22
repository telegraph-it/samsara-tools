"""
Route data models for Samsara API responses.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RoutePoint(BaseModel):
    """Represents a GPS point along a route."""
    latitude: float
    longitude: float
    time: datetime
    speed: Optional[float] = None
    heading: Optional[int] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RouteStop(BaseModel):
    """Represents a stop along a route."""
    id: str
    name: Optional[str] = None
    address: Optional[str] = None
    latitude: float
    longitude: float
    arrival_time: Optional[datetime] = None
    departure_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    notes: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Route(BaseModel):
    """Represents a complete route."""
    id: str
    name: Optional[str] = None
    driver_id: Optional[str] = None
    driver_name: Optional[str] = None
    vehicle_id: Optional[str] = None
    vehicle_name: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    start_location: Optional[Dict[str, float]] = None  # {"lat": 0.0, "lng": 0.0}
    end_location: Optional[Dict[str, float]] = None
    distance_meters: Optional[int] = None
    duration_seconds: Optional[int] = None
    stops: List[RouteStop] = Field(default_factory=list)
    points: List[RoutePoint] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_gpx(self) -> str:
        """Convert route to GPX format."""
        gpx_header = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Samsara Tools"
     xmlns="http://www.topografix.com/GPX/1/1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://www.topografix.com/GPX/1/1 
     http://www.topografix.com/GPX/1/1/gpx.xsd">
  <metadata>
    <name>{name}</name>
    <time>{time}</time>
  </metadata>
  <trk>
    <name>{name}</name>
    <trkseg>
""".format(name=self.name or f"Route {self.id}", time=self.start_time.isoformat())
        
        track_points = ""
        for point in self.points:
            track_points += f"""      <trkpt lat="{point.latitude}" lon="{point.longitude}">
        <time>{point.time.isoformat()}</time>
        {f'<speed>{point.speed}</speed>' if point.speed else ''}
      </trkpt>
"""
        
        waypoints = ""
        for stop in self.stops:
            waypoints += f"""  <wpt lat="{stop.latitude}" lon="{stop.longitude}">
    <name>{stop.name or 'Stop'}</name>
    {f'<desc>{stop.address}</desc>' if stop.address else ''}
    {f'<time>{stop.arrival_time.isoformat()}</time>' if stop.arrival_time else ''}
  </wpt>
"""
        
        gpx_footer = """    </trkseg>
  </trk>
{waypoints}</gpx>""".format(waypoints=waypoints)
        
        return gpx_header + track_points + gpx_footer
    
    def to_csv_dict(self) -> Dict[str, Any]:
        """Convert route to a flat dictionary for CSV export."""
        return {
            "route_id": self.id,
            "route_name": self.name,
            "driver_id": self.driver_id,
            "driver_name": self.driver_name,
            "vehicle_id": self.vehicle_id,
            "vehicle_name": self.vehicle_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "start_lat": self.start_location.get("lat") if self.start_location else None,
            "start_lng": self.start_location.get("lng") if self.start_location else None,
            "end_lat": self.end_location.get("lat") if self.end_location else None,
            "end_lng": self.end_location.get("lng") if self.end_location else None,
            "distance_meters": self.distance_meters,
            "duration_seconds": self.duration_seconds,
            "num_stops": len(self.stops),
            "num_points": len(self.points)
        }
