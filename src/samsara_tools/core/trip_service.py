"""Trip service for managing and filtering trailer trips."""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..models.trip import Trip, TripPoint, TripStop
from .client import SamsaraClient
from .geofence_resolver import GeofenceResolver

logger = logging.getLogger(__name__)


class TripService:
    """Service for querying and filtering trips with geofence support."""
    
    def __init__(self, api_token: str, lazy_resolver: bool = True):
        """Initialize trip service.
        
        Args:
            api_token: Samsara API token
            lazy_resolver: If True, delay GeofenceResolver initialization until needed
        """
        self.client = SamsaraClient(api_token)
        self.logger = logger
        self._resolver = None
        self._lazy_resolver = lazy_resolver
        self._path_cache = {}  # Cache trip paths by trip ID
        
        if not lazy_resolver:
            self._ensure_resolver()
    
    def _ensure_resolver(self):
        """Initialize GeofenceResolver if not already done."""
        if self._resolver is None:
            self.logger.info("Initializing GeofenceResolver...")
            self._resolver = GeofenceResolver(self.client)
    
    def _resolve_name(self, lat: Optional[float], lng: Optional[float]) -> Optional[str]:
        """Resolve coordinates to geofence name."""
        if lat is None or lng is None:
            return None
        
        self._ensure_resolver()
        return self._resolver.resolve(lat, lng)
    
    def _normalize(self, name: str) -> str:
        """Normalize name for case-insensitive comparison."""
        return name.lower().strip()
    
    def _to_trip_model(self, raw: Dict[str, Any], include_path: bool = False, trailer_id: str = '') -> Optional[Trip]:
        """Convert raw API response to Trip model.
        
        Args:
            raw: Raw trip data from API
            include_path: Whether to fetch and include trip path data
            
        Returns:
            Trip model instance or None if parsing fails
        """
        try:
            # Extract basic trip data
            trip_id = raw.get('id')
            if not trip_id:
                # Generate ID from start time and coordinates since Samsara doesn't provide trip IDs
                start_ms = raw.get('startMs', 0)
                start_coords = raw.get('startCoordinates', {})
                if start_ms and start_coords:
                    lat = start_coords.get('latitude', 0)
                    lng = start_coords.get('longitude', 0)
                    trip_id = f"trip_{start_ms}_{int(lat*1000000)}_{int(lng*1000000)}"
                else:
                    self.logger.warning("Trip missing both ID and sufficient data to generate ID, skipping")
                    return None
            
            # Parse timestamps
            start_ms = raw.get('startMs', 0)
            end_ms = raw.get('endMs', 0)
            
            if not start_ms:
                self.logger.warning(f"Trip {trip_id} missing start time, skipping")
                return None
            
            start_time = datetime.fromtimestamp(start_ms / 1000)
            end_time = datetime.fromtimestamp(end_ms / 1000) if end_ms else None
            
            # Parse locations
            start_coords = raw.get('startCoordinates', {})
            end_coords = raw.get('endCoordinates', {})
            
            start_location = None
            if start_coords:
                start_location = {
                    'lat': start_coords.get('latitude'),
                    'lng': start_coords.get('longitude')
                }
            
            end_location = None
            if end_coords:
                end_location = {
                    'lat': end_coords.get('latitude'),
                    'lng': end_coords.get('longitude')
                }
            
            # Calculate duration
            duration_seconds = None
            if start_ms and end_ms:
                duration_seconds = int((end_ms - start_ms) / 1000)
            
            # Create trip instance
            trip = Trip(
                id=trip_id,
                trailer_id=trailer_id or raw.get('vehicleId', ''),
                name=raw.get('name'),
                start_time=start_time,
                end_time=end_time,
                start_location=start_location,
                end_location=end_location,
                distance_meters=raw.get('distanceMeters'),
                duration_seconds=duration_seconds
            )
            
            # Add resolved geofence names if available
            # First check if API provided address names
            start_addr = raw.get('startAddress', {})
            end_addr = raw.get('endAddress', {})
            
            start_geofence = start_addr.get('name')
            end_geofence = end_addr.get('name')
            
            # If no names provided, resolve from coordinates
            if not start_geofence and start_location:
                start_geofence = self._resolve_name(
                    start_location.get('lat'),
                    start_location.get('lng')
                )
            
            if not end_geofence and end_location:
                end_geofence = self._resolve_name(
                    end_location.get('lat'),
                    end_location.get('lng')
                )
            
            # Store resolved names in enter_geofences for now
            # (This is a temporary solution until we add proper fields)
            if start_geofence or end_geofence:
                geofences = []
                if start_geofence:
                    geofences.append(f"start:{start_geofence}")
                if end_geofence:
                    geofences.append(f"end:{end_geofence}")
                trip.enter_geofences = geofences
            
            # Fetch path data if requested
            if include_path:
                try:
                    # Check cache first
                    if trip_id in self._path_cache:
                        path_data = self._path_cache[trip_id]
                    else:
                        path_data = self.client.get_trip_path(trip_id, include_stops=True)
                        self._path_cache[trip_id] = path_data
                    
                    if path_data:
                        # Parse GPS points
                        points = []
                        for point in path_data.get('points', []):
                            trip_point = TripPoint(
                                latitude=point['latitude'],
                                longitude=point['longitude'],
                                time=datetime.fromtimestamp(point['timeMs'] / 1000),
                                speed=point.get('speed'),
                                heading=point.get('heading')
                            )
                            points.append(trip_point)
                        trip.points = points
                        
                        # Parse stops
                        stops = []
                        for stop in path_data.get('stops', []):
                            trip_stop = TripStop(
                                id=stop['id'],
                                name=stop.get('name'),
                                address=stop.get('address'),
                                latitude=stop['latitude'],
                                longitude=stop['longitude'],
                                arrival_time=datetime.fromtimestamp(stop['arrivalTimeMs'] / 1000) if stop.get('arrivalTimeMs') else None,
                                departure_time=datetime.fromtimestamp(stop['departureTimeMs'] / 1000) if stop.get('departureTimeMs') else None,
                                duration_seconds=stop.get('durationSeconds'),
                                notes=stop.get('notes')
                            )
                            stops.append(trip_stop)
                        trip.stops = stops
                        
                except Exception as e:
                    self.logger.warning(f"Failed to fetch path for trip {trip_id}: {e}")
            
            return trip
            
        except Exception as e:
            self.logger.error(f"Failed to parse trip: {e}")
            return None
    
    def get_trips(self, asset_id: str, start_time: datetime, end_time: datetime,
                  include_path: bool = False, use_cache: bool = True) -> List[Trip]:
        """Get all trips for an asset within a time range.
        
        Args:
            asset_id: Asset/trailer ID
            start_time: Start of time range
            end_time: End of time range
            include_path: Whether to include GPS path data
            use_cache: Whether to use cached data
            
        Returns:
            List of Trip model instances
        """
        self.logger.info(f"Fetching trips for asset {asset_id} from {start_time} to {end_time}")
        
        # Get raw trips from API
        raw_trips = self.client.get_trips(asset_id, start_time, end_time, use_cache=use_cache)
        
        if len(raw_trips) > 1000:
            self.logger.warning(f"Retrieved {len(raw_trips)} trips - potential pagination issue")
        
        # Convert to model instances
        trips = []
        for raw_trip in raw_trips:
            trip = self._to_trip_model(raw_trip, include_path=include_path, trailer_id=asset_id)
            if trip:
                trips.append(trip)
        
        self.logger.info(f"Successfully parsed {len(trips)} trips")
        return trips
    
    def get_trip_by_id(self, trip_id: str, include_path: bool = False) -> Optional[Trip]:
        """Get a single trip by ID.
        
        Args:
            trip_id: Trip ID
            include_path: Whether to include GPS path data
            
        Returns:
            Trip model instance or None if not found
        """
        # Note: The Samsara API doesn't have a direct endpoint for single trip fetch
        # We would need to implement this differently, perhaps with a time range search
        # For now, return None with a warning
        self.logger.warning("get_trip_by_id not fully implemented - Samsara API lacks single trip endpoint")
        return None
    
    def filter_trips_by_geofence(self, trips: List[Trip], geofence_name: str,
                                match_start: bool = True, match_end: bool = True,
                                case_insensitive: bool = True) -> List[Trip]:
        """Filter trips by geofence name.
        
        Args:
            trips: List of trips to filter
            geofence_name: Geofence name to match
            match_start: Whether to match trips starting in geofence
            match_end: Whether to match trips ending in geofence
            case_insensitive: Whether to use case-insensitive matching
            
        Returns:
            Filtered list of trips
        """
        if not match_start and not match_end:
            self.logger.warning("Both match_start and match_end are False, returning empty list")
            return []
        
        normalized_target = self._normalize(geofence_name) if case_insensitive else geofence_name
        filtered_trips = []
        
        for trip in trips:
            # Extract geofence names from enter_geofences
            start_geofence = None
            end_geofence = None
            
            for geofence_entry in trip.enter_geofences:
                if geofence_entry.startswith("start:"):
                    start_geofence = geofence_entry[6:]  # Remove "start:" prefix
                elif geofence_entry.startswith("end:"):
                    end_geofence = geofence_entry[4:]  # Remove "end:" prefix
            
            # Check matches
            start_match = False
            end_match = False
            
            if match_start and start_geofence:
                normalized_start = self._normalize(start_geofence) if case_insensitive else start_geofence
                start_match = normalized_start == normalized_target
            
            if match_end and end_geofence:
                normalized_end = self._normalize(end_geofence) if case_insensitive else end_geofence
                end_match = normalized_end == normalized_target
            
            if start_match or end_match:
                filtered_trips.append(trip)
        
        self.logger.info(f"Filtered {len(filtered_trips)} trips matching geofence '{geofence_name}'")
        return filtered_trips
    
    def query_trips(self, asset_id: str, start_time: datetime, end_time: datetime,
                   geofence: Optional[str] = None, include_path: bool = False,
                   match_start: bool = True, match_end: bool = True,
                   use_cache: bool = True) -> List[Trip]:
        """Query trips with optional geofence filtering.
        
        Args:
            asset_id: Asset/trailer ID
            start_time: Start of time range
            end_time: End of time range
            geofence: Optional geofence name filter
            include_path: Whether to include GPS path data
            match_start: Whether to match trips starting in geofence
            match_end: Whether to match trips ending in geofence
            use_cache: Whether to use cached data
            
        Returns:
            List of Trip model instances
        """
        # Get all trips
        trips = self.get_trips(asset_id, start_time, end_time, 
                              include_path=include_path, use_cache=use_cache)
        
        # Apply geofence filter if provided
        if geofence:
            trips = self.filter_trips_by_geofence(
                trips, geofence, 
                match_start=match_start, 
                match_end=match_end
            )
        
        return trips
    
    def print_trips_summary(self, trips: List[Trip]):
        """Print a summary of trips to console."""
        if not trips:
            print("No trips found")
            return
        
        print(f"\nFound {len(trips)} trips:")
        print("=" * 80)
        
        for i, trip in enumerate(trips, 1):
            # Extract geofence names
            start_geofence = "Unknown"
            end_geofence = "Unknown"
            
            for geofence_entry in trip.enter_geofences:
                if geofence_entry.startswith("start:"):
                    start_geofence = geofence_entry[6:]
                elif geofence_entry.startswith("end:"):
                    end_geofence = geofence_entry[4:]
            
            # Format times
            start_str = trip.start_time.strftime('%Y-%m-%d %H:%M')
            end_str = trip.end_time.strftime('%Y-%m-%d %H:%M') if trip.end_time else 'In Progress'
            
            # Calculate distance in miles
            distance_mi = trip.distance_meters / 1609.34 if trip.distance_meters else 0
            
            print(f"\n{i}. Trip {trip.id}")
            print(f"   Start: {start_str} at {start_geofence}")
            print(f"   End:   {end_str} at {end_geofence}")
            print(f"   Distance: {distance_mi:.1f} miles")
            
            if trip.duration_seconds:
                hours = trip.duration_seconds // 3600
                minutes = (trip.duration_seconds % 3600) // 60
                print(f"   Duration: {hours}h {minutes}m")
    
    def query_trips_by_geofence(self, geofence_name: str, start_time: datetime, 
                                end_time: datetime, match_start: bool = True, 
                                match_end: bool = True, include_path: bool = False,
                                use_cache: bool = True, asset_types: Optional[List[str]] = None) -> Dict[str, List[Trip]]:
        """Query trips for all assets that start or end in a specific geofence.
        
        Args:
            geofence_name: Geofence name to match
            start_time: Start of time range
            end_time: End of time range
            match_start: Whether to match trips starting in geofence
            match_end: Whether to match trips ending in geofence
            include_path: Whether to include GPS path data
            use_cache: Whether to use cached data
            asset_types: Optional list of asset types to filter (e.g., ['trailer'])
            
        Returns:
            Dictionary mapping asset IDs to their matching trips
        """
        self.logger.info(f"Querying all assets for trips in geofence '{geofence_name}'")
        
        # First get all assets
        all_assets = []
        
        # Get trailers
        if not asset_types or 'trailer' in asset_types:
            trailers = self.client.get_all_trailers()
            for trailer in trailers:
                all_assets.append({
                    'id': trailer['id'],
                    'name': trailer.get('name', 'Unnamed'),
                    'type': 'trailer'
                })
        
        # Get vehicles if requested
        if asset_types and 'vehicle' in asset_types:
            # Note: Would need to implement get_all_vehicles in client
            # For now, just log a warning
            self.logger.warning("Vehicle asset type filtering not yet implemented")
        
        self.logger.info(f"Found {len(all_assets)} assets to check")
        
        # Query trips for each asset
        results = {}
        total_trips = 0
        
        for i, asset in enumerate(all_assets):
            asset_id = asset['id']
            asset_name = asset['name']
            
            if (i + 1) % 10 == 0:
                self.logger.info(f"Processing asset {i + 1}/{len(all_assets)}...")
            
            try:
                # Get trips for this asset
                trips = self.get_trips(asset_id, start_time, end_time, 
                                     include_path=include_path, use_cache=use_cache)
                
                # Filter by geofence
                if trips:
                    filtered_trips = self.filter_trips_by_geofence(
                        trips, geofence_name,
                        match_start=match_start,
                        match_end=match_end
                    )
                    
                    if filtered_trips:
                        results[asset_id] = filtered_trips
                        total_trips += len(filtered_trips)
                        self.logger.debug(f"Asset {asset_name} has {len(filtered_trips)} matching trips")
                        
            except Exception as e:
                self.logger.warning(f"Failed to query trips for asset {asset_id}: {e}")
                continue
        
        self.logger.info(f"Found {total_trips} total trips across {len(results)} assets")
        return results
    
    def print_geofence_trips_summary(self, results: Dict[str, List[Trip]], geofence_name: str):
        """Print a summary of trips by geofence results."""
        if not results:
            print(f"No trips found for any assets in geofence '{geofence_name}'")
            return
        
        total_trips = sum(len(trips) for trips in results.values())
        print(f"\nFound {total_trips} trips across {len(results)} assets in geofence '{geofence_name}':")
        print("=" * 80)
        
        # Get asset names for display
        asset_names = {}
        trailers = self.client.get_all_trailers()
        for trailer in trailers:
            asset_names[trailer['id']] = trailer.get('name', 'Unnamed')
        
        for asset_id, trips in results.items():
            asset_name = asset_names.get(asset_id, asset_id)
            print(f"\n{asset_name} (ID: {asset_id}) - {len(trips)} trips:")
            print("-" * 40)
            
            for trip in trips:
                # Extract geofence names
                start_geofence = "Unknown"
                end_geofence = "Unknown"
                
                for geofence_entry in trip.enter_geofences:
                    if geofence_entry.startswith("start:"):
                        start_geofence = geofence_entry[6:]
                    elif geofence_entry.startswith("end:"):
                        end_geofence = geofence_entry[4:]
                
                # Format times
                start_str = trip.start_time.strftime('%Y-%m-%d %H:%M')
                end_str = trip.end_time.strftime('%Y-%m-%d %H:%M') if trip.end_time else 'In Progress'
                
                # Calculate distance in miles
                distance_mi = trip.distance_meters / 1609.34 if trip.distance_meters else 0
                
                print(f"  {start_str} to {end_str} ({distance_mi:.1f} mi)")
                print(f"    From: {start_geofence}")
                print(f"    To:   {end_geofence}")
    
    def save_geofence_trips(self, results: Dict[str, List[Trip]], format: str = 'json',
                           output_file: Optional[Path] = None) -> Path:
        """Save geofence query results to file.
        
        Args:
            results: Dictionary mapping asset IDs to trips
            format: Output format (json, csv)
            output_file: Output file path (auto-generated if not provided)
            
        Returns:
            Path to saved file
        """
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = Path(f'geofence_trips_{timestamp}.{format}')
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'json':
            # Structure the output with asset information
            output_data = {
                'query_time': datetime.now().isoformat(),
                'total_trips': sum(len(trips) for trips in results.values()),
                'total_assets': len(results),
                'assets': {}
            }
            
            # Get asset names
            asset_names = {}
            trailers = self.client.get_all_trailers()
            for trailer in trailers:
                asset_names[trailer['id']] = trailer.get('name', 'Unnamed')
            
            for asset_id, trips in results.items():
                output_data['assets'][asset_id] = {
                    'name': asset_names.get(asset_id, 'Unknown'),
                    'trip_count': len(trips),
                    'trips': [trip.model_dump() for trip in trips]
                }
            
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2, default=str)
        
        elif format == 'csv':
            # Flatten the structure for CSV
            with open(output_file, 'w', newline='') as f:
                # Get asset names
                asset_names = {}
                trailers = self.client.get_all_trailers()
                for trailer in trailers:
                    asset_names[trailer['id']] = trailer.get('name', 'Unnamed')
                
                # Define extended fieldnames including asset info
                base_fields = ['asset_id', 'asset_name']
                if results:
                    # Get trip fields from first trip
                    first_trip = next(iter(results.values()))[0]
                    trip_fields = list(first_trip.to_csv_dict().keys())
                    fieldnames = base_fields + trip_fields
                    
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for asset_id, trips in results.items():
                        asset_name = asset_names.get(asset_id, 'Unknown')
                        for trip in trips:
                            row = {
                                'asset_id': asset_id,
                                'asset_name': asset_name,
                                **trip.to_csv_dict()
                            }
                            writer.writerow(row)
        
        else:
            raise ValueError(f"Unsupported format for geofence trips: {format}")
        
        total_trips = sum(len(trips) for trips in results.values())
        self.logger.info(f"Saved {total_trips} trips from {len(results)} assets to {output_file}")
        return output_file
    
    def save_trips(self, trips: List[Trip], format: str = 'json', 
                   output_file: Optional[Path] = None) -> Path:
        """Save trips to file in specified format.
        
        Args:
            trips: List of trips to save
            format: Output format (json, csv, gpx)
            output_file: Output file path (auto-generated if not provided)
            
        Returns:
            Path to saved file
        """
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = Path(f'trips_{timestamp}.{format}')
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'json':
            with open(output_file, 'w') as f:
                json.dump([trip.model_dump() for trip in trips], f, indent=2, default=str)
        
        elif format == 'csv':
            with open(output_file, 'w', newline='') as f:
                if trips:
                    writer = csv.DictWriter(f, fieldnames=trips[0].to_csv_dict().keys())
                    writer.writeheader()
                    for trip in trips:
                        writer.writerow(trip.to_csv_dict())
        
        elif format == 'gpx':
            # Combine multiple trips into one GPX file
            gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Samsara Tools"
     xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>Samsara Trips Export</name>
    <time>{time}</time>
  </metadata>
""".format(time=datetime.now().isoformat())
            
            # Add each trip as a separate track
            for trip in trips:
                if trip.points:  # Only include trips with GPS data
                    gpx_content += trip.to_gpx().split('<metadata>')[1].split('</gpx>')[0]
            
            gpx_content += "</gpx>"
            
            with open(output_file, 'w') as f:
                f.write(gpx_content)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        self.logger.info(f"Saved {len(trips)} trips to {output_file}")
        return output_file